"""价位与规则提醒（收盘后跑）。
一、data/levels.json 里的固定价位（他说的、用户定的）：碰到就提醒，只提醒一次。
二、按他的规则自动算（观察池=他点名的票+纸面账户D的票+选股器最新结果）：
  R1 回踩前一个涨停价：近30日有涨停，今天最低碰到涨停收盘价±1%以内且收盘没跌破 → "回踩涨停价未破"；收盘跌破涨停价2%以上 → "跌破涨停价（他说的保护位）"
  R2 回踩年线：最低≤年线×1.02 且收盘≥年线 → "回踩年线未破"；收盘<年线×0.98 且前一天还在年线上 → "跌破年线"
  R3 箱体突破（横有多长竖有多高）：收盘>前60日最高收盘 且 量≥前20日均量1.5倍
  R4 趋势股回踩20日线翻红：最低≤20日线 且 收盘≥20日线 且 收盘>开盘，且年线上
结果写 data/alerts/日期.json；有任何一条时写 data/alerts/ALERTS_日期.md 并在 daily_log 记一行。规则提醒全部是①级，只用于纸面检验。"""
import json, os, urllib.request, datetime, statistics as st, time, glob
H={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"}
def get(u):
    for i in range(3):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30).read())
        except Exception:
            if i==2: raise
            time.sleep(2)
def bars(sym,today):
    d=get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen=300")
    d=[{"day":x["day"],"o":float(x["open"]),"h":float(x["high"]),"l":float(x["low"]),"c":float(x["close"]),"v":float(x["volume"])} for x in d if x["day"]<=today]
    if not d or d[-1]["day"]!=today:
        m=[x for x in get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sym}&scale=5&ma=no&datalen=60") if x["day"].startswith(today)]
        if not m: return None
        d.append({"day":today,"o":float(m[0]["open"]),"h":max(float(x["high"]) for x in m),"l":min(float(x["low"]) for x in m),"c":float(m[-1]["close"]),"v":sum(float(x["volume"]) for x in m)})
    return d
def is_etf(s): return s[2:5] in ("159","510","512","513","515","516","518","560","561","562","588")
def limit_pct(s): return 0.20 if s[2:4] in ("30","68") else 0.10
def rules(s,b):
    out=[]; t=b[-1]; c=[x["c"] for x in b]
    if len(b)<61: return out
    ma20=st.mean(c[-20:]); ma250=st.mean(c[-250:]) if len(c)>=250 else None
    if not is_etf(s):
        lim=[i for i in range(len(b)-30,len(b)-1) if i>0 and b[i]["c"]>=round(b[i-1]["c"]*(1+limit_pct(s)),2)-0.011]
        if lim:
            i=lim[-1]; lp=b[i]["c"]
            if t["l"]<=lp*1.01 and t["c"]>=lp*0.99: out.append(("R1",f"回踩{b[i]['day'][5:]}涨停价{lp:.2f}未破（收{t['c']:.2f}，最低{t['l']:.2f}）"))
            elif t["c"]<lp*0.98 and b[-2]["c"]>=lp*0.98: out.append(("R1",f"收盘跌破{b[i]['day'][5:]}涨停价{lp:.2f}（他说的保护位）"))
    if ma250:
        if t["l"]<=ma250*1.02 and t["c"]>=ma250: out.append(("R2",f"回踩年线{ma250:.2f}未破（收{t['c']:.2f}）"))
        elif t["c"]<ma250*0.98 and b[-2]["c"]>=ma250: out.append(("R2",f"跌破年线{ma250:.2f}（收{t['c']:.2f}）"))
    hi60=max(c[-61:-1]); vr=t["v"]/st.mean(x["v"] for x in b[-21:-1])
    if t["c"]>hi60 and vr>=1.5: out.append(("R3",f"放量突破60日最高{hi60:.2f}（量比{vr:.2f}）"))
    if ma250 and t["c"]>ma250 and t["l"]<=ma20<=t["c"] and t["c"]>t["o"]: out.append(("R4",f"年线上方回踩20日线{ma20:.2f}收红"))
    return out
