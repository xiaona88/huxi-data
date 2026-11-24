"""光模块（CPO）板块扫描：用手工维护的成分列表 + 新浪实时行情 + 新浪日K 60日涨跌 + 前一日快照的流通市值。"""
import json, urllib.request, datetime, os, gzip, csv, glob
H={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"}
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=15).read().decode("gbk","replace")
L="sz300308 sz300502 sz300394 sz002281 sz000988 sh603083 sz300548 sz301205 sz300570 sh688313 sh688498 sh688205 sz300620 sh688195 sz002902 sz003031 sh688048 sh600105 sh600487 sz002491 sz001267 sz002384 sz300757 sh688025 sz300408 sz301486 sz002222 sh688167 sz301183 sh603042 sh688498".split()
L=list(dict.fromkeys(L))
snap=sorted(glob.glob("data/snapshot/*.csv.gz"))[-1]
nmc={r["symbol"]:float(r["nmc"] or 0)/1e4 for r in csv.DictReader(gzip.open(snap,"rt",encoding="utf-8"))}
q={}
t=get("https://hq.sinajs.cn/list="+",".join(L))
for line in t.strip().split("\n"):
    k=line.split("=")[0].split("_")[-1]; v=line.split('"')[1].split(",")
    if len(v)>5: q[k]={"name":v[0],"open":float(v[1]),"prev":float(v[2]),"now":float(v[3]),"high":float(v[4]),"low":float(v[5])}
out=[]
for s in L:
    if s not in q: continue
    x=q[s]
    try:
        d=json.loads(urllib.request.urlopen(urllib.request.Request(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={s}&scale=240&ma=no&datalen=80",headers=H),timeout=15).read())
        c=[float(z["close"]) for z in d if z["day"]<datetime.date.today().isoformat() or True]
        c=[float(z["close"]) for z in d]
        ref=x["prev"]; r60=round((ref/c[-61]-1)*100,1) if len(c)>61 else None
        hi=max(float(z["high"]) for z in d); off=round((ref/hi-1)*100,1)
    except Exception: r60=off=None
    out.append({"symbol":s,"name":x["name"],"float_yi":round(nmc.get(s,0)),"open%":round((x["open"]/x["prev"]-1)*100,2) if x["open"] else None,"now%":round((x["now"]/x["prev"]-1)*100,2),"60d%":r60,"from80dHigh%":off})
bj=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
os.makedirs("data/scan",exist_ok=True)
json.dump({"at_bj":bj.isoformat(timespec="seconds"),"stocks":out},open(f"data/scan/cpo_{bj.strftime('%Y-%m-%d_%H%M')}.json","w"),ensure_ascii=False,indent=0)
for o in sorted(out,key=lambda z:z["float_yi"]): print(o)
