"""每日收盘数据清单。GitHub Actions 运行，结果写入 data/daily/。"""
import json, urllib.request, datetime, os, gzip, csv, io, time
H={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"}
def get(u,tries=3):
    for i in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30).read().decode("utf-8","replace")
        except Exception as e:
            if i==tries-1: raise
            time.sleep(2)
def kline(sym,n=30):
    return json.loads(get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen={n}"))

INDEX={"上证":"sh000001","上证50":"sh000016","沪深300":"sh000300","中证1000":"sh000852","创业板指":"sz399006","科创50":"sh000688"}
ETF={"50ETF":"sh510050","300ETF":"sh510300","500ETF":"sh510500","科创50ETF":"sh588000","创业板ETF":"sz159915",
     "科创半导体588170":"sh588170","通信515880":"sh515880","影视516620":"sh516620","机器人562500":"sh562500","红利低波512890":"sh512890"}
TRACK={"中际旭创":"sz300308","美的集团":"sz000333","川投能源":"sh600674","长江电力":"sh600900"}

os.makedirs("data/daily",exist_ok=True)
ref=kline("sh000001",2)
day=ref[-1]["day"]
out={"date":day,"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
bj=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat()
if day!=bj:
    out["note"]=f"今天({bj})没有新K线，可能休市"
    json.dump(out,open(f"data/daily/{bj}_closed.json","w"),ensure_ascii=False,indent=1); raise SystemExit

def stat(sym,n=30):
    d=kline(sym,n); c=[float(x["close"]) for x in d]; v=[float(x["volume"]) for x in d]
    r={"close":c[-1],"chg%":round((c[-1]/c[-2]-1)*100,2),"5d%":round((c[-1]/c[-6]-1)*100,2)}
    r["ma5"]=round(sum(c[-5:])/5,4); r["ma20"]=round(sum(c[-20:])/20,4)
    r["above_ma5"]=c[-1]>=r["ma5"]; r["above_ma20"]=c[-1]>=r["ma20"]
    r["vol_ratio20"]=round(v[-1]/(sum(v[-21:-1])/20),2)
    return r
out["index"]={k:stat(s) for k,s in INDEX.items()}
out["etf"]={k:stat(s) for k,s in ETF.items()}
out["etf_alarm"]=[k for k,r in out["etf"].items() if r["vol_ratio20"]>=2.5 and k in("50ETF","300ETF","500ETF","科创50ETF","创业板ETF")]
out["track"]={k:stat(s) for k,s in TRACK.items()}

# 全A
rows=[]
for p in range(1,80):
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
try:
    j=json.loads(get("https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPTA_RZRQ_LSHJ&columns=ALL&pageSize=6&sortColumns=DIM_DATE&sortTypes=-1"))
    d=j["result"]["data"]
    out["margin"]=[{"date":x["DIM_DATE"][:10],"rzye_yi":round(x["RZYE"]/1e8),"rz_net_buy_yi":round(x.get("RZJME",0)/1e8,1)} for x in d]
except Exception as e:
    out["margin"]={"err":repr(e)[:200]}

json.dump(out,open(f"data/daily/{day}.json","w"),ensure_ascii=False,indent=1)
# 人读摘要
ix=out["index"]; b=out["breadth"]
lines=[f"## {day}",
 "指数："+"，".join(f"{k}{v['chg%']:+.2f}%" for k,v in ix.items()),
 f"全A：涨{b['up']} 跌{b['down']}，涨停{b['limit_up']} 跌停{b['limit_down']}，炸板率{b['broken_rate%']}%，成交约{b['amount_yi']}亿",
 "ETF量比："+"，".join(f"{k}{v['vol_ratio20']}" for k,v in out["etf"].items()),
 "宽基放量报警："+("、".join(out["etf_alarm"]) or "无"),
 "破5日线："+("、".join(k for k,v in {**out['etf'],**out['track']}.items() if not v['above_ma5']) or "无"),
]
if isinstance(out["margin"],list) and out["margin"]: m=out["margin"][0]; lines.append(f"融资余额（{m['date']}）：{m['rzye_yi']}亿，净买入{m['rz_net_buy_yi']}亿")
with open("data/daily_log.md","a",encoding="utf-8") as f: f.write("\n".join(lines)+"\n\n")
print("\n".join(lines))
