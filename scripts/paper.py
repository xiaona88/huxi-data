"""纸面账户每日结算，规则见 data/paper/rules.md。在 daily.py 之后运行。"""
import json, os, urllib.request, datetime, time
H={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"}
def get(u):
    for i in range(3):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=15).read())
        except Exception:
            if i==2: raise
            time.sleep(2)
def daily(s,n=40): return get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={s}&scale=240&ma=no&datalen={n}")
def m5(s): return get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={s}&scale=5&ma=no&datalen=60")
FEE=0.00025; MINFEE=0.0; STAMP=0.0005; CAP0=100000.0; START=os.environ.get("PAPER_START","2026-11-25"); D=os.environ.get("PAPER_DIR","data/paper")
bj=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
today=os.environ.get("TODAY") or bj.date().isoformat()
if today<START: raise SystemExit("not started")
# 11-25 修：北京时间收盘前不结算（之前在凌晨跑过一次，把空的一天记成"已结算"）
if not os.environ.get("TODAY") and (bj.hour,bj.minute)<(15,5): raise SystemExit("before close, skip")
SP=f"{D}/state.json"; os.makedirs(D,exist_ok=True)
st=json.load(open(SP)) if os.path.exists(SP) else {"D":{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[]},"A":{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[]},"B":{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[],"bought":False},"C":{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[]},"last":""}
if st["last"]==today: raise SystemExit("already settled today")
st.setdefault("F",{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[],"bought":False})
log=[]
def bars(s):
    b=[x for x in m5(s) if x["day"].startswith(today)]
    return [{"t":x["day"][11:16],"o":float(x["open"]),"h":float(x["high"]),"l":float(x["low"]),"c":float(x["close"])} for x in b]
def prev_close_and_ma20(s):
    d=[x for x in daily(s) if x["day"]<today]
    c=[float(x["close"]) for x in d]
    return c[-1], sum(c[-20:])/20
def equity(acc,prices): return acc["cash"]+sum(p["sh"]*prices.get(k,p.get("last",0)) for k,p in acc["pos"].items())
def buy(acc,s,amt_or_sh,price,why,by_shares=False,prices=None,cap=None):
    sh=amt_or_sh if by_shares else int(amt_or_sh/price/100)*100
    if sh<=0: return 0
    cost=sh*price+max(MINFEE,sh*price*FEE)
    if cap is not None:
        eq=equity(acc,prices); held=eq-acc["cash"]
        if held+sh*price>cap*eq: return 0
    if cost>acc["cash"]: return 0
    acc["cash"]-=cost; p=acc["pos"].setdefault(s,{"sh":0,"cost":0.0})
    p["cost"]=(p["cost"]*p["sh"]+sh*price)/(p["sh"]+sh); p["sh"]+=sh
    log.append(f"{today} {why} 买 {s} {sh}份 @{price:.3f}"); return sh
def sell(acc,s,sh,price,why):
    p=acc["pos"].get(s)
    if not p or sh<=0: return 0
    sh=min(sh,p["sh"]); amt=sh*price
    tax=amt*STAMP if is_stock(s) else 0.0
    acc["cash"]+=amt-max(MINFEE,amt*FEE)-tax; p["sh"]-=sh
    log.append(f"{today} {why} 卖 {s} {sh}份 @{price:.3f}"); return sh

def is_stock(s): return s[2:4] in ("00","30","60","68") and not s[2:5] in ("159","510","512","513","515","516","518","560","561","562","588")
def tick(s): return 0.01 if is_stock(s) else 0.001
# 成交假设（11-25 改保守）：挂价单必须"穿价"至少一个最小价位才算成交，只碰到不算
def thru_down(b,lv,s): return b["l"]<=lv-tick(s)
def thru_up(b,lv,s): return b["h"]>=lv+tick(s)
prices={}
def run_t(acc,symbols,base=0.10,sell_up=0.03,back=0.03,cap=0.60,stop_ma5=None,tag=""):
    acc.setdefault("flags",{})
    for s in symbols:
        B5=bars(s)
        if not B5: continue
        d=[x for x in daily(s) if x["day"]<today]; cl=[float(x["close"]) for x in d]
        pc=cl[-1]; ma20=sum(cl[-20:])/20
        f=acc["flags"].setdefault(s,{"base":False,"lad":[],"buyback":None})
        sold_today=False
        avail=acc["pos"].get(s,{}).get("sh",0)   # T+1
        if s=="sh588170": levels=[(0.65,0.05,"梯子0.65"),(0.60,0.10,"梯子0.60")]
        elif stop_ma5 is None: levels=[(round(ma20*0.95,3),0.05,"均线下5%"),(round(ma20*0.90,3),0.10,"均线下10%")]
        else: levels=[]
        for b in B5:
            prices[s]=b["c"]
            if not f["base"] and thru_down(b,pc,s):
                if buy(acc,s,base*CAP0,min(pc,b["o"]),tag+"底仓(翻绿)",prices=prices,cap=cap): f["base"]=True
            for lv,w,name in levels:
                if name not in f["lad"] and thru_down(b,lv,s):
                    if buy(acc,s,w*CAP0,min(lv,b["o"]),tag+name,prices=prices,cap=cap): f["lad"].append(name)
            if f["buyback"] and thru_down(b,f["buyback"]["px"],s):
                px=min(f["buyback"]["px"],b["o"])
                if buy(acc,s,f["buyback"]["sh"],px,tag+"接回",by_shares=True,prices=prices,cap=cap): f["buyback"]=None
            p=acc["pos"].get(s)
            if p and avail>=300 and not f["buyback"] and not sold_today and thru_up(b,pc*(1+sell_up),s):
                px=max(pc*(1+sell_up),b["o"]); sh=int(avail/3/100)*100
                if sell(acc,s,sh,px,tag+f"冲高+{int(sell_up*100)}%卖1/3"):
                    sold_today=True; avail-=sh; f["buyback"]={"sh":sh,"px":round(min(px*(1-back),pc),3)}
        if stop_ma5 is not None and acc["pos"].get(s) and avail>0:
            ma5=(sum(cl[-4:])+B5[-1]["c"])/5
            if B5[-1]["c"]<ma5*(1-stop_ma5):
                sell(acc,s,avail,B5[-1]["c"],tag+"收盘破5日线清仓"); f["base"]=False; f["buyback"]=None
        if acc["pos"].get(s): acc["pos"][s]["last"]=prices.get(s,0)
