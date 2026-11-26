import json, urllib.request, re
def get(u,ref):
    return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":ref}),timeout=30).read().decode("utf8","ignore")
out={}
for s in ["SOXX","QQQ","NVDA",".IXIC","UVIX"]:
    try:
        t=get(f"https://stock.finance.sina.com.cn/usstock/api/jsonp.php/x/US_MinKService.getDailyK?symbol={s}&type=daily","https://stock.finance.sina.com.cn/")
        j=json.loads(t[t.index("(")+1:t.rindex(")")]); out[s]=j[-3:]
    except Exception as e: out[s]=repr(e)[:150]
for s in ["105.SOXX","105.QQQ","105.NVDA"]:
    try:
        j=json.loads(get(f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={s}&fields1=f1&fields2=f51,f53&klt=101&fqt=0&lmt=3&end=20500101","https://quote.eastmoney.com/"))
        out[s]=j["data"]["klines"]
    except Exception as e: out[s]=repr(e)[:150]
try: out["hq"]=get("https://hq.sinajs.cn/list=gb_soxx,gb_qqq,gb_nvda,gb_ixic","https://finance.sina.com.cn/")[:800]
except Exception as e: out["hq"]=repr(e)
json.dump(out,open("data/probe.json","w"),ensure_ascii=False,indent=1)
