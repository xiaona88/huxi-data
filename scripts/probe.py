import json, urllib.request, time
def get(u):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":"https://finance.sina.com.cn/"}),timeout=40).read()
        except Exception as e: err=e; time.sleep(3)
    raise err
out={}
for s in ["sz159915","sh588000","sh512480","sh588170","sz399006","sh000688"]:
    try: out[s]=json.loads(get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={s}&scale=240&ma=no&datalen=5000"))
    except Exception as e: out[s]=repr(e)
json.dump(out,open("data/probe.json","w"))
