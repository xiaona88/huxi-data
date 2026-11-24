import json, urllib.request, datetime, os
H={"User-Agent":"Mozilla/5.0","Referer":"https://quote.eastmoney.com"}
def get(u): return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=15).read().decode())
# 找概念板块
bk=[]
for pn in range(1,8):
    j=get(f"https://push2.eastmoney.com/api/qt/clist/get?pn={pn}&pz=100&fs=m:90+t:3&fields=f12,f14,f3")
    d=(j.get("data") or {}).get("diff") or []
    if not d: break
    bk+= d if isinstance(d,list) else list(d.values())
hit=[b for b in bk if any(k in b["f14"] for k in ["CPO","光模块","光通信","共封装"])]
print("boards",[(b["f12"],b["f14"],b["f3"]) for b in hit])
rows={}
for b in hit:
    j=get(f"https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=300&fs=b:{b['f12']}&fields=f12,f14,f2,f3,f17,f18,f21,f24,f25,f8")
    d=(j.get("data") or {}).get("diff") or []
    for x in (d if isinstance(d,list) else d.values()):
        x.setdefault("boards",[]); rows.setdefault(x["f12"],x)["boards"].append(b["f14"])
out=[]
for c,x in rows.items():
    try:
        out.append({"code":c,"name":x["f14"],"chg%":x["f3"],"open":x["f17"],"prev":x["f18"],"float_yi":round(x["f21"]/1e8,1),"60d%":x["f24"],"ytd%":x["f25"],"boards":x["boards"]})
    except Exception: pass
bj=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
os.makedirs("data/scan",exist_ok=True)
json.dump({"at_bj":bj.isoformat(timespec="seconds"),"stocks":out},open(f"data/scan/cpo_{bj.strftime('%Y-%m-%d_%H%M')}.json","w"),ensure_ascii=False,indent=0)
print(len(out))
