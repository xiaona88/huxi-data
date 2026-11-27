"""盘前冻结：北京时间开盘前运行，生成当天名单并提交（提交时间即冻结证明）。只用前一交易日数据和隔夜美股，规则全部机械化。"""
import json, os, datetime, urllib.request, time
H={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"}
def get(u):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=15).read().decode("utf-8","replace")
        except Exception:
            if i==2: raise
            time.sleep(2)
bj=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
today=os.environ.get("TODAY") or bj.date().isoformat()
os.makedirs("data/premarket",exist_ok=True)
_f=f"data/premarket/{today}.json"
if os.path.exists(_f) and not os.environ.get("TODAY"):
    _o=json.load(open(_f,encoding="utf-8"))
    if _o.get("frozen_at_bj","")[:10]==today: print("already frozen this morning"); raise SystemExit(0)
if not os.environ.get("TODAY") and (bj.hour,bj.minute)>=(9,25):
    print("too late to freeze (>=09:25), skip"); raise SystemExit(0)
plan=json.load(open("data/plan.json",encoding="utf-8"))
days=sorted(f[:-5] for f in os.listdir("data/daily") if f.endswith(".json") and f[:4].isdigit() and len(f)==15)
prev=[d for d in days if d<today]
if not prev: print("no previous daily"); raise SystemExit(0)
pd=prev[-1]; D=json.load(open(f"data/daily/{pd}.json",encoding="utf-8"))
out={"date":today,"frozen_at_bj":bj.isoformat(timespec="seconds"),"based_on":pd}

# 1 闸门（全部来自前一日数据）
ix=D["index"]; b=D["breadth"]
above5=[k for k,v in ix.items() if v["above_ma5"]]; above20=[k for k,v in ix.items() if v["above_ma20"]]
m=D.get("margin") if isinstance(D.get("margin"),list) else []
neg=0
for x in m:
    if x["rz_net_buy_yi"]<0: neg+=1
    else: break
gate={"指数站上5日线":above5,"指数站上20日线":above20,"成交亿":b["amount_yi"],"涨停":b["limit_up"],"跌停":b["limit_down"],"炸板率%":b["broken_rate%"],
      "融资连续净流出天数":neg,"20cm条件(他原话:需2万亿)":"满足" if b["amount_yi"]>=20000 else "不满足"}
score=0
score+= 1 if len(above20)>=3 else -1
score+= 1 if (b["broken_rate%"] or 99)<25 else -1
score+= -1 if neg>=3 else 0
gate["闸门结论"]="偏强" if score>=1 else ("偏弱" if score<=-1 else "中性")
gate["规则"]="指数站上20日线≥3个+1否则-1；炸板率<25%+1否则-1；融资连续净流出≥3天-1（规则是我们定的，①）"
out["gate"]=gate

# 2 隔夜美股（只用来预判开盘方向，③：美股只影响开盘，不影响收盘）
def _get_ref(u,ref):
    return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":ref}),timeout=20).read().decode("utf-8","replace")
def _us_sina(k):
    # 新浪美股日K（11-26 探测在 GitHub 机器上可用；东方财富 push2his 对境外 IP 经常直接断开连接）
    t=_get_ref(f"https://stock.finance.sina.com.cn/usstock/api/jsonp.php/x/US_MinKService.getDailyK?symbol={k}&type=daily","https://stock.finance.sina.com.cn/")
    j=json.loads(t[t.index("(")+1:t.rindex(")")])
    return [(x["d"],float(x["c"])) for x in j[-3:]]
