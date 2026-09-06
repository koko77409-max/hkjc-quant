# -*- coding: utf-8 -*-
import requests
import json
import math

class WeatherService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        })
        self.hko_url = "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php?dataType=rhrread&lang=tc"

    def get_shatin_wind_bias(self):
        """
        抓取沙田即時風向風速，計算沙田直路 (約 220 度方位) 之實質順/逆風效應
        回傳: 跑法風格加權字典 {"Front": 權重, "Mid": 權重, "Closer": 權重}
        """
        bias = {"Front": 1.0, "Mid": 1.0, "Closer": 1.0, "desc": "微風/無風"}
        try:
            r = self.session.get(self.hko_url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                wind_data = data.get("wind", {}).get("data", [])
                st_wind = next((w for w in wind_data if "沙田" in w.get("place", "")), None)
                if not st_wind and wind_data:
                    st_wind = wind_data[0]
                    
                if st_wind:
                    direction_str = st_wind.get("direction", "無")
                    speed = float(st_wind.get("speed", 0))
                    
                    # 沙田直路朝向西南 (約 220 度)
                    # 東北風 (NE) 為順風，西南風 (SW) 為逆風
                    if any(d in direction_str for d in ["東北", "東", "北"]) and speed >= 12:
                        # 順風有利前領
                        bias["Front"] = round(1.0 + (speed / 100.0) * 0.45, 3)
                        bias["Closer"] = round(1.0 - (speed / 100.0) * 0.35, 3)
                        bias["desc"] = f"直路順風 ({direction_str} {speed} km/h) - 利前領"
                    elif any(d in direction_str for d in ["西南", "南", "西"]) and speed >= 12:
                        # 逆風有利後追 (前馬破風吃虧)
                        bias["Front"] = round(1.0 - (speed / 100.0) * 0.40, 3)
                        bias["Closer"] = round(1.0 + (speed / 100.0) * 0.45, 3)
                        bias["desc"] = f"直路逆風 ({direction_str} {speed} km/h) - 利後追"
                    else:
                        bias["desc"] = f"和緩風向 ({direction_str} {speed} km/h) - 影響中性"
        except Exception as e:
            bias["desc"] = "氣象通訊略過，維持基準權重"
            
        return bias
