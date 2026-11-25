import os,subprocess,json,sys
os.makedirs("data/signal",exist_ok=True)
res={}
for d in ["2026-11-03","2026-11-13","2026-11-24"]:
    env=dict(os.environ); env["TODAY"]=d
    r=subprocess.run([sys.executable,"scripts/signal.py"],env=env,capture_output=True,text=True)
    res[d]={"out":r.stdout[-700:],"err":r.stderr[-400:],"rc":r.returncode}
    print(d,res[d],flush=True)
for f in os.listdir("data/signal"): os.remove("data/signal/"+f)
json.dump(res,open("data/probe.json","w"),ensure_ascii=False)
