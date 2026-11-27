import json, urllib.request, datetime
def get(u,ref):
    return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":ref}),timeout=30).read().decode("utf8","ignore")
out={"at":datetime.datetime.utcnow().isoformat()}
for s in ["sh510300","sh510050","sh588000","sz159915","sh000001","sh000688","sh588170"]:
    try:
        t=get(f"https://quotes.sina.cn/cn/api/jsonp_v2.php/x/CN_MarketDataService.getKLineData?symbol={s}&scale=5&ma=no&datalen=150","https://finance.sina.com.cn/")
        out[s]=json.loads(t[t.index("(")+1:t.rindex(")")])
    except Exception as e: out[s]=repr(e)[:200]
json.dump(out,open("data/probe.json","w"),ensure_ascii=False)
