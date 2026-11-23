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
plan=json.load(open("data/plan.json",encoding="utf-8"))
days=sorted(f[:-5] for f in os.listdir("data/daily") if f.endswith(".json") and f[:4].isdigit() and len(f)==15)
prev=[d for d in days if d<today]
if not prev: raise SystemExit("no previous daily")
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
us={}
for k,secid in plan["us_watch"].items():
    try:
        j=json.loads(get(f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1&fields2=f51,f53&klt=101&fqt=1&end=20500101&lmt=3"))
        kl=[x.split(",") for x in j["data"]["klines"]]
        us[k]={"date":kl[-1][0],"close":float(kl[-1][1]),"chg%":round((float(kl[-1][1])/float(kl[-2][1])-1)*100,2)}
    except Exception as e: us[k]={"err":repr(e)[:120]}
out["us"]=us
s=us.get("SOXX",{}).get("chg%")
if s is None: exp="美股数据缺失"
elif s>2: exp="SOXX>+2%：科创大概率高开（历史76%），但开盘后均值-0.17%，不追高开"
elif s<-2: exp="SOXX<-2%：科创大概率低开（历史86%），开盘后均值+0.37%，低开翻绿是低吸机会"
else: exp="SOXX在±2%内：对开盘影响小"
out["open_expectation"]=exp

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
   "隔夜美股："+"，".join(f"{k} {v.get('chg%','?')}%" for k,v in us.items())+f"。{exp}","","ETF梯子（碰到买价按买价成交，同日+2%卖）："]
for s_,x in lad.items(): L.append(f"- {x['name']}：前收{x['prev_close']}，5日线{x['ma5']}，买价 "+"、".join(f"{p}×{n}" for p,n in x['buy_levels']))
L+=["","他点名的票（观察期内）："]+[f"- {x['name']} {x['symbol']}：{x['said']}｜判据：{x['check']}｜到期{x['due'] or '无'}" for x in out["mentions_open"]]
L+=["","进行中的预测："]+[f"- {x['id']}（{x['by']}）{x['claim']}｜到期{x['due'] or '无'}｜{x['backtest']}" for x in out["predictions_open"]]
open(f"data/premarket/{today}.md","w",encoding="utf-8").write("\n".join(L)+"\n")
print("\n".join(L))
