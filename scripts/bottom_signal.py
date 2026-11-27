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
def evaluate(c,v):
    """c,v: 截至当天（含）的收盘价、成交量列表，至少21个。返回 (status, 距20日最高%, 当日%, 量比)"""
    hi=max(c[-21:-1]); dd=(c[-1]/hi-1)*100; ch=(c[-1]/c[-2]-1)*100; vr=v[-1]/st.mean(v[-21:-1])
    status="触发" if dd<=-12 and ch<=-3 and vr>=1.3 else ("接近" if dd<=-10 and ch<=-2 else "无")
    return status,dd,ch,vr

def main():
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
        status,dd,ch,vr=evaluate(c,v)
        r5=(c[-1]/c[-6]-1)*100
        jj=(r5<=-6 and dd<=-10 and vr<1)   # H8 缩量急跌（规律筛选第一轮：检验期N=18，次日涨72%、5日均+1.67%，弱正，①~②）
        out["items"][name]={"status":status,"距20日最高%":round(dd,2),"当日%":round(ch,2),"量比":round(vr,2),"5日%":round(r5,2),"缩量急跌":jj}
        if jj: alert.append(f"{name}：缩量急跌（5日{r5:.1f}%，距20日最高{dd:.1f}%，量比{vr:.2f}；规律筛选H8，检验期次日上涨72%、5日均+1.7%，弱正、只看指数/ETF，不是个股买点）")
        if status!="无": alert.append(f"{name}：{status}（距20日最高{dd:.1f}%，当日{ch:.1f}%，量比{vr:.2f}）")
    os.makedirs("data/signal",exist_ok=True)
    json.dump(out,open(f"data/signal/{today}.json","w"),ensure_ascii=False,indent=1)
    trig=[a for a in alert if "：触发" in a]
    if alert:
        try:
            with open("data/daily_log.md","a",encoding="utf-8") as f: f.write(f"\n底部信号检查 {today}："+"；".join(alert)+"\n")
        except Exception: pass
    if trig:
        txt=(f"# 底部信号 {today}\n"+"\n".join(alert)+"\n\n"
             "历史参考（①，样本小）：2025-01至2026-11逐日回放，'触发'只出现在2025-04-07（科创50、创业板，20日后+11%、+12%）和2026-11-03（科创50）。"
             "2020年以来科创50共6次，满仓20日均+11%；创业板更早有2次失败（2015-07-15、2011-05-23）。量比门槛1.3，11-03只有1.36，刚好过线，门槛稍高就会漏掉，参数有拟合风险。\n"
             "纸面账户G按规则处理；用户本人只做纸面，不实盘。\n")
        open(f"data/signal/ALERT_{today}.md","w").write(txt)
    print(json.dumps(out,ensure_ascii=False))

if __name__=="__main__": main()