ETF=["sh588170","sh515880","sh516620","sh562500","sz159995"]
run_t(st["A"],ETF)
st.setdefault("D",{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[]})
STK=["sz000333","sz300308","sh600674","sh600900","sz002242","sz000700","sz002042","sz000711","sh600186"]
run_t(st["D"],STK,base=0.10,sell_up=0.05,back=0.03,cap=0.60,stop_ma5=0.02)
# ---- B ----
Bacc=st["B"]
WB={"sh588170":.15,"sh515880":.15,"sh516620":.15,"sh562500":.15,"sz159928":.13,"sh512170":.13,"sh512890":.13}
for s in WB:
    if s not in prices:
        b=bars(s); 
        if b: prices[s]=b[-1]["c"]
if not Bacc.get("bought"):
    for s,w in WB.items():
        if s in prices: buy(Bacc,s,w*CAP0,prices[s],"B建仓(收盘)")
    Bacc["bought"]=True
for s,p in Bacc["pos"].items(): p["last"]=prices.get(s,p.get("last",0))
# ---- F 笨办法基准：首日收盘 沪深300ETF、红利低波各半，之后不动 ----
Facc=st.setdefault("F",{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[],"bought":False})
for s in ["sh510300","sh512890"]:
    if s not in prices:
        b=bars(s)
        if b: prices[s]=b[-1]["c"]
if not Facc.get("bought"):
    for s in ["sh510300","sh512890"]:
        if s in prices: buy(Facc,s,0.5*CAP0*0.999,prices[s],"F基准建仓(收盘)")
    Facc["bought"]=True
for s,p in Facc["pos"].items(): p["last"]=prices.get(s,p.get("last",0))
# ---- G 底部信号账户：信号触发当天收盘，用50%资金买对应ETF（科创50→588000，创业板指→159915），持有20个交易日后收盘卖 ----
Gacc=st.setdefault("G",{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[],"hold":{}})
try: sig=json.load(open(f"data/signal/{today}.json"))["items"]
except Exception: sig={}
GMAP={"科创50":"sh588000","创业板指":"sz159915"}
for name,s in GMAP.items():
    if sig.get(name,{}).get("status")=="触发" and s not in Gacc["hold"]:
        b=bars(s)
        if b:
            prices[s]=b[-1]["c"]; sh=buy(Gacc,s,0.5*CAP0*0.99,b[-1]["c"],"G底部信号买入(收盘)")
            if sh: Gacc["hold"][s]={"left":20}
for s in list(Gacc["hold"]):
    if s not in prices:
        b=bars(s)
        if b: prices[s]=b[-1]["c"]
    h=Gacc["hold"][s]; h["left"]-=1
    if h["left"]<=0 and s in prices:
        sell(Gacc,s,Gacc["pos"].get(s,{}).get("sh",0),prices[s],"G持满20日收盘卖"); del Gacc["hold"][s]
for s,p in Gacc["pos"].items(): p["last"]=prices.get(s,p.get("last",0))
# ---- H 用户可交易版：任一指数"触发"当天收盘，沪深300ETF买30%；创业板ETF先买10%，再跌5%、10%各加10%（创业板历史上可能比科创晚见底5~8%）；都持有20个交易日 ----
Hacc=st.setdefault("H",{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[],"hold":{},"lad":None})
if any(sig.get(n,{}).get("status")=="触发" for n in GMAP) and not Hacc["hold"]:
    for s,w in [("sh510300",0.30),("sz159915",0.10)]:
        b=bars(s)
        if b:
            prices[s]=b[-1]["c"]
            if buy(Hacc,s,w*CAP0,b[-1]["c"],"H信号买入(收盘)"): Hacc["hold"][s]={"left":20}
    if "sz159915" in prices: Hacc["lad"]={"p0":prices["sz159915"],"done":[]}
