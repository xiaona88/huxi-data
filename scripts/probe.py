import json, urllib.request, datetime
def get(u,ref):
    return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":ref}),timeout=30).read().decode("gbk","ignore")
out={"at":datetime.datetime.utcnow().isoformat()}
syms="sh688516,sz000158,sz000700,sh603360,sz002931,sh588170,sh600186,sz000711,sz002042,sh000001,sz399006,sh000688"
try: out["hq"]=get("https://hq.sinajs.cn/list="+syms,"https://finance.sina.com.cn/")
except Exception as e: out["hq"]=repr(e)
json.dump(out,open("data/probe.json","w"),ensure_ascii=False,indent=1)
# 1795745792
