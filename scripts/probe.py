import json, urllib.request
def get(u,ref="https://finance.sina.com.cn/"):
    return urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Referer":ref}),timeout=20).read()
out={}
S="sh600186"
try: out["hq"]=get(f"https://hq.sinajs.cn/list={S},sh000001,sh000300",).decode("gbk")
except Exception as e: out["hq"]=repr(e)
try: out["d"]=json.loads(get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={S}&scale=240&ma=no&datalen=260"))
except Exception as e: out["d"]=repr(e)
try: out["m1"]=json.loads(get(f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={S}&scale=5&ma=no&datalen=48"))
except Exception as e: out["m1"]=repr(e)
try: out["ff"]=json.loads(get("https://push2.eastmoney.com/api/qt/stock/fflow/kline/get?lmt=0&klt=1&secid=1.600186&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57","https://data.eastmoney.com/"))["data"]["klines"]
except Exception as e: out["ff"]=repr(e)
try: out["ffd"]=json.loads(get("https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=15&klt=101&secid=1.600186&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57","https://data.eastmoney.com/"))["data"]["klines"]
except Exception as e: out["ffd"]=repr(e)
try: out["tick"]=get(f"https://vip.stock.finance.sina.com.cn/quotes_service/view/CN_TransListV2.php?num=40&symbol={S}").decode("gbk")[:3000]
except Exception as e: out["tick"]=repr(e)
json.dump(out,open("data/probe.json","w"),ensure_ascii=False)
