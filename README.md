# es_api

1. function connection_info
   Elasticsearch 連線主機資訊
   http_auth 認證資訊

2. function connection_info
   定義產品要抓取的前幾個

3. function telegram_bot_sendtext
   定義發送 tg 的資訊

4. function get_agent_list
   query 產品 index 現在時間到一天的代理總數後  並做 bucket 計算出前幾名丟進陣列內

5. function check_agent_count
   根據傳進來的 product 參數，來搜尋三分內的代理總數，低於 1 就呼叫 function telegram_bot_sendtext 發出告警
