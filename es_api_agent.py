import datetime
import requests
from elasticsearch import Elasticsearch
from elasticsearch_dsl import A,Q,Search
import json
import argparse

#es連線資訊
def connection_info():
    es = Elasticsearch(["192.168.185.88"],
        http_auth=('elastic', 'changeme')
    )
    return es

def product_info(product):
    products = {
        'lc' : '10',
        'v8' : '5',
        'mp' : '2',
        'ly1' : '1',
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

#query特定條件，並做aggregations後輸出top 10 Agent
def get_agent_list(product):

    #取得es連線資訊
    es = connection_info()
    top_size = product_info(product)
    #獲取特定時間的代理號總數並做bucket
    try:
        s = Search(using=es, index=f"logstash-{product}-channelhandle-out-*").filter('range',  ** {'@timestamp':{'gte': "now-30d" }})
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

#計算三分鐘內agent 數量，如果小於1則發出告警
def check_agent_count(product):   
    es = connection_info()
    agent_list = get_agent_list(product)
    try:
        for agent in agent_list:
            s = Search(using=es, index=f"logstash-{product}-channelhandle-out-*").query("match",agent=agent).filter('range',  ** {'@timestamp':{'gte': "now-30d" }})
            response =  s.execute()
            if response.hits.total.value <1 : 
                bot_message = f"{product} 代理：{agent} 目前人數小於1，請確認代理是否維護中"
                telegram_bot_sendtext(bot_message)
            else:
               bot_message = f"{product} 代理：{agent} 目前人數 {response.hits.total.value}"
               telegram_bot_sendtext(bot_message)
    except :
        print(f"{product} 代理抓取失敗")

parser = argparse.ArgumentParser(description='Agent count Alert')
parser.add_argument('--product','-p',help='請輸入產品，kyt, ktgpk, ly1, ly2, mp, lc, v8, xsj, xsj2', required=True)
args = parser.parse_args()

if __name__ == "__main__":

    check_agent_count(args.product)



