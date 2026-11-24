"""分批回填全A近300个交易日日K，可多次运行续跑。每次最多跑 BUDGET 秒，结果存 data/hist/part_*.csv.gz。
优先东方财富前复权，失败退回新浪（不复权，source 列标明）。"""
import json, urllib.request, gzip, csv, io, time, os, glob, concurrent.futures as cf
BUDGET=int(os.environ.get("BUDGET","13000")); t0=time.time()
H={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"}
def get(u,to=6,tries=2):
    for i in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=to).read().decode("utf-8","replace")
        except Exception: time.sleep(1)
    return ""
os.makedirs("data/hist",exist_ok=True)
done=set()
for f in glob.glob("data/hist/part_*.csv.gz"):
    for r in csv.DictReader(gzip.open(f,"rt",encoding="utf-8")): done.add(r["symbol"])
snap=sorted(glob.glob("data/snapshot/*.csv.gz"))[-1]
_rows=[r for r in csv.DictReader(gzip.open(snap,"rt",encoding="utf-8")) if r["symbol"] not in done]
_rows.sort(key=lambda r:-float(r.get("nmc") or 0))   # 流通市值大的先回填
syms=[r["symbol"] for r in _rows]
print("todo",len(syms),"done",len(done),flush=True)
def one(s):
    if time.time()-t0>BUDGET: return s,None,""
    secid=("1." if s.startswith("sh") else "0.")+s[2:]
    t=get(f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1&fields2=f51,f52,f53,f54,f55,f56,f57,f61&klt=101&fqt=1&end=20500101&lmt=300")
    try:
        kl=json.loads(t)["data"]["klines"]; return s,[k.split(",") for k in kl],"em_qfq"
    except Exception: pass
    t=get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={s}&scale=240&ma=no&datalen=300")
    try:
        kl=json.loads(t); return s,[[x["day"],x["open"],x["close"],x["high"],x["low"],x["volume"],"",""] for x in kl],"sina_raw"
    except Exception: return s,[],""
buf=io.StringIO(); w=csv.writer(buf); w.writerow(["symbol","day","open","close","high","low","volume","amount","turnover","source"])
n=ok=0
with cf.ThreadPoolExecutor(3) as ex:
    for s,rows,src in ex.map(one,syms):
        if rows is None: continue
        n+=1
        if rows: ok+=1; [w.writerow([s]+r+[src]) for r in rows]
        if n%300==0: print(n,ok,int(time.time()-t0),flush=True)
if ok:
    k=len(glob.glob("data/hist/part_*.csv.gz"))
    with gzip.open(f"data/hist/part_{k:03d}.csv.gz","wt",encoding="utf-8") as f: f.write(buf.getvalue())
print("this run",n,"ok",ok,"remaining",len(syms)-n)