def _us_em(secid):
    j=json.loads(_get_ref(f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1&fields2=f51,f53&klt=101&fqt=1&end=20500101&lmt=3","https://quote.eastmoney.com/"))
    return [(a,float(b)) for a,b in (x.split(",")[:2] for x in j["data"]["klines"])]
us={}
for k,secid in plan["us_watch"].items():
    errs=[]
    for src,fn in (("sina",lambda:_us_sina(k)),("eastmoney",lambda:_us_em(secid))):
        for i in range(3):
            try:
                kl=fn()
                us[k]={"date":kl[-1][0],"close":kl[-1][1],"chg%":round((kl[-1][1]/kl[-2][1]-1)*100,2),"src":src}
                break
            except Exception as e:
                errs.append(f"{src}#{i+1}:{repr(e)[:60]}"); time.sleep(3)
        if k in us: break
    if k not in us: us[k]={"err":"; ".join(errs)[:300]}
    time.sleep(1.5)   # 逐个查、隔开，避免被限流
out["us"]=us
# 美股日期核对：应为北京今天的前一个美东自然日；更早说明美股休市（或数据没更新）
_d=(bj-datetime.timedelta(hours=13)).date()   # 北京早上 ≈ 美东前一天晚上（夏令时差12小时，偏差不影响日期）
while _d.weekday()>=5: _d-=datetime.timedelta(days=1)   # 周一早上对应美东周五
_et_prev=_d.isoformat()
_ds=sorted({v["date"] for v in us.values() if "date" in v})
if _ds and _ds[-1]<_et_prev:
    out["us_date_note"]=f"美股最新交易日是{_ds[-1]}，昨晚（美东{_et_prev}）没有新数据（休市或未更新），隔夜信号沿用旧数据，不算新信号"
elif _ds: out["us_date_note"]=f"美股数据日期{_ds[-1]}，是昨晚的交易日"
s=us.get("SOXX",{}).get("chg%")
if s is None: exp="美股数据缺失"
elif out.get("us_date_note","").startswith("美股最新交易日"): exp="昨晚美股没有交易：今天没有隔夜信号"
elif s>2: exp="SOXX>+2%：科创大概率高开（历史76%），但开盘后均值-0.17%，不追高开"
elif s<-2: exp="SOXX<-2%：科创大概率低开（历史86%），开盘后均值+0.37%，低开翻绿是低吸机会"
else: exp="SOXX在±2%内：对开盘影响小"
out["open_expectation"]=exp

# 2b 韩国开盘（KOSPI 北京08:00开盘，早于A股1.5小时）。回测2024-03~2026-11（N≈640）：韩开盘跳空与A股开盘跳空相关约0.5，
# 扣掉美股后仍约0.44，美股休市日约0.66~0.70；与A股开盘后（收/开）相关≈0。韩高开≥1%：A股高开约83%，科创50开盘后均-0.30%；
# 韩低开≤-1%：A股低开约92%，科创50开盘后均+0.18%。→ 和美股一样只决定怎么开，不决定怎么收。
kos={}
try:
    _t=_get_ref("https://hq.sinajs.cn/list=b_KOSPI","https://finance.sina.com.cn/")
    _f=_t.split('"')[1].split(",")
    _o,_pc,_p=float(_f[8]),float(_f[9]),float(_f[1])
    kos={"open_gap%":round((_o/_pc-1)*100,2),"now%":round((_p/_pc-1)*100,2),"time":_f[7],"date":_f[6]}
except Exception as e: kos={"err":repr(e)[:120]}
out["kospi"]=kos
g=kos.get("open_gap%")
if g is None: kexp="韩国数据缺失"
elif kos.get("date")!=today: kexp="韩国今天没开盘（休市或数据未更新）"
elif g>=1: kexp=f"韩国高开{g}%：A股大概率高开（历史约83%），但科创50开盘后均-0.30%，不追高开"
elif g<=-1: kexp=f"韩国低开{g}%：A股大概率低开（历史约92%），科创50开盘后均+0.18%"
else: kexp=f"韩国开盘{g}%，平开附近：对A股开盘影响小"
out["kospi_expectation"]=kexp

# 3 ETF梯子
lad={}
for sym,cfg in plan["etf_ladders"].items():
    name=cfg["name"]; v=D["etf"].get(name,{})
    if "buy" in cfg: levels=cfg["buy"]
    else: levels=[[round(v.get("ma5",0)*(1+cfg["buy_ma5_dev"]),3),1]] if v else []
    lad[sym]={"name":name,"prev_close":v.get("close"),"ma5":v.get("ma5"),"buy_levels":levels,"take_profit":plan["t_take_profit"],"source":cfg["source"]}
out["etf_ladders"]=lad

# 4 他的点名票（按 mentions.json，仍在观察期的）
ms=json.load(open("data/mentions.json",encoding="utf-8"))
out["mentions_open"]=[x for x in ms if (not x["due"]) or x["due"]>=today]
out["predictions_open"]=[x for x in json.load(open("data/predictions.json",encoding="utf-8")) if (not x["due"]) or x["due"]>=today]

json.dump(out,open(f"data/premarket/{today}.json","w"),ensure_ascii=False,indent=1)
L=[f"# 盘前冻结 {today}（北京 {bj.strftime('%H:%M')} 冻结，依据 {pd} 收盘）","",
   f"闸门：{gate['闸门结论']}。站上20日线的指数：{'、'.join(above20) or '无'}；炸板率{gate['炸板率%']}%；成交{gate['成交亿']}亿（20cm条件{gate['20cm条件(他原话:需2万亿)']}）；融资连续净流出{neg}天。",
   "隔夜美股："+"，".join(f"{k} {v.get('chg%','?')}%" for k,v in us.items())+f"（{out.get('us_date_note','日期未知')}）。{exp}",f"韩国开盘：{kexp}（当前{kos.get('now%','?')}%，{kos.get('time','')}）","","ETF梯子（碰到买价按买价成交，同日+2%卖）："]
for s_,x in lad.items(): L.append(f"- {x['name']}：前收{x['prev_close']}，5日线{x['ma5']}，买价 "+"、".join(f"{p}×{n}" for p,n in x['buy_levels']))
L+=["","他点名的票（观察期内）："]+[f"- {x['name']} {x['symbol']}：{x['said']}｜判据：{x['check']}｜到期{x['due'] or '无'}" for x in out["mentions_open"]]
L+=["","进行中的预测："]+[f"- {x.get('id')}（{x.get('by') or x.get('who','')}）{x.get('claim','')}｜到期{x.get('due') or '无'}｜{x.get('backtest') or x.get('basis','')}" for x in out["predictions_open"]]
open(f"data/premarket/{today}.md","w",encoding="utf-8").write("\n".join(L)+"\n")
print("\n".join(L))
