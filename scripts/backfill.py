"""一次性回填全A近300个交易日日K（前复权），供选股器计算年线、箱体、回撤等。输出 data/hist/all.csv.gz"""
import json, urllib.request, gzip, csv, io, time, os, glob, concurrent.futures as cf
H={"User-Agent":"Mozilla/5.0","Referer":"https://quote.eastmoney.com"}
def get(u):
    for i in range(4):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=15).read().decode("utf-8","replace")
        except Exception:
            time.sleep(1.5*(i+1))
    return ""
snap=sorted(glob.glob("data/snapshot/*.csv.gz"))[-1]
syms=[r["symbol"] for r in csv.DictReader(gzip.open(snap,"rt",encoding="utf-8"))]
print("symbols",len(syms),flush=True)
def secid(s):
    if s.startswith("sh"): return "1."+s[2:]
    return "0."+s[2:]   # sz 和 bj 都用 0.
def one(s):
    t=get(f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid(s)}&fields1=f1&fields2=f51,f52,f53,f54,f55,f56,f57,f61&klt=101&fqt=1&end=20500101&lmt=300")
    try: kl=json.loads(t)["data"]["klines"]
    except Exception: return s,[]
    return s,[k.split(",") for k in kl]
os.makedirs("data/hist",exist_ok=True)
buf=io.StringIO(); w=csv.writer(buf); w.writerow(["symbol","day","open","close","high","low","volume","amount","turnover"])
ok=bad=0
with cf.ThreadPoolExecutor(4) as ex:
    for i,(s,rows) in enumerate(ex.map(one,syms)):
        if rows: ok+=1; [w.writerow([s]+r) for r in rows]
        else: bad+=1
        if i%500==0: print(i,ok,bad,flush=True)
with gzip.open("data/hist/all.csv.gz","wt",encoding="utf-8") as f: f.write(buf.getvalue())
print("done ok",ok,"bad",bad)
