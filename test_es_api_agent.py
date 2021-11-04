from datetime import datetime,timedelta
import requests
from elasticsearch import Elasticsearch
from elasticsearch_dsl import A,Q,Search
import pytz
import json
import argparse

#es連線資訊
def connection_info():
    es = Elasticsearch(["10.121.0.41","10.121.0.42","10.121.0.43","10.121.0.44","10.121.0.45","10.121.0.46"],
    http_auth=('elastic', 'zT0YA5W01tcTlIi2De04')
    )
    return es
def product_info(product):
    products = {
        'lc' : '10',
        'v8' : '5',
        'mp' : '2',
        'ly1' : '10',
        'ly2' : '10',
        'ly3' : '5', 
        'xsj' : '1',
        'xsj2' : '2',
        'ky34' : '10',
        'ky110' : '10',
        'ky508' : '10',
        'kydf' : '10',
        'kygpk' : '10',
        'kyt' : '2',
        'kyz' : '10'
    }
    return products[product]

# telegram 資訊
def telegram_bot_sendtext(bot_message):
    #product channel
    # bot_token = '1854129202:AAE5amgijJpQVYPo2ARMZP4b7dvS7PlZuic'
    # bot_chatID = '-512809025'
    #test channel 
    bot_token = '1882707925:AAFkhLbz45lZFrURcn_IQVsW8uNgfXrxbpo'
    bot_chatID = '999849909'
    send_text = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={bot_chatID}&parse_mode=Markdown&text={bot_message}"
    response = requests.get(send_text)

#建立index並放入資料
def create_index(product):
    ymd = datetime.today().strftime('%Y%m%d')
    index_name = f"logstash-{product}-agnet-monitor-alert-{ymd}"
    es = connection_info()
    created = True
    # index settings
    settings = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1
        },
        "mappings": {
                "properties": {
                    "@timestamp": {
                        "type": "date"
                    },
                    "product": {
                        "type": "keyword"
                    },
                    "agent": {
                        "type": "long"
                    },
                    "count": {
                        "type": "long"
                    },
                    "result": {
                        "type": "keyword"
                    }
                }
        }
    }
    try:
        if not es.indices.exists(index_name):
            # Ignore 400 means to ignore "Index Already Exist" error.
            es.indices.create(index=index_name, ignore=400 , body=settings)
            print('Created index done')
        created = False
    except Exception as ex:
        print(str(ex))
    finally:
        return created

#query特定條件，並做aggregations後輸出top 10 Agent
def get_agent_list(product):
    #取得es連線資訊
    es = connection_info()
    top_size = product_info(product)
    #獲取特定時間的代理號總數並做bucket
    try:
        s = Search(using=es, index=f"logstash-{product}-channelhandle-out-*").filter('range',  ** {'@timestamp':{'gte': "now-12h" }})
        s.aggs.bucket('agent','terms', field='agent',size=top_size)
        response = s.execute()
    except:
        print(f"{product} 代理統計失敗！！")
    
    i = 0
    list_of_agent = []
    #將抓取到前10大代理號放進陣列中
    for hit in response.aggregations.agent.buckets:
        agent = hit.key
        list_of_agent.append(agent)
    return list_of_agent

#計算三分鐘內agent 數量，將資料存進elasticsearch內
def check_agent_count_to_es(product):
    create_index(product)   
    es = connection_info()
    ymd = datetime.today().strftime('%Y%m%d')
    index_name = f"logstash-{product}-agent-monitor-alert-{ymd}"
    agent_list = get_agent_list(product)

    for agent in agent_list:
        s = Search(using=es, index=f"logstash-{product}-channelhandle-out-*").query("match",agent=agent).filter('range',  ** {'@timestamp':{'gte': "now-3m" }})
        response =  s.execute()
        
        #定義時間時區
        local = pytz.timezone('Asia/Taipei')
        local_dt = local.localize(datetime.now(), is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)
        time_str = datetime.strftime(utc_dt, "%Y-%m-%dT%H:%M:%S.%f")

        if response.hits.total.value <1 :             
            #定義data 
            data={
                "@timestamp": time_str+ "Z",
                "product": product,
                "agent" : agent,
                "count" : response.hits.total.value,
                "result": "No data",
            }
            #塞資料到elasticsearch內
            insert_data = es.index(index=index_name, body=data)
            #發出告警
            # bot_message = f"{product} 代理：{agent} 目前人數小於1，請確認代理是否維護中"
            # telegram_bot_sendtext(bot_message)                
        else:
            data={
                "@timestamp": time_str+ "Z",
                "product": product,
                "agent" : agent,
                "count" : response.hits.total.value,
                "result": "Resolved",
            }
            #塞資料到elk內
            insert_data = es.index(index=index_name, body=data)                
            #bot_message = f"{product} 代理：{agent} 目前人數 {response.hits.total.value}"
            #telegram_bot_sendtext(bot_message)

def monitor_alert(product):
    es = connection_info()
    ymd = datetime.today().strftime('%Y%m%d')
    agent_list = get_agent_list(product)
    NowTS = round(datetime.timestamp(datetime.now()))*1000
    ThreeMinTS = round(datetime.timestamp(datetime.now()+timedelta(minutes=-3)))*1000
    SixMinTS = round(datetime.timestamp(datetime.now()+timedelta(minutes=-6)))*1000
 
    for agent in agent_list:
        s1 = Search(using=es, index=f"logstash-{product}-agent-monitor-alert-{ymd}").query("match",agent=agent).filter('range',  ** {'@timestamp':{'gte':ThreeMinTS,'lt':NowTS}})
        s2 = Search(using=es, index=f"logstash-{product}-agent-monitor-alert-{ymd}").query("match",agent=agent).filter('range',  ** {'@timestamp':{'gte':SixMinTS,'lt':ThreeMinTS}})
        result_3 = s1.execute()
        result_6 = s2.execute()

        for i,j in zip(result_3,result_6):
            if i['result'] == 'Resolved' and j['result'] == 'Resolved':
                return "OK"
            elif i['result'] == 'No data' and j['result'] == 'No data':
                return "No Data"
            elif i['result'] == 'Resolved' and j['result'] == 'No data':
                bot_message = f"Status: Warning!! {product} 代理：{agent} API Request < 0."
                telegram_bot_sendtext(bot_message)
            elif i['result'] == 'No data' and j['result'] =='Resolved':
                bot_message = f"Status: Resolve!! {product} 代理：{agent} API Request > 0."
                telegram_bot_sendtext(bot_message) 
            else:
                return "Nothing"

                


parser = argparse.ArgumentParser(description='Agent count Alert')
parser.add_argument('--product','-p',help='請輸入產品，kyt, ktgpk, ly1, ly2, mp, lc, v8, xsj, xsj2', required=True)
args = parser.parse_args()

if __name__ == "__main__":

    # check_agent_count_to_es(args.product)
    monitor_alert(args.product)



