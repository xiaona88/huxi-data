# 事件研究：不同级别消息对A股的影响持续多久；美元指数和A股的关系
import json, urllib.request, time, statistics as st
H={"User-Agent":"Mozilla/5.0","Referer":"https://quote.eastmoney.com/"}
def get(u):
    for i in range(4):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=20).read()
        except Exception as e: err=e; time.sleep(3)
    raise err
def em(secid):
    j=json.loads(get(f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1&fields2=f51,f52,f53,f54,f55,f56&klt=101&fqt=0&beg=20070101&end=20500101"))
    return [(x.split(",")[0],float(x.split(",")[1]),float(x.split(",")[2]),float(x.split(",")[5])) for x in j["data"]["klines"]]
def sina(sym):
    m=json.loads(get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen=6000"))
    return [(r["day"],float(r["open"]),float(r["close"]),float(r["volume"])) for r in m]
IDX={"上证":("1.000001","sh000001"),"沪深300":("1.000300","sh000300"),"创业板":("0.399006","sz399006"),"科创50":("1.000688","sh000688")}
data={};src={}
for n,(s,sn) in IDX.items():
    try: data[n]=em(s);src[n]="em"
    except Exception as e:
        try: data[n]=sina(sn);src[n]="sina"
        except Exception as e2: src[n]=repr(e2)[:100]
ev=json.load(open("data/events.json"))["events"]
out={"src":src,"events":[],"by_level":{}}
H_=[("d0",0),("d5",5),("d20",20),("d60",60)]
for d,lv,name in ev:
    row={"date":d,"lv":lv,"name":name}
    for n,k in data.items():
        ds=[x[0] for x in k]
        i=next((j for j,x in enumerate(ds) if x>=d),None)
        if i is None or i==0: continue
        pc=k[i-1][2]; o=k[i][1]; c=k[i][2]
        r={"day0":ds[i],"gap":round((o/pc-1)*100,2),"d0":round((c/pc-1)*100,2),
           "vol":round(k[i][3]/st.mean(x[3] for x in k[max(0,i-20):i]),2)}
        for h,m in H_[1:]:
            if i+m<len(k): r[h]=round((k[i+m][2]/pc-1)*100,2); r[h+"_after_d0"]=round((k[i+m][2]/c-1)*100,2)
        row[n]=r
    out["events"].append(row)
# 按级别汇总（用上证；创业板作对照）
for idx in ["上证","创业板"]:
    for lv in "ABXDP":
        rs=[e[idx] for e in out["events"] if e["lv"]==lv and idx in e]
        if not rs: continue
        agg={"n":len(rs)}
        for f in ["gap","d0","d5","d20","d60","d5_after_d0","d20_after_d0","d60_after_d0"]:
            v=[r[f] for r in rs if f in r]
            if v: agg[f]=round(st.mean(v),2); agg[f+"_win"]=round(sum(x>0 for x in v)/len(v),2)
        out["by_level"][f"{idx}_{lv}"]=agg
# 美元指数（他说"美元指数涨不是好事"）
try:
    dx=em("100.UDI"); src["美元指数"]="em"
    sh={x[0]:x[2] for x in data["沪深300"]}; dxm={x[0]:x[2] for x in dx}
    days=[d for d in sorted(sh) if d in dxm and d>="2015-01-01"]
    def ch(m,a,b): return m[b]/m[a]-1
    same=[];nxt=[]
    for j in range(20,len(days)-20,5):
        a,b,c=days[j-20],days[j],days[j+20]
        same.append((ch(dxm,a,b),ch(sh,a,b))); nxt.append((ch(dxm,a,b),ch(sh,b,c)))
    def corr(p):
        xs,ys=zip(*p); return round(st.correlation(xs,ys),3)
    def split(p):
        up=[y for x,y in p if x>0.02]; dn=[y for x,y in p if x<-0.02]; al=[y for x,y in p]
        return {"美元20日涨>2%后":(len(up),round(st.mean(up)*100,2) if up else None),"跌>2%后":(len(dn),round(st.mean(dn)*100,2) if dn else None),"全部":round(st.mean(al)*100,2)}
    out["usd"]={"同期20日相关":corr(same),"领先20日相关":corr(nxt),"沪深300同期":split(same),"沪深300之后20日":split(nxt),"样本":len(same)}
except Exception as e: out["usd"]=repr(e)[:150]
json.dump(out,open("data/probe.json","w"),ensure_ascii=False,indent=1)
print(json.dumps(out["by_level"],ensure_ascii=False,indent=1)); print(out.get("usd")); print(src)
