import os,subprocess,json
res={}
for d in ["2026-11-03","2026-11-13","2026-11-24"]:
    r=subprocess.run(["python3","scripts/signal.py"],env={**os.environ,"TODAY":d},capture_output=True,text=True)
    res[d]=r.stdout[-600:]+r.stderr[-300:]
for f in os.listdir("data/signal"): os.remove("data/signal/"+f)
json.dump(res,open("data/probe.json","w"),ensure_ascii=False)
