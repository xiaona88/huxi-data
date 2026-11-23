import json, urllib.request, datetime, os
os.makedirs("data",exist_ok=True)
H={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"}
tests={
 "sina_kline":"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000001&scale=240&ma=no&datalen=3",
 "sina_hq_node":"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=5&sort=symbol&asc=1&node=hs_a",
 "em_rzrq":"https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPTA_RZRQ_LSHJ&columns=ALL&pageSize=2&sortColumns=DIM_DATE&sortTypes=-1",
 "em_push2his":"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000001&fields1=f1&fields2=f51,f53&klt=101&fqt=1&end=20500101&lmt=3",
}
out={"run_at":datetime.datetime.utcnow().isoformat()}
for k,u in tests.items():
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=20).read().decode("utf-8","replace")
        out[k]={"ok":True,"head":r[:300]}
    except Exception as e:
        out[k]={"ok":False,"err":repr(e)[:300]}
json.dump(out,open("data/probe.json","w"),ensure_ascii=False,indent=1)
print(json.dumps(out,ensure_ascii=False)[:2000])
