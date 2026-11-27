import json, urllib.request, datetime
def get(u,ref):
    return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":ref}),timeout=30).read().decode("utf8","ignore")
out={"at":datetime.datetime.utcnow().isoformat()}
for k,s in [("KOSPI","100.KS11"),("N225","100.N225")]:
    try:
        j=json.loads(get(f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={s}&fields1=f1&fields2=f51,f52,f53,f54,f55&klt=101&fqt=0&lmt=700&end=20500101","https://quote.eastmoney.com/"))
        out[k]=j["data"]["klines"]
    except Exception as e: out[k]=repr(e)[:200]
for s in ["sh000688","sh000001","sz399006"]:
    try:
        t=get(f"https://quotes.sina.cn/cn/api/jsonp_v2.php/x/CN_MarketDataService.getKLineData?symbol={s}&scale=240&ma=no&datalen=700","https://finance.sina.com.cn/")
        out[s]=json.loads(t[t.index("(")+1:t.rindex(")")])
    except Exception as e: out[s]=repr(e)[:200]
for s in ["SOXX","QQQ"]:
    try:
        t=get(f"https://stock.finance.sina.com.cn/usstock/api/jsonp.php/x/US_MinKService.getDailyK?symbol={s}&type=daily","https://stock.finance.sina.com.cn/")
        out[s]=json.loads(t[t.index("(")+1:t.rindex(")")])[-700:]
    except Exception as e: out[s]=repr(e)[:200]
try: out["hq"]=get("https://hq.sinajs.cn/list=b_KOSPI,b_NKY,sh000688,sh000001","https://finance.sina.com.cn/")
except Exception as e: out["hq"]=repr(e)
json.dump(out,open("data/probe.json","w"),ensure_ascii=False)
