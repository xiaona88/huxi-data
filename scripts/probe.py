# 抓行业分类（新浪行业；失败再试东财），存 data/ref/industry.json：{symbol: 行业名}
import json, urllib.request, time, re, os
def get(u,ref="https://finance.sina.com.cn"):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":ref}),timeout=30).read()
        except Exception as e: err=e; time.sleep(2)
    raise err
out={}; log=[]
try:
    t=get("https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php").decode("gbk")
    j=json.loads(t[t.index("{"):t.rindex("}")+1])
    nodes=[(k,v.split(",")[1]) for k,v in j.items()]
    log.append(f"sina industries {len(nodes)}")
    for code,name in nodes:
        for p in range(1,20):
            r=json.loads(get(f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page={p}&num=100&sort=symbol&asc=1&node={code}&_s_r_a=page").decode("gbk") or "[]")
            if not r: break
            for x in r: out.setdefault(x["symbol"],name)
            if len(r)<100: break
except Exception as e: log.append("sina fail "+repr(e)[:200])
log.append(f"symbols {len(out)}")
os.makedirs("data/ref",exist_ok=True)
json.dump(out,open("data/ref/industry.json","w"),ensure_ascii=False)
json.dump({"log":log,"n":len(out),"sample":list(out.items())[:10]},open("data/probe.json","w"),ensure_ascii=False)