def main():
    bj=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    today=os.environ.get("TODAY") or bj.date().isoformat()
    if not os.environ.get("TODAY") and (bj.hour,bj.minute)<(15,5): raise SystemExit("before close")
    L=json.load(open("data/levels.json",encoding="utf-8"))
    pool={}
    for x in json.load(open("data/mentions.json",encoding="utf-8")): pool[x["symbol"]]=x["name"][:8]
    for s,n in [("sz000333","美的集团"),("sz300308","中际旭创"),("sh600674","川投能源"),("sh600900","长江电力"),("sz002242","九阳股份"),("sz000700","模塑科技"),("sh600186","莲花控股"),("sh588170","科创半导体ETF"),("sh515880","通信ETF"),("sh516620","影视ETF"),("sz159995","芯片ETF")]: pool.setdefault(s,n)
    sc=sorted(glob.glob("data/screener/*.json"))
    if sc:
        j=json.load(open(sc[-1],encoding="utf-8"))
        for k in ("E1","E1b","E2","E3"):
            for x in j.get(k,[]): pool.setdefault(x["symbol"],x["name"]+f"（选股器{k}）")
    for x in L["levels"]: pool.setdefault(x["symbol"],x["name"])
    cache={}; hits=[]
    for s in pool:
        try: cache[s]=bars(s,today)
        except Exception as e: cache[s]=None
    for x in L["levels"]:
        if x.get("triggered") and not x.get("repeat"): continue
        b=cache.get(x["symbol"])
        if not b or b[-1]["day"]!=today: continue
        v=b[-1][{"close":"c","low":"l","high":"h"}[x["check"]]]
        ok=v<=x["level"] if x["dir"]=="below" else v>=x["level"]
        if ok:
            x["triggered"]=today
            hits.append({"type":"价位","source":x["source"],"symbol":x["symbol"],"name":x["name"],"text":f"{'跌到' if x['dir']=='below' else '涨到'}{x['level']}（{ {'close':'收盘','low':'最低','high':'最高'}[x['check']] }{v}）——{x['note']}"})
    for s,n in pool.items():
        b=cache.get(s)
        if not b or b[-1]["day"]!=today: continue
        for code,txt in rules(s,b): hits.append({"type":"规则","source":code,"symbol":s,"name":n,"text":txt})
    # 持有天数提醒：短线票拿满5个交易日（回测：主线短线票超额约只维持5天）
    try:
        UH=json.load(open("data/user_holdings.json",encoding="utf-8"))
        for h in [x for x in UH["holdings"] if "sold" not in x]:
            b=cache.get(h["symbol"]) or bars(h["symbol"],today)
            if not b or b[-1]["day"]!=today: continue
            n=sum(1 for x in b if x["day"]>h["buy_date"])
            if h.get("type")=="短线" and n==5:
                c=b[-1]["c"]; hits.append({"type":"价位","source":"用户","symbol":h["symbol"],"name":h["name"],"text":f"已持有满5个交易日（{h['buy_date']}买入价{h['price']}，今天收{c}，{(c/h['price']-1)*100:+.1f}%）。回测：主线里的短线票，超额大约只维持5天，拿到20天平均转为跑输；他自己个股一般拿2~5天"})
    except Exception as e: print("holdings check fail",e)
    # 今天六层选股的结果（明天的挂单）
    try:
        sk=json.load(open(f"data/stack/{today}.json",encoding="utf-8"))
        for r in sk.get("picks",[]):
            hits.append({"type":"规则","source":"六层","symbol":r["symbol"],"name":r["name"],"text":f"六层选股入选（{r['ind']}）：明天挂{r['limit_buy']}，保护位{r['stop']}，冲高+8%卖一半，最多拿5天——纸面账户I照此执行"})
        if not sk.get("gate",{}).get("通过",True): hits.append({"type":"规则","source":"六层","symbol":"","name":"大势闸门","text":f"不通过（全A等权5日{sk['gate']['全A等权5日%']}%），今天不出短线票"})
    except Exception: pass
    if hits and all(h["name"]=="大势闸门" for h in hits): hits=[]   # 只有闸门不通过时不单独推送
    json.dump(L,open("data/levels.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    os.makedirs("data/alerts",exist_ok=True)
    json.dump({"date":today,"pool":len(pool),"hits":hits},open(f"data/alerts/{today}.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    if hits:
        pv=[h for h in hits if h["type"]=="价位"]; rl=[h for h in hits if h["type"]=="规则"]
        txt=f"# 价位与规则提醒 {today}\n\n"
        if pv: txt+="价位（他说的/你定的）：\n"+"\n".join(f"- [{h['source']}] {h['name']}：{h['text']}" for h in pv)+"\n\n"
        sixl=[h for h in rl if h["source"]=="六层"]; rl=[h for h in rl if h["source"]!="六层"]
        if sixl: txt+="六层选股（他的选股思路自动跑，回测打平附近，只做纸面）：\n"+"\n".join(f"- {h['name']}：{h['text']}" for h in sixl)+"\n\n"
        if rl: txt+="按他的规则算出来的位置（只是背景，全市场回测单独用会跑输，不是信号）：\n"+"\n".join(f"- [{h['source']}] {h['name']}：{h['text']}" for h in rl)+"\n"
        open(f"data/alerts/ALERTS_{today}.md","w",encoding="utf-8").write(txt)
        try:
            with open("data/daily_log.md","a",encoding="utf-8") as f: f.write(f"\n价位与规则提醒 {today}：{len(pv)}条价位、{len(rl)}条规则，详见 data/alerts/ALERTS_{today}.md\n")
        except Exception: pass
    print(json.dumps(hits,ensure_ascii=False,indent=1))
if __name__=="__main__": main()
