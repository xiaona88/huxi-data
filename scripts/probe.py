import json, urllib.request, statistics as st
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn/"}),timeout=20).read()
k=json.loads(get("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh588170&scale=240&ma=no&datalen=400"))
m=json.loads(get("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh588170&scale=5&ma=no&datalen=1970"))
json.dump({"d":k,"m":m},open("data/probe.json","w"))
