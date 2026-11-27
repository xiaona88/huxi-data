import json, urllib.request, datetime
def get(u,ref):
    return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":ref}),timeout=30).read().decode("gbk","ignore")
out={"at":datetime.datetime.utcnow().isoformat()}
try: out["hq"]=get("https://hq.sinajs.cn/list=sz301000,sz002428,sz000700,sh600186,sh588170,sz158041,sh000688,sz399006","https://finance.sina.com.cn/")
except Exception as e: out["hq"]=repr(e)
json.dump(out,open("data/probe.json","w"),ensure_ascii=False)
