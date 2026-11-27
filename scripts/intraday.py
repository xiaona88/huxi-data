"""盘中扫描（北京10:05、13:05由cron-job.org触发workflow_dispatch）。写 data/intraday/日期_HHMM.json/.md。
内容：主要指数和ETF相对昨收、量能节奏；涨停池行业扎堆；用户持仓离止盈/离场线；按"事件剧本"标出可能触发的条目。不是投资建议。"""
import json, os, urllib.request, datetime, collections
BJ=datetime.timezone(datetime.timedelta(hours=8))
now=datetime.datetime.now(BJ); day=now.strftime("%Y-%m-%d"); hm=now.strftime("%H%M")
def get(u,ref,enc="gbk"):
    return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":ref}),timeout=30).read().decode(enc,"ignore")
IDX={"上证":"sh000001","沪深300":"sh000300","创业板指":"sz399006","科创50":"sh000688"}
ETF={"科创50ETF":"sh588000","科创半导体588170":"sh588170","创业板ETF":"sz159915","沪深300ETF":"sh510300","上证50ETF":"sh510050","通信515880":"sh515880","中证500ETF":"sh510500"}
H=[x for x in json.load(open("data/user_holdings.json"))["holdings"] if "sold" not in x]
syms=list(IDX.values())+list(ETF.values())+[x["symbol"] for x in H]+["b_KOSPI"]
out={"date":day,"time":now.strftime("%H:%M"),"quotes":{},"holdings":[],"zt":{},"notes":[]}
try:
    t=get("https://hq.sinajs.cn/list="+",".join(dict.fromkeys(syms)),"https://finance.sina.com.cn/")
    for line in t.split(";"):
        if '="' not in line: continue
        code=line.split("=")[0].split("_")[-1]; f=line.split('"')[1].split(",")
        if code=="KOSPI" and len(f)>9:
            out["quotes"]["KOSPI"]={"pct":round((float(f[1])/float(f[9])-1)*100,2)}; continue
        if len(f)<10 or float(f[2] or 0)==0: continue
        pc=float(f[2]); p=float(f[3]) or pc
        out["quotes"][code[2:]]={"name":f[0],"price":p,"pct":round((p/pc-1)*100,2),"high":float(f[4]),"low":float(f[5]),"vol":float(f[8])}
except Exception as e: out["notes"].append("行情失败:"+repr(e)[:80])
# 量能节奏：对比昨日全天成交量（daily json 里没有就跳过）
try:
    import glob
    prev=sorted(glob.glob("data/snapshot/*.csv.gz"))[-1]
except Exception: prev=None
# 宽基ETF放量：累计成交量 ÷ 20日均量，并按已交易分钟数折算全天（≥2.5倍报警，口径同 daily.py 的 etf_alarm）
BROAD={"上证50ETF":"sh510050","沪深300ETF":"sh510300","中证500ETF":"sh510500","科创50ETF":"sh588000","创业板ETF":"sz159915"}
def traded_min(t):
    m=t.hour*60+t.minute
    a=max(0,min(m,690)-570); b=max(0,min(m,900)-780)
    return max(1,a+b)
