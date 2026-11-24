"""每日收盘数据清单。GitHub Actions 运行，结果写入 data/daily/。"""
import json, urllib.request, datetime, os, gzip, csv, io, time
H={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"}
def get(u,tries=3):
    for i in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=15).read().decode("utf-8","replace")
        except Exception as e:
            if i==tries-1: raise
            time.sleep(2)
def kline(sym,n=30):
    """东方财富日K（盘中即含当天），失败时退回新浪。"""
    secid=("1." if sym.startswith("sh") else "0.")+sym[2:]
    try:
        j=json.loads(get(f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1&fields2=f51,f52,f53,f54,f55,f56&klt=101&fqt=1&end=20500101&lmt={n}"))
        return [dict(zip(["day","open","close","high","low","volume"],k.split(","))) for k in j["data"]["klines"]]
    except Exception:
        return json.loads(get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen={n}"))

INDEX={"上证":"sh000001","上证50":"sh000016","沪深300":"sh000300","中证1000":"sh000852","创业板指":"sz399006","科创50":"sh000688"}
ETF={"50ETF":"sh510050","300ETF":"sh510300","500ETF":"sh510500","科创50ETF":"sh588000","创业板ETF":"sz159915",
     "科创半导体588170":"sh588170","通信515880":"sh515880","影视516620":"sh516620","机器人562500":"sh562500","红利低波512890":"sh512890"}
TRACK={"中际旭创":"sz300308","美的集团":"sz000333","川投能源":"sh600674","长江电力":"sh600900"}

os.makedirs("data/daily",exist_ok=True)
_now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
bj=_now.date().isoformat()
if (_now.hour,_now.minute)<(15,5) and not os.environ.get("FORCE"): raise SystemExit("before close, skip")
if os.path.exists(f"data/daily/{bj}.json") and not os.environ.get("FORCE"): raise SystemExit("already done today")
ref=kline("sh000001",2)
day=ref[-1]["day"]
if day!=bj:
    m=json.loads(get("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000001&scale=5&ma=no&datalen=5"))
    if m and m[-1]["day"].startswith(bj): day=bj
out={"date":day,"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
bj=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat()
if day!=bj:
    out["note"]=f"今天({bj})没有新K线，可能休市"
    print(out["note"]); raise SystemExit

def today_from_5min(sym):
    """用新浪5分钟线拼出当天日K（新浪日K收盘后要晚些才更新）。"""
    m=json.loads(get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sym}&scale=5&ma=no&datalen=60"))
    t=[x for x in m if x["day"].startswith(day)]
    if not t: return None
    return {"day":day,"open":t[0]["open"],"close":t[-1]["close"],"high":str(max(float(x["high"]) for x in t)),
            "low":str(min(float(x["low"]) for x in t)),"volume":str(sum(float(x["volume"]) for x in t))}
def stat(sym,n=30):
    print("stat",sym,flush=True)
    time.sleep(0.6)
    d=kline(sym,n)
    if d[-1]["day"]!=day:
        try:
            b=today_from_5min(sym)
            if b: d=d+[b]
        except Exception as e: print("5min fail",sym,e,flush=True)
    c=[float(x["close"]) for x in d]; v=[float(x["volume"]) for x in d]
    r={"close":c[-1],"chg%":round((c[-1]/c[-2]-1)*100,2),"5d%":round((c[-1]/c[-6]-1)*100,2)}
    r["ma5"]=round(sum(c[-5:])/5,4); r["ma20"]=round(sum(c[-20:])/20,4)
    r["above_ma5"]=c[-1]>=r["ma5"]; r["above_ma20"]=c[-1]>=r["ma20"]
    r["vol_ratio20"]=round(v[-1]/(sum(v[-21:-1])/20),2)
    r["data_day"]=d[-1]["day"]
    if d[-1]["day"]!=day: r["STALE"]=True
    return r
out["index"]={k:stat(s) for k,s in INDEX.items()}
out["etf"]={k:stat(s) for k,s in ETF.items()}
out["etf_alarm"]=[k for k,r in out["etf"].items() if r["vol_ratio20"]>=2.5 and k in("50ETF","300ETF","500ETF","科创50ETF","创业板ETF")]
out["track"]={k:stat(s) for k,s in TRACK.items()}

# 全A
rows=[]
for p in range(1,80):
    if p%10==1: print("page",p,flush=True)
    a=json.loads(get(f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page={p}&num=100&sort=symbol&asc=1&node=hs_a") or "[]")
    if not a: break
    rows+=a
def lim(r):
    c=r["code"]; n=r["name"]
    if r["symbol"].startswith("bj"): return 0.30
    if "ST" in n: return 0.05
    if c.startswith(("300","301","688","689")): return 0.20
    return 0.10
up=dn=flat=zt=dt=zb=0; tot_amt=0.0
for r in rows:
    try:
        pc=float(r["settlement"]); t=float(r["trade"]); h=float(r["high"]); l=float(r["low"])
    except: continue
    if pc<=0 or t<=0: continue
    tot_amt+=float(r.get("amount") or 0)
    L=lim(r); upl=round(pc*(1+L)+1e-9,2); dnl=round(pc*(1-L)+1e-9,2)
    if t>pc: up+=1
    elif t<pc: dn+=1
    else: flat+=1
    if t>=upl: zt+=1
    elif h>=upl: zb+=1
    if t<=dnl: dt+=1
out["breadth"]={"stocks":len(rows),"up":up,"down":dn,"flat":flat,"limit_up":zt,"limit_down":dt,"broken_limit":zb,
  "broken_rate%":round(zb/(zt+zb)*100,1) if zt+zb else None,"amount_yi":round(tot_amt/1e8)}
# 原始快照
buf=io.StringIO(); w=csv.writer(buf)
keys=["symbol","name","trade","settlement","open","high","low","volume","amount","changepercent","turnoverratio","nmc","mktcap"]
w.writerow(keys); [w.writerow([r.get(k) for k in keys]) for r in rows]
os.makedirs("data/snapshot",exist_ok=True)
with gzip.open(f"data/snapshot/{day}.csv.gz","wt",encoding="utf-8") as f: f.write(buf.getvalue())

# 融资
print("margin",flush=True)
try:
    j=json.loads(get("https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPTA_RZRQ_LSHJ&columns=ALL&pageSize=6&sortColumns=DIM_DATE&sortTypes=-1"))
    d=j["result"]["data"]
    out["margin"]=[{"date":x["DIM_DATE"][:10],"rzye_yi":round(x["RZYE"]/1e8),"rz_net_buy_yi":round(x.get("RZJME",0)/1e8,1)} for x in d]
except Exception as e:
    out["margin"]={"err":repr(e)[:200]}


# ---- 对账盘前冻结 ----
def board(sym):
    if sym.startswith("bj"): return "北交"
    c=sym[2:]
    if c.startswith(("688","689")): return "科创"
    if c.startswith(("300","301")): return "创业"
    return "沪主板" if sym.startswith("sh") else "深主板"
bavg={}
for r in rows:
    try: bavg.setdefault(board(r["symbol"]),[]).append(float(r["changepercent"]))
    except: pass
bavg={k:round(sum(v)/len(v),2) for k,v in bavg.items()}
out["board_avg%"]=bavg
pm=f"data/premarket/{day}.json"
if os.path.exists(pm):
    P=json.load(open(pm,encoding="utf-8")); R={"frozen_at_bj":P["frozen_at_bj"]}
    upr=round(b["up"]/max(1,b["up"]+b["down"])*100,1)
    g=P["gate"]["闸门结论"]
    R["gate"]={"盘前":g,"实际上涨家数占比%":upr,"判定":("对" if (g=="偏强" and upr>50) or (g=="偏弱" and upr<50) else ("不判" if g=="中性" else "错"))}
    try:
        m=json.loads(get("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000688&scale=5&ma=no&datalen=60"))
        t=[x for x in m if x["day"].startswith(day)]
        pc=out["index"]["科创50"]["close"]/(1+out["index"]["科创50"]["chg%"]/100)
        R["kc50_open_gap%"]=round((float(t[0]["open"])/pc-1)*100,2) if t else None
    except Exception as e: R["kc50_open_gap%"]=None
    R["open_expectation"]=P.get("open_expectation")
    lad={}
    for sym,x in P["etf_ladders"].items():
        try:
            m=json.loads(get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sym}&scale=5&ma=no&datalen=60"))
            bars=[y for y in m if y["day"].startswith(day)]
        except Exception: bars=[]
        fills=[]; 
        for price,n in sorted(x["buy_levels"],key=lambda z:-z[0]):
            for i,y in enumerate(bars):
                if float(y["low"])<=price:
                    tp=price*(1+x["take_profit"]); sold=None
                    for z in bars[i+1:]:
                        if float(z["high"])>=tp: sold=round(tp,4); break
                    last=float(bars[-1]["close"])
                    fills.append({"buy":price,"n":n,"at":y["day"][11:16],"sell":sold,"pnl%":round(((sold or last)/price-1)*100,2),"closed":sold is not None})
                    break
        lad[x["name"]]={"low":min([float(y["low"]) for y in bars]) if bars else None,"high":max([float(y["high"]) for y in bars]) if bars else None,"fills":fills}
    R["etf_ladders"]=lad
    md=[]
    rowmap={r["symbol"]:r for r in rows}
    for x in P.get("mentions_open",[]):
        r=rowmap.get(x["symbol"])
        if not r: continue
        try:
            chg=float(r["changepercent"]); bd=board(x["symbol"])
            item={"name":x["name"],"symbol":x["symbol"],"chg%":round(chg,2),"board":bd,"board_avg%":bavg.get(bd),"excess%":round(chg-bavg.get(bd,0),2)}
            if x["due"]==day and "最高价" in x["check"]:
                item["high_vs_prev%"]=round((float(r["high"])/float(r["settlement"])-1)*100,2)
            md.append(item)
        except Exception: pass
    R["mentions"]=md
    out["reconcile"]=R

json.dump(out,open(f"data/daily/{day}.json","w"),ensure_ascii=False,indent=1)
# 人读摘要
ix=out["index"]; b=out["breadth"]
lines=[f"## {day}",
 "指数："+"，".join(f"{k}{v['chg%']:+.2f}%" for k,v in ix.items()),
 f"全A：涨{b['up']} 跌{b['down']}，涨停{b['limit_up']} 跌停{b['limit_down']}，炸板率{b['broken_rate%']}%，成交约{b['amount_yi']}亿",
 "ETF量比："+"，".join(f"{k}{v['vol_ratio20']}" for k,v in out["etf"].items()),
 "宽基放量报警："+("、".join(out["etf_alarm"]) or "无"),
 "破5日线："+("、".join(k for k,v in {**out['etf'],**out['track']}.items() if not v['above_ma5'] and not v.get('STALE')) or "无"),
 "数据缺当天（未计入）："+("、".join(k for k,v in {**out['index'],**out['etf'],**out['track']}.items() if v.get('STALE')) or "无"),
]
if "reconcile" in out:
    R=out["reconcile"]; lines.append(f"盘前对账：闸门{R['gate']['盘前']}，实际上涨占比{R['gate']['实际上涨家数占比%']}%（{R['gate']['判定']}）；科创50开盘{R.get('kc50_open_gap%')}%")
    for k,v in R["etf_ladders"].items():
        lines.append(f"  梯子 {k}：区间{v['low']}~{v['high']}，"+("；".join(f"{f['buy']}买@{f['at']}"+(f"→{f['sell']}卖" if f['closed'] else "→未卖")+f"({f['pnl%']}%)" for f in v['fills']) or "未触发"))
    for x in R["mentions"]: lines.append(f"  点名 {x['name']}：{x['chg%']}% vs {x['board']}{x['board_avg%']}%（超额{x['excess%']}）"+(f"，最高{x['high_vs_prev%']}%" if 'high_vs_prev%' in x else ""))
if isinstance(out["margin"],list) and out["margin"]: m=out["margin"][0]; lines.append(f"融资余额（{m['date']}）：{m['rzye_yi']}亿，净买入{m['rz_net_buy_yi']}亿")
import re
log=open("data/daily_log.md",encoding="utf-8").read() if os.path.exists("data/daily_log.md") else ""
log=re.sub(r"## "+re.escape(day)+r"\n.*?(?=\n## |\Z)","",log,flags=re.S).strip()
open("data/daily_log.md","w",encoding="utf-8").write((log+"\n\n" if log else "")+"\n".join(lines)+"\n")
print("\n".join(lines))
