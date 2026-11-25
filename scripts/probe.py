import os,subprocess,sys,json
env=dict(os.environ); env["TODAY"]="2026-11-24"
subprocess.run([sys.executable,"-m","pip","install","-q","pandas"])
r=subprocess.run([sys.executable,"scripts/stack.py"],env=env,capture_output=True,text=True)
json.dump({"out":r.stdout[-4000:],"err":r.stderr[-1500:]},open("data/probe.json","w"),ensure_ascii=False,indent=1)