out["broad_vol"]={}
for n,s in BROAD.items():
    try:
        k=json.loads(get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={s}&scale=240&ma=no&datalen=22","https://finance.sina.com.cn/","utf8"))
        hist=[float(x["volume"]) for x in k if x["day"]<day][-20:]
        v=out["quotes"].get(s[2:],{}).get("vol")
        if not hist or not v: continue
        avg=sum(hist)/len(hist); el=traded_min(now)
        out["broad_vol"][n]={"so_far":round(v/avg,2),"projected":round(v/avg*240/el,2),"elapsed_min":el}
    except Exception as e: out["notes"].append(f"{n}量比失败:"+repr(e)[:60])
alarm=[n for n,r in out["broad_vol"].items() if r["projected"]>=2.5]
out["broad_alarm"]=alarm
if alarm: out["notes"].append("宽基放量报警（折算全天≥2.5倍）："+"、".join(alarm)+" → 用户12-02条件C2可能成立，收盘再确认")
# 涨停池
try:
    D=day.replace("-","")
    j=json.loads(get(f"https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=500&sort=fbt:asc&date={D}","https://quote.eastmoney.com/ztb/","utf8"))
    pool=(j.get("data") or {}).get("pool") or []
    zb=json.loads(get(f"https://push2ex.eastmoney.com/getTopicZBPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=500&sort=fbt:asc&date={D}","https://quote.eastmoney.com/ztb/","utf8"))
    zbp=(zb.get("data") or {}).get("pool") or []
    by=collections.Counter(p.get("hybk") for p in pool).most_common(6)
    out["zt"]={"zt":len(pool),"zb":len(zbp),"by_ind":by,"top_lb":sorted([(p.get("n"),p.get("lbc")) for p in pool],key=lambda x:-(x[1] or 0))[:5]}
except Exception as e: out["notes"].append("涨停池失败:"+repr(e)[:80])
q=out["quotes"]
for x in H:
    s=x["symbol"][2:]; v=q.get(s)
    if not v: continue
    r={"name":x["name"],"cost":x["price"],"price":v["price"],"pnl%":round((v["price"]/x["price"]-1)*100,1)}
    if x.get("take_profit"): r["离止盈%"]=round((x["take_profit"]/v["price"]-1)*100,1)
    if x.get("stop_close"): r["离离场线%"]=round((x["stop_close"]/v["price"]-1)*100,1)
    out["holdings"].append(r)
# 剧本检查（只标出，不下结论）
k=q.get("000688",{}); c=q.get("399006",{})
if k.get("pct",0)>=5 or c.get("pct",0)>=5: out["notes"].append("剧本：指数单日已涨≥5% → 不追，只处理持仓（高开/冲高是卖点）")
if k.get("pct",0)<=-3 or c.get("pct",0)<=-3: out["notes"].append("剧本：指数跌≥3% → 收盘看是否放量（底部信号）还是缩量（缩量急跌）；盘中不抄")
if out["zt"].get("zt",0) and out["zt"]["by_ind"]:
    top=out["zt"]["by_ind"][0]
    if top[1]>=5: out["notes"].append(f"涨停扎堆：{top[0]} {top[1]}只（只当题材地图，不当买入名单）")
os.makedirs("data/intraday",exist_ok=True)
json.dump(out,open(f"data/intraday/{day}_{hm}.json","w"),ensure_ascii=False,indent=1)
L=[f"# 盘中扫描 {day} {out['time']}（北京）",""]
L.append("指数："+"；".join(f"{n} {q[s[2:]]['pct']:+.2f}%" for n,s in IDX.items() if s[2:] in q)+(f"；韩国 {q['KOSPI']['pct']:+.2f}%" if "KOSPI" in q else ""))
L.append("ETF："+"；".join(f"{n} {q[s[2:]]['pct']:+.2f}%" for n,s in ETF.items() if s[2:] in q))
if out["broad_vol"]: L.append("宽基量比（已成交/折算全天）："+"；".join(f"{n} {r['so_far']}/{r['projected']}" for n,r in out["broad_vol"].items())+("  报警："+"、".join(out["broad_alarm"]) if out["broad_alarm"] else "  无报警"))
if out["zt"]: L.append(f"涨停{out['zt']['zt']} 炸板{out['zt']['zb']}；扎堆："+"、".join(f"{a}{b}" for a,b in out['zt']['by_ind']))
for r in out["holdings"]: L.append(f"持仓 {r['name']} 成本{r['cost']} 现{r['price']} {r['pnl%']:+.1f}%"+(f" 离止盈{r['离止盈%']:+.1f}%" if '离止盈%' in r else "")+(f" 离离场线{r['离离场线%']:+.1f}%" if '离离场线%' in r else "（无离场线）"))
L+=out["notes"]
open(f"data/intraday/{day}_{hm}.md","w").write("\n".join(L))
print("\n".join(L))
