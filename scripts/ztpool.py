"""东方财富涨停池/炸板池/跌停池（公开接口，无需登录）。写 data/ztpool/日期.json 和 日期.md。
字段：lbc 连板数、fbt 首次封板、lbt 最后封板、zbc 炸板次数、hybk 所属行业、fund 封板资金、hs 换手、zttj 几天几板。"""
import json, os, urllib.request, datetime
BJ=datetime.timezone(datetime.timedelta(hours=8))
day=os.environ.get("ZT_DATE") or datetime.datetime.now(BJ).strftime("%Y-%m-%d")
D=day.replace("-","")
UT="7eea3edcaed734bea9cbfc24409ed989"
def get(kind,sort):
    u=f"https://push2ex.eastmoney.com/{kind}?ut={UT}&dpt=wz.ztzt&Pageindex=0&pagesize=500&sort={sort}&date={D}"
    r=urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":"https://quote.eastmoney.com/ztb/"})
    j=json.loads(urllib.request.urlopen(r,timeout=30).read().decode("utf8"))
    return ((j.get("data") or {}).get("pool")) or []
out={"date":day}
try: zt=get("getTopicZTPool","fbt:asc")
except Exception as e: zt=[]; out["err_zt"]=repr(e)[:200]
try: zb=get("getTopicZBPool","fbt:asc")
except Exception as e: zb=[]; out["err_zb"]=repr(e)[:200]
try: dt=get("getTopicDTPool","fund:asc")
except Exception as e: dt=[]; out["err_dt"]=repr(e)[:200]
def t(x): x=str(x).zfill(6); return f"{x[:2]}:{x[2:4]}"
def row(p): 
    z=p.get("zttj") or {}
    return {"code":p.get("c"),"name":p.get("n"),"chg":p.get("zdp"),"lbc":p.get("lbc"),"fbt":t(p.get("fbt","")),"lbt":t(p.get("lbt","")),
            "zbc":p.get("zbc"),"ind":p.get("hybk"),"fund":p.get("fund"),"hs":p.get("hs"),"days":z.get("days"),"ct":z.get("ct")}
out["zt"]=[row(p) for p in zt]; out["zb"]=[row(p) for p in zb]; out["dt"]=[{"code":p.get("c"),"name":p.get("n"),"ind":p.get("hybk")} for p in dt]
nz,nb=len(out["zt"]),len(out["zb"])
out["summary"]={"zt":nz,"zb":nb,"dt":len(out["dt"]),"zb_rate":round(nb/(nz+nb),3) if nz+nb else None,
  "max_lbc":max([r["lbc"] or 0 for r in out["zt"]] or [0])}
from collections import Counter
out["summary"]["by_ind"]=Counter(r["ind"] for r in out["zt"]).most_common(8)
os.makedirs("data/ztpool",exist_ok=True)
if nz==0 and nb==0 and not any(k.startswith("err") for k in out):
    print("空池（休市或未更新）",day)
json.dump(out,open(f"data/ztpool/{day}.json","w"),ensure_ascii=False,indent=1)
s=out["summary"]; L=[f"# 涨停池 {day}（东方财富口径）","",f"涨停{s['zt']} 炸板{s['zb']} 跌停{s['dt']} 炸板率{s['zb_rate']} 最高连板{s['max_lbc']}",
  "行业扎堆："+"、".join(f"{a}{b}" for a,b in s["by_ind"]),"","连板梯队："]
for r in sorted(out["zt"],key=lambda r:-(r["lbc"] or 0)):
    if (r["lbc"] or 0)>=2: L.append(f"- {r['name']}({r['code']}) {r['lbc']}连板｜{r['days']}天{r['ct']}板｜首封{r['fbt']} 炸板{r['zbc']}次｜{r['ind']}")
open(f"data/ztpool/{day}.md","w").write("\n".join(L))
print("\n".join(L[:12]))
