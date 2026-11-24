# 测试：五档盘口、逐笔成交、个股分钟资金流、筹码原料（换手率）能否从云端拿到
import json, urllib.request
def get(u,ref="https://finance.sina.com.cn/"):
    return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":ref}),timeout=20).read()
out={}
tests={
 "五档盘口_sina":("https://hq.sinajs.cn/list=sh588170,sz300308","https://finance.sina.com.cn/"),
 "逐笔成交_sina":("https://vip.stock.finance.sina.com.cn/quotes_service/view/CN_TransListV2.php?num=20&symbol=sz300308","https://finance.sina.com.cn/"),
 "分钟资金流_em":("https://push2.eastmoney.com/api/qt/stock/fflow/kline/get?lmt=0&klt=1&secid=0.300308&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57","https://data.eastmoney.com/"),
 "日资金流_em":("https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=5&klt=101&secid=0.300308&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57","https://data.eastmoney.com/"),
 "换手率_em":("https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=0.300308&fields1=f1&fields2=f51,f53,f61&klt=101&fqt=1&lmt=5&end=20500101","https://quote.eastmoney.com/"),
 "五档_em":("https://push2.eastmoney.com/api/qt/stock/get?secid=0.300308&fields=f19,f20,f17,f18,f39,f40,f37,f38","https://quote.eastmoney.com/"),
}
for k,(u,r) in tests.items():
    try: b=get(u,r); t=b.decode("gbk","ignore") if "sina" in u else b.decode("utf8","ignore"); out[k]={"ok":True,"len":len(t),"head":t[:400]}
    except Exception as e: out[k]={"ok":False,"err":repr(e)[:150]}
json.dump(out,open("data/probe.json","w"),ensure_ascii=False,indent=1)
for k,v in out.items(): print(k,v)
