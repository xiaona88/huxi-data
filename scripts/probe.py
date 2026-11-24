import json, urllib.request, os
H={"User-Agent":"Mozilla/5.0","Referer":"https://data.eastmoney.com/"}
BK={"BK0475":"银行","BK0474":"保险","BK0473":"证券","BK1036":"半导体","BK0448":"通信设备","BK0459":"电子元件","BK0737":"软件开发","BK1037":"消费电子"}
out={}
for k,n in BK.items():
    u=f"https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=5&klt=101&secid=90.{k}&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57"
    try:
        j=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=15).read())
        out[n]=[(x.split(",")[0][5:],*[round(float(v)/1e8,1) for v in x.split(",")[1:6]],x.split(",")[6]) for x in j["data"]["klines"]]
        out[n+"_name"]=j["data"].get("name")
    except Exception as e: out[n]=repr(e)[:150]
for k,v in out.items(): print(k,v)
