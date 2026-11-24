"""按知识库里他的选股规则机械选股（v1，2026-11-24 登记）。
用法：python3 screener.py            -> 输出今天名单到 data/screener/日期.json
     python3 screener.py diag 代码... -> 逐条列出这些票过/不过哪条规则（用来查我们和他的偏差）
规则（全部①级，来源见知识库第3节）：
  通用：剔除ST、北交所、流通市值<50亿（他：'盘子太小=量化短线不碰'）、历史不足250天。
  E1 超跌龙头（他：龙头超跌性价比、'三折'、低位）：流通≥200亿；收盘≤250日最高的50%；最近3天低点逐日抬高（'观察三天在筑底'）；收盘≥5日线。
  E1b（11-24 用户提出的并行变体，不替换E1）：同E1但流通门槛降到100亿，只收E1没收到的。两版并行，看哪版更像他、哪版收益更好。
  E2 横有多长竖有多高：60日箱体振幅≤35%；250日内最高≥最低×2（前期暴涨过）；收盘≤250日最高的60%；20日均量<60日均量×0.8（缩量）。
  E3 趋势股（他：贴5日线不走、年线上；11-13趋势组②1次）：流通≥100亿；收盘>250日线；20日日收益标准差<2%；收盘距20日线±2%以内（踩20日线）。
每条取前3名。数据：新浪不复权日K为主（遇除权会失真，已知缺陷）。"""
import gzip, csv, glob, json, os, sys, statistics, datetime
def load():
    H={}
    for f in sorted(glob.glob("data/hist/part_*.csv.gz")):
        for r in csv.DictReader(gzip.open(f,"rt",encoding="utf-8")):
            H.setdefault(r["symbol"],{})[r["day"]]=(float(r["open"]),float(r["close"]),float(r["high"]),float(r["low"]),float(r["volume"] or 0))
    meta={}
    for f in sorted(glob.glob("data/snapshot/*.csv.gz")):
        day=os.path.basename(f)[:10]
        for r in csv.DictReader(gzip.open(f,"rt",encoding="utf-8")):
            meta[r["symbol"]]={"name":r["name"],"nmc_yi":float(r["nmc"] or 0)/1e4}
            if r["symbol"] in H and day not in H[r["symbol"]]:
                try: H[r["symbol"]][day]=(float(r["open"]),float(r["trade"]),float(r["high"]),float(r["low"]),float(r["volume"] or 0))
                except: pass
    return H,meta
def feats(bars,upto=None):
    d=sorted(x for x in bars if (upto is None or x<=upto)); o=[bars[x] for x in d]
    c=[x[1] for x in o]; h=[x[2] for x in o]; l=[x[3] for x in o]; v=[x[4] for x in o]
    if len(c)<250: return None
    f={"day":d[-1],"close":c[-1]}
    f["hi250"]=max(h[-250:]); f["lo250"]=min(l[-250:])
    f["ma5"]=sum(c[-5:])/5; f["ma20"]=sum(c[-20:])/20; f["ma250"]=sum(c[-250:])/250
    f["box60"]=(max(h[-60:])/min(l[-60:])-1)
    f["vol20_60"]=(sum(v[-20:])/20)/(sum(v[-60:])/60 or 1)
    r=[c[i]/c[i-1]-1 for i in range(len(c)-20,len(c))]; f["sd20"]=statistics.pstdev(r)
    f["low3_up"]=l[-3]<l[-2]<l[-1]
    return f
def checks(sym,f,m):
    nm=m.get("name",""); fl=m.get("nmc_yi",0)
    base={"非ST":"ST" not in nm,"非北交":not sym.startswith("bj"),"流通≥50亿":fl>=50}
    e1={"流通≥200亿":fl>=200,"收盘≤250日高50%":f["close"]<=0.5*f["hi250"],"3天低点抬高":f["low3_up"],"收盘≥5日线":f["close"]>=f["ma5"]}
    e1b={"流通≥100亿":fl>=100,"收盘≤250日高50%":f["close"]<=0.5*f["hi250"],"3天低点抬高":f["low3_up"],"收盘≥5日线":f["close"]>=f["ma5"]}
    e2={"60日箱体≤35%":f["box60"]<=0.35,"曾暴涨(高≥低×2)":f["hi250"]>=2*f["lo250"],"收盘≤250日高60%":f["close"]<=0.6*f["hi250"],"缩量(20/60<0.8)":f["vol20_60"]<0.8}
    e3={"流通≥100亿":fl>=100,"收盘>年线":f["close"]>f["ma250"],"20日波动<2%":f["sd20"]<0.02,"距20日线±2%":abs(f["close"]/f["ma20"]-1)<=0.02}
    return base,e1,e1b,e2,e3
def main():
    H,meta=load()
    if len(sys.argv)>1 and sys.argv[1]=="diag":
        for a in sys.argv[2:]:
            s,_,upto=a.partition("@"); upto=upto or None   # 代码@日期：只用该日及以前的数据
            if s not in H: print(s,"无历史数据（回填未覆盖）"); continue
            f=feats(H[s],upto)
            if not f: print(s,"历史不足250天"); continue
            b,e1,e1b,e2,e3=checks(s,f,meta.get(s,{}))
            def fmt(d): return " ".join(("✓" if v else "✗")+k for k,v in d.items())
            print(s,meta.get(s,{}).get("name",""),f["day"],"| 通用:",fmt(b),"| E1:",fmt(e1),"| E1b:",fmt(e1b),"| E2:",fmt(e2),"| E3:",fmt(e3))
        return
    out={"generated_bj":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="seconds"),"E1":[],"E1b":[],"E2":[],"E3":[]}
    for s,bars in H.items():
        f=feats(bars)
        if not f: continue
        b,e1,e1b,e2,e3=checks(s,f,meta.get(s,{}))
        if not all(b.values()): continue
        nm=meta.get(s,{}).get("name",""); fl=meta.get(s,{}).get("nmc_yi",0)
        if all(e1.values()): out["E1"].append((f["close"]/f["hi250"],s,nm,round(fl)))
        if all(e1b.values()) and not all(e1.values()): out["E1b"].append((f["close"]/f["hi250"],s,nm,round(fl)))
        if all(e2.values()): out["E2"].append((f["box60"],s,nm,round(fl)))
        if all(e3.values()): out["E3"].append((f["sd20"],s,nm,round(fl)))
    for k in ["E1","E1b","E2","E3"]:
        out[k+"_n"]=len(out[k]); out[k]=[{"symbol":x[1],"name":x[2],"float_yi":x[3],"score":round(x[0],4)} for x in sorted(out[k])[:3]]
    os.makedirs("data/screener",exist_ok=True)
    day=out["generated_bj"][:10]
    json.dump(out,open(f"data/screener/{day}.json","w"),ensure_ascii=False,indent=1)
    print(json.dumps(out,ensure_ascii=False,indent=1))
if __name__=="__main__": main()
