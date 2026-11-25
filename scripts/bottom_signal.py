"""底部信号检查（收盘后跑）。定义见知识库第6节/6h：收盘较前20日最高收盘跌≥12%、当日跌≥3%、量≥前20日均量1.3倍。
接近（预警）：较20日最高跌≥10%且当日跌≥2%。结果写 data/signal/日期.json；触发时写 data/signal/ALERT_日期.md。"""
import json, os, urllib.request, datetime, statistics as st, time
H={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"}
def get(u):
    for i in range(3):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30).read())
        except Exception:
            if i==2: raise
            time.sleep(3)
bj=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
today=os.environ.get("TODAY") or bj.date().isoformat()
if not os.environ.get("TODAY") and (bj.hour,bj.minute)<(15,5): raise SystemExit("before close")
IDX={"科创50":"sh000688","创业板指":"sz399006"}
out={"date":today,"rule":"跌离20日最高≥12% 且 当日≤-3% 且 量≥1.3倍","items":{}}
alert=[]
for name,s in IDX.items():
    d=get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={s}&scale=240&ma=no&datalen=40")
    d=[x for x in d if x["day"]<=today]
    if d[-1]["day"]!=today:
        m=[x for x in get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={s}&scale=5&ma=no&datalen=60") if x["day"].startswith(today)]
        if not m: out["items"][name]={"status":"无今日数据"}; continue
        d.append({"day":today,"close":m[-1]["close"],"volume":str(sum(float(x["volume"]) for x in m))})
    c=[float(x["close"]) for x in d]; v=[float(x["volume"]) for x in d]
    hi=max(c[-21:-1]); dd=(c[-1]/hi-1)*100; ch=(c[-1]/c[-2]-1)*100; vr=v[-1]/st.mean(v[-21:-1])
    status="触发" if dd<=-12 and ch<=-3 and vr>=1.3 else ("接近" if dd<=-10 and ch<=-2 else "无")
    out["items"][name]={"status":status,"距20日最高%":round(dd,2),"当日%":round(ch,2),"量比":round(vr,2)}
    if status!="无": alert.append(f"{name}：{status}（距20日最高{dd:.1f}%，当日{ch:.1f}%，量比{vr:.2f}）")
os.makedirs("data/signal",exist_ok=True)
json.dump(out,open(f"data/signal/{today}.json","w"),ensure_ascii=False,indent=1)
if alert:
    txt=f"""# 底部信号 {today}
{chr(10).join(alert)}

历史参考（①，样本小）：科创50 2020年起6次信号，满仓20日均+11%、60日均+7%，中途最深均-2%；创业板4次中2次失败（2015-07-15、2011-05-23）。知识库还记有2026-10两次信号来早了。
纸面账户 G 按规则处理；用户本人不实盘（项目规则：只做纸面）。
"""
    open(f"data/signal/ALERT_{today}.md","w").write(txt)
    try:
        with open("data/daily_log.md","a",encoding="utf-8") as f: f.write(f"\n**⚠ 底部信号检查 {today}：** "+"；".join(alert)+"（详见 data/signal/ALERT_"+today+".md）\n")
    except Exception: pass
print(json.dumps(out,ensure_ascii=False))
