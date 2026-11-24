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
FEE=0.0001; CAP0=100000.0; START=os.environ.get("PAPER_START","2026-11-25"); D=os.environ.get("PAPER_DIR","data/paper")
bj=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
today=os.environ.get("TODAY") or bj.date().isoformat()
if today<START: raise SystemExit("not started")
SP=f"{D}/state.json"; os.makedirs(D,exist_ok=True)
st=json.load(open(SP)) if os.path.exists(SP) else {"D":{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[]},"A":{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[]},"B":{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[],"bought":False},"C":{"cash":CAP0,"pos":{},"peak":CAP0,"mdd":0,"days":[]},"last":""}
if st["last"]==today: raise SystemExit("already settled today")
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
    cost=sh*price*(1+FEE)
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
    sh=min(sh,p["sh"]); acc["cash"]+=sh*price*(1-FEE); p["sh"]-=sh
    log.append(f"{today} {why} 卖 {s} {sh}份 @{price:.3f}"); return sh

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
            if not f["base"] and b["l"]<=pc:
                if buy(acc,s,base*CAP0,min(pc,b["o"]),tag+"底仓(翻绿)",prices=prices,cap=cap): f["base"]=True
            for lv,w,name in levels:
                if name not in f["lad"] and b["l"]<=lv:
                    if buy(acc,s,w*CAP0,min(lv,b["o"]),tag+name,prices=prices,cap=cap): f["lad"].append(name)
            if f["buyback"] and b["l"]<=f["buyback"]["px"]:
                px=min(f["buyback"]["px"],b["o"])
                if buy(acc,s,f["buyback"]["sh"],px,tag+"接回",by_shares=True,prices=prices,cap=cap): f["buyback"]=None
            p=acc["pos"].get(s)
            if p and avail>=300 and not f["buyback"] and not sold_today and b["h"]>=pc*(1+sell_up):
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
STK=["sz000333","sz300308","sh600674","sh600900","sz002242","sz000700"]
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
for k in ["A","B","C","D"]:
    acc=st[k]; acc["pos"]={s:p for s,p in acc["pos"].items() if p["sh"]>0}
    eq=equity(acc,prices); acc["peak"]=max(acc["peak"],eq); dd=(eq/acc["peak"]-1)*100; acc["mdd"]=min(acc["mdd"],dd)
    acc["days"].append({"date":today,"equity":round(eq,2)})
    pos_pct=round((eq-acc["cash"])/eq*100,1)
    summ.append(f"{k}：净值{eq:,.0f}（{(eq/CAP0-1)*100:+.2f}%），仓位{pos_pct}%，最大回撤{acc['mdd']:.2f}%")
st["last"]=today
json.dump(st,open(SP,"w"),ensure_ascii=False,indent=1)
with open(f"{D}/ledger.md","a",encoding="utf-8") as f: f.write("\n".join([f"## {today}"]+summ+log)+"\n\n")
print("\n".join(summ+log))
