# 用 bottom_signal.evaluate（与每日脚本同一个函数）逐日回放 2025-01-01 ~ 今天
import json, urllib.request, time, subprocess, sys, os
from bottom_signal import evaluate
def get(u):
    for i in range(3):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"}),timeout=40).read())
        except Exception as e: err=e; time.sleep(3)
    raise err
out={}
for name,s in {"科创50":"sh000688","创业板指":"sz399006","上证":"sh000001"}.items():
    d=get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={s}&scale=240&ma=no&datalen=520")
    c=[float(x["close"]) for x in d]; v=[float(x["volume"]) for x in d]; L=[x["low"] for x in d]
    rows=[]; n=0
    for i in range(21,len(d)):
        if d[i]["day"]<"2025-01-01": continue
        n+=1
        st,dd,ch,vr=evaluate(c[:i+1],v[:i+1])
        if st!="无":
            f=lambda k: round((c[i+k]/c[i]-1)*100,2) if i+k<len(c) else None
            mn=lambda k: round((min(float(x) for x in L[i+1:i+k+1])/c[i]-1)*100,2) if i+k<len(c) else None
            rows.append({"day":d[i]["day"],"status":st,"dd":round(dd,1),"ch":round(ch,1),"vr":round(vr,2),"r5":f(5),"r20":f(20),"r60":f(60),"low20":mn(20)})
    out[name]={"days_checked":n,"from":d[0]["day"],"signals":rows}
env=dict(os.environ); env["TODAY"]="2026-11-03"; os.makedirs("data/signal",exist_ok=True)
r=subprocess.run([sys.executable,"scripts/bottom_signal.py"],env=env,capture_output=True,text=True)
out["main_2026-11-03"]=r.stdout[-400:]+r.stderr[-200:]
for f in os.listdir("data/signal"): os.remove("data/signal/"+f)
json.dump(out,open("data/probe.json","w"),ensure_ascii=False,indent=1)
