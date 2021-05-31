from elasticsearch import  Elasticsearch
from datetime import datetime


es = Elasticsearch(
    ['10.121.0.41:9200',"10.121.0.42:9200", "10.121.0.43:9200"], # 連線叢集，以列表的形式存放各節點的IP地址
    sniff_on_start=True,    # 連線前測試
    sniff_on_connection_fail=True,  # 節點無響應時重新整理節點
    sniff_timeout=60,    # 設定超時時間
    http_auth=('elastic', 'zT0YA5W01tcTlIi2De04')  # 認證資訊
    )
    "body": {
        "size": 0,
        "aggs": {
        "2": {
            "terms": {
            "field": "agent",
            "order": {
                "_count": "asc"
            },
            "size": 500
            }
        }
        }
    }
    request = es.search(index="logstash-ky110-channelhandle-out-20210531", doc_type="mytype", body=body)
    print(request)