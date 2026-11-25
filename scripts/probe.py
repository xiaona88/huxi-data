import json, urllib.request, time
def get(u):
    for i in range(3):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn"}),timeout=40).read())
        except Exception as e: err=e; time.sleep(3)
    raise err
out={s:get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={s}&scale=240&ma=no&datalen=2000") for s in ["sh000001","sh000300","sh000688","sz399006","sh000852"]}
json.dump(out,open("data/probe.json","w"))
