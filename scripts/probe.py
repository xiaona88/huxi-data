import os,subprocess,json,sys
res={}
for d in ["2026-11-20","2026-11-24"]:
    subprocess.run(["git","checkout","data/levels.json"])
    env=dict(os.environ); env["TODAY"]=d
    r=subprocess.run([sys.executable,"scripts/levels_check.py"],env=env,capture_output=True,text=True)
    res[d]={"out":r.stdout[-6000:],"err":r.stderr[-800:]}
json.dump(res,open("data/probe.json","w"),ensure_ascii=False,indent=1)
