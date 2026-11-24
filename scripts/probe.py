import json, urllib.request, os
os.makedirs("data",exist_ok=True)
H={"User-Agent":"Mozilla/5.0"}
out={}
for s in ["105.NVDA","105.SOXX","105.QQQ"]:
    for fq in (0,1):
        u=f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={s}&fields1=f1&fields2=f51,f52,f53,f54,f55&klt=101&fqt={fq}&end=20500101&lmt=4"
        try: out[f"{s}_fq{fq}"]=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=15).read())["data"]["klines"]
        except Exception as e: out[f"{s}_fq{fq}"]=repr(e)
print(json.dumps(out,ensure_ascii=False,indent=0))
json.dump(out,open("data/probe.json","w"),indent=0)
