import json, urllib.request, time, datetime
def get(u):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"}),timeout=30).read()
        except Exception as e: err=e; time.sleep(2)
    raise err
rows=[]
for p in range(1,70):
    t=get(f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page={p}&num=100&sort=symbol&asc=1&node=hs_a&_s_r_a=page")
    j=json.loads(t.decode("gbk"))
    if not j: break
    rows+=j
def lim(r):
    s=r["symbol"]; n=r.get("name","")
    if "ST" in n: return 0.05
    if s[2:4] in ("30","68"): return 0.20
    if s.startswith("bj"): return 0.30
    return 0.10
up=dn=zt=dt=0; amt=0; zb=0; ztl=[]; dtl=[]
for r in rows:
    try: pc=float(r["settlement"]); c=float(r["trade"]); h=float(r["high"])
    except: continue
    if pc<=0 or c<=0: continue
    amt+=float(r.get("amount") or 0)
    ch=c/pc-1; L=lim(r)
    up+=ch>0; dn+=ch<0
    if c>=round(pc*(1+L),2)-0.001: zt+=1; ztl.append((r["name"],r["symbol"],round(ch*100,1)))
    elif h>=round(pc*(1+L),2)-0.001: zb+=1
    if c<=round(pc*(1-L),2)+0.001: dt+=1; dtl.append((r["name"],r["symbol"],round(ch*100,1)))
idx={}
for s in ["sh000001","sz399001","sz399006","sh000688","sh000016","sh000852"]:
    m=json.loads(get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={s}&scale=5&ma=no&datalen=200"))
    by={}
    for x in m: by.setdefault(x["day"][:10],[]).append(x)
    ds=sorted(by)[-4:]
    idx[s]={d:{"last":by[d][-1]["day"][11:16],"close":by[d][-1]["close"],"prev":None} for d in ds}
out={"n":len(rows),"time":rows[0].get("ticktime") if rows else None,"up":up,"down":dn,"zt":zt,"dt":dt,"zb":zb,"amount_yi":round(amt/1e8),"dt_list":dtl,"zt_sample":ztl[:80]}
json.dump(out,open("data/probe.json","w"),ensure_ascii=False,indent=1)
