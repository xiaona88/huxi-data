import json, urllib.request, datetime
def get(u,ref):
    return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":ref}),timeout=30).read().decode("gbk","ignore")
out={"at":datetime.datetime.utcnow().isoformat()}
syms="bj920186,sh688516,sz003043,sh603690,sh688605,sh588170,sh000688,sh510050,sh588000,sz000700,sz002931"
try: out["hq"]=get("https://hq.sinajs.cn/list="+syms,"https://finance.sina.com.cn/")
except Exception as e: out["hq"]=repr(e)
json.dump(out,open("data/probe.json","w"),ensure_ascii=False)