if Hacc.get("lad") and "sz159915" in Hacc["hold"]:
    b=bars("sz159915")
    if b:
        prices["sz159915"]=b[-1]["c"]
        for k in (0.05,0.10):
            lv=round(Hacc["lad"]["p0"]*(1-k),3)
            if k not in Hacc["lad"]["done"] and any(thru_down(x,lv,"sz159915") for x in b):
                if buy(Hacc,"sz159915",0.10*CAP0,lv,f"H创业板跌{int(k*100)}%加仓"): Hacc["lad"]["done"].append(k)
for s in list(Hacc["hold"]):
    if s not in prices:
        b=bars(s)
        if b: prices[s]=b[-1]["c"]
    h=Hacc["hold"][s]; h["left"]-=1
    if h["left"]<=0 and s in prices:
        sell(Hacc,s,Hacc["pos"].get(s,{}).get("sh",0),prices[s],"H持满20日收盘卖"); del Hacc["hold"][s]
        if s=="sz159915": Hacc["lad"]=None
for s,p in Hacc["pos"].items(): p["last"]=prices.get(s,p.get("last",0))
# ---- I 选股六层（scripts/stack.py 前一交易日的结果）：挂价买，跌破保护位走，+8%卖一半，最多5天 ----
import glob as _g
Iacc=st.setdefault("I",{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[],"hold":{}})
for s,h in list(Iacc["hold"].items()):
    b=bars(s)
    if not b: continue
    prices[s]=b[-1]["c"]; h["days"]+=1
    sh=Iacc["pos"].get(s,{}).get("sh",0)
    if sh<=0: del Iacc["hold"][s]; continue
    if not h["half"] and any(thru_up(x,h["buy"]*1.08,s) for x in b):
        q=int(sh/2/100)*100
        if q>0: sell(Iacc,s,q,round(h["buy"]*1.08,2),"I冲高+8%卖一半"); h["half"]=True; sh-=q
    if b[-1]["c"]<h["stop"] or h["days"]>=5:
        sell(Iacc,s,sh,b[-1]["c"],"I跌破保护位" if b[-1]["c"]<h["stop"] else "I满5天收盘卖"); del Iacc["hold"][s]
prev=[f for f in sorted(_g.glob("data/stack/*.json")) if os.path.basename(f)[:10]<today]
if prev:
    pk=json.load(open(prev[-1],encoding="utf-8")).get("picks",[])
    for r in pk:
        s=r["symbol"]
        if s in Iacc["hold"]: continue
        b=bars(s)
        if not b: continue
        hit=[x for x in b if thru_down(x,r["limit_buy"],s)]
        if hit:
            px=min(r["limit_buy"],hit[0]["o"])
            if buy(Iacc,s,0.10*CAP0,px,f"I挂价买入（{r.get('name','')} {r.get('ind','')}）"): Iacc["hold"][s]={"buy":px,"stop":r["stop"],"half":False,"days":0}
        prices[s]=b[-1]["c"]
for s,p in Iacc["pos"].items(): p["last"]=prices.get(s,p.get("last",0))
# ---- C ----
Cacc=st["C"]; calls=json.load(open("data/paper/follow_calls.json",encoding="utf-8"))
for c in calls:
    s=c["symbol"]
    if c.get("buy_date")==today and not c.get("bought"):
        b=bars(s)
        if b and c.get("registered","")<today+" 09:30":
            sh=buy(Cacc,s,0.10*CAP0,b[0]["o"],"跟预测开盘买："+c["claim"]); c["bought"]=sh
    if c.get("sell_date")==today and c.get("bought") and not c.get("sold"):
        b=bars(s)
        if b: sell(Cacc,s,c["bought"],b[-1]["c"],"跟预测收盘卖"); c["sold"]=True
    if s not in prices:
        b=bars(s)
        if b: prices[s]=b[-1]["c"]
for s,p in Cacc["pos"].items(): p["last"]=prices.get(s,p.get("last",0))
json.dump(calls,open("data/paper/follow_calls.json","w"),ensure_ascii=False,indent=1)
# ---- 结算 ----
summ=[]
for k in ["A","B","C","D","F","G","H","I"]:
    acc=st[k]; acc["pos"]={s:p for s,p in acc["pos"].items() if p["sh"]>0}
    eq=equity(acc,prices); acc["peak"]=max(acc["peak"],eq); dd=(eq/acc["peak"]-1)*100; acc["mdd"]=min(acc["mdd"],dd)
    acc["days"].append({"date":today,"equity":round(eq,2)})
    pos_pct=round((eq-acc["cash"])/eq*100,1)
    summ.append(f"{k}：净值{eq:,.0f}（{(eq/CAP0-1)*100:+.2f}%），仓位{pos_pct}%，最大回撤{acc['mdd']:.2f}%")
st["last"]=today
json.dump(st,open(SP,"w"),ensure_ascii=False,indent=1)
with open(f"{D}/ledger.md","a",encoding="utf-8") as f: f.write("\n".join([f"## {today}"]+summ+log)+"\n\n")
print("\n".join(summ+log))
