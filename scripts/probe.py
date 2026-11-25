import os,subprocess,sys,json
subprocess.run([sys.executable,"-m","pip","install","-q","pandas"])
env=dict(os.environ); env["TODAY"]="2026-11-24"
a=subprocess.run([sys.executable,"scripts/stack.py"],env=env,capture_output=True,text=True)
b=subprocess.run([sys.executable,"scripts/levels_check.py"],env=env,capture_output=True,text=True)
md=open("data/alerts/ALERTS_2026-11-24.md").read() if os.path.exists("data/alerts/ALERTS_2026-11-24.md") else "无"
json.dump({"stack":a.stdout[-1500:]+a.stderr[-500:],"levels_err":b.stderr[-800:],"md":md},open("data/probe.json","w"),ensure_ascii=False,indent=1)
