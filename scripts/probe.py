import json, urllib.request
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn/"}),timeout=20).read()
out={"hq":get("https://hq.sinajs.cn/list=sz000700,sh600186,sh588170,sh000688,sz399006,sh000001").decode("gbk")}
out["d"]=json.loads(get("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sz000700&scale=240&ma=no&datalen=30"))
json.dump(out,open("data/probe.json","w"),ensure_ascii=False)
