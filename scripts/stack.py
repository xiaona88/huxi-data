"""他的选股六层，每日收盘后自动跑（第1层分钱=纸面账户I只用短线小仓规则）。
2 大势闸门：全A等权近5日没有跌超3%（且底部信号日另算）
3 主线：所在新浪行业近5日等权涨幅排前20%
4 位置：近30日有涨停、今天回踩到涨停收盘价±1%且没跌破、成交量≤前20日均量0.7倍
5 价位：明天挂今天收盘价，碰到才买；保护位=涨停价×0.98
6 卖法：收盘跌破保护位就走；冲高+8%先卖一半；最多拿5个交易日
每天最多3只（行业最热的优先）。全部候选（只满足第4层的）也存下来，用来对照他实际挑了哪只。
回测（2025-09~2026-11，含费用）：每笔平均-0.12%，相对同板块+0.14%，赚钱占35%，最差-18.6%（①，打平附近，还没证明能赚钱）。"""
import pandas as pd, numpy as np, glob, json, os, datetime, gzip
bj=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
today=os.environ.get("TODAY") or bj.date().isoformat()
if not os.environ.get("TODAY") and (bj.hour,bj.minute)<(15,10): raise SystemExit("before close")
parts=[pd.read_csv(f,usecols=["symbol","day","open","close","high","low","volume"]) for f in glob.glob("data/hist/*.csv.gz")]
for f in sorted(glob.glob("data/snapshot/*.csv.gz")):
    s=pd.read_csv(f); dday=os.path.basename(f)[:10]
    s=s.rename(columns={"trade":"close"}); s["day"]=dday
    parts.append(s[["symbol","day","open","close","high","low","volume"]])
df=pd.concat(parts)
df=df[~df.symbol.str.startswith("bj")&(df.day<=today)]
for c in ["open","close","high","low","volume"]: df[c]=pd.to_numeric(df[c],errors="coerce")
df=df.dropna().query("close>0").drop_duplicates(["symbol","day"],keep="last").sort_values(["symbol","day"])
df=df[df.day>=sorted(df.day.unique())[-70]]
if df.day.max()!=today: raise SystemExit(f"no data for {today}, latest {df.day.max()}")
g=df.groupby("symbol",sort=False)
df["pc"]=g.close.shift(1); df["ret"]=df.close/df.pc-1
lim=np.where(df.symbol.str[2:4].isin(["30","68"]),0.20,0.10)
df["zt"]=df.close>=np.round(df.pc*(1+lim),2)-0.011
df["ztp"]=df.close.where(df.zt); df["lastzt"]=g.ztp.transform(lambda s:s.shift(1).ffill(limit=29))
df["v20"]=g.volume.transform(lambda s:s.shift(1).rolling(20).mean())
df["r5"]=g.close.transform(lambda s:s/s.shift(5)-1)
ind=json.load(open("data/ref/industry.json",encoding="utf-8")); df["ind"]=df.symbol.map(ind)
t=df[df.day==today].copy()
it=t[t.ind.notna()].groupby("ind").r5.agg(["mean","size"]); it=it[it["size"]>=8]; it["rk5"]=it["mean"].rank(pct=True)
t["rk5"]=t.ind.map(it.rk5)
mk=df[df.symbol.isin(t.symbol)].groupby("day").ret.mean().tail(5); m5=float((1+mk).prod()-1)
gate=m5>-0.03
pos=t.lastzt.notna()&(t.low<=t.lastzt*1.01)&(t.close>=t.lastzt*0.99)&(t.volume<=0.7*t.v20)&(abs(t.ret)<0.25)
cands=t[pos].copy(); cands["main"]=cands.rk5>=0.8
names={}
try:
    sn=pd.read_csv(sorted(glob.glob("data/snapshot/*.csv.gz"))[-1]); names=dict(zip(sn.symbol,sn.name))
except Exception: pass
picks=cands[cands.main].sort_values("rk5",ascending=False)
picks=picks[~picks.symbol.map(lambda s:"ST" in str(names.get(s,"")))].head(3) if gate else picks.head(0)
def row(r): return {"symbol":r.symbol,"name":names.get(r.symbol,""),"ind":r.ind if isinstance(r.ind,str) else "","close":round(r.close,3),"limit_buy":round(r.close,3),"stop":round(r.lastzt*0.98,3),"lastzt":round(r.lastzt,3),"ind_rank5":None if pd.isna(r.rk5) else round(r.rk5,2)}
out={"date":today,"gate":{"全A等权5日%":round(m5*100,2),"通过":bool(gate)},"picks":[row(r) for r in picks.itertuples()],
     "candidates_n":int(len(cands)),"candidates":[row(r) for r in cands.sort_values("rk5",ascending=False).itertuples()][:200],
     "rules":"明天挂limit_buy，碰到才买；收盘跌破stop就走；冲高+8%先卖一半；最多5个交易日"}
os.makedirs("data/stack",exist_ok=True)
json.dump(out,open(f"data/stack/{today}.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print(json.dumps({k:out[k] for k in ["date","gate","picks","candidates_n"]},ensure_ascii=False,indent=1))
