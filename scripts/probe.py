import json, urllib.request
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn/"}),timeout=40).read()
json.dump({"d":json.loads(get("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh600186&scale=240&ma=no&datalen=400"))},open("data/probe.json","w"))
