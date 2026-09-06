# -*- coding: utf-8 -*-
import requests
import json

class WeatherService:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=ch",
            "Origin": "https://bet.hkjc.com"
        }
        self.graphql_url = "https://info.cld.hkjc.com/graphql/base/"

    def fetch_racecourse_weather(self):
        """
        調用官方 Weather 原生白名單查詢，取得分段微風速、土壤含水量與陣風數據
        """
        payload = {
            "operationName": "Weather",
            "variables": {},
            "query": """query Weather {
  weather {
    racecourse
    sectional {
      location
      date
      time
      avgCorrectedWindDirection
      avgCorrectedWindSpeed
      correctedGustDirection
      correctedGustSpeed
      isValid
    }
    weatherStation {
      location
      avgCorrectedWindDirection
      avgCorrectedWindSpeed
      temperature
      relativeHumidity
      soilVolumeticWaterContent
      rainFallPrecipitation10Min
      isValid
    }
  }
}"""
        }
        
        info = {
            "venue": "HV/ST",
            "avg_wind_speed": 0.0,
            "wind_direction": "微風",
            "soil_moisture": 0.0,
            "rain_10m": 0.0,
            "Front": 1.0,
            "Mid": 1.0,
            "Closer": 1.0,
            "summary": "環境微感測器運行中"
        }

        try:
            r = self.session.post(self.graphql_url, headers=self.headers, json=payload, timeout=8)
            if r.status_code == 200:
                data = r.json()
                weather_data = data.get("data", {}).get("weather", {})
                if weather_data:
                    info["venue"] = weather_data.get("racecourse", "ST")
                    sec_list = weather_data.get("sectional", [])
                    station_list = weather_data.get("weatherStation", [])
                    
                    # 1. 提取分段風速儀讀數
                    valid_sections = [s for s in sec_list if s.get("isValid")]
                    if valid_sections:
                        # 取直路端點測速
                        latest_sec = valid_sections[-1]
                        info["avg_wind_speed"] = float(latest_sec.get("avgCorrectedWindSpeed", 0.0))
                        info["wind_direction"] = str(latest_sec.get("avgCorrectedWindDirection", "微風"))
                        
                    # 2. 提取氣象站土壤體積含水率 (Soil Volumetric Water Content)
                    valid_stations = [w for w in station_list if w.get("isValid")]
                    if valid_stations:
                        st = valid_stations[0]
                        info["soil_moisture"] = float(st.get("soilVolumeticWaterContent", 0.0))
                        info["rain_10m"] = float(st.get("rainFallPrecipitation10Min", 0.0))
        except Exception:
            pass

        # 3. 跑道物理阻力綜合加權計算
        # 跑馬地（Happy Valley）直路僅 312 米，若無降雨且風阻不大，先天利好前領 (Front 1.05)
        # 若土壤含水率偏高 (soil_moisture > 30% 或近 10 分鐘降雨 > 0)，外疊後追馬抓地優勢放大
        if info["venue"] == "HV" or "Valley" in str(info["venue"]):
            base_front = 1.06
            base_closer = 0.94
            venue_name = "跑馬地 (HV)"
        else:
            base_front = 1.03
            base_closer = 0.97
            venue_name = "沙田 (ST)"

        if info["soil_moisture"] >= 35.0 or info["rain_10m"] > 0:
            # 跑道受水變黏，前領破風與抵抗外疊消耗變大
            info["Front"] = round(base_front * 0.92, 3)
            info["Closer"] = round(base_closer * 1.10, 3)
            info["summary"] = f"{venue_name} 草皮偏濕軟 (含水量 {info['soil_moisture']}%) 🌧️ 後追加成"
        elif info["avg_wind_speed"] >= 15.0:
            # 強風抗阻
            info["Front"] = round(base_front * 0.95, 3)
            info["Closer"] = round(base_closer * 1.06, 3)
            info["summary"] = f"{venue_name} 直路頂頭風 ({info['avg_wind_speed']} km/h) 🌪️ 逆風利後追"
        else:
            info["Front"] = base_front
            info["Closer"] = base_closer
            info["summary"] = f"{venue_name} 乾快硬地，風力平穩 ({info['avg_wind_speed']} km/h) ⚡ 利前領貼欄"

        return info

if __name__ == "__main__":
    service = WeatherService()
    res = service.fetch_racecourse_weather()
    print("=" * 60)
    print("🏇 馬會官方微氣象與土壤感測器讀數:")
    print(f"➜ 當前賽場: {res['venue']}")
    print(f"➜ 分段校正風速: {res['avg_wind_speed']} km/h (方位: {res['wind_direction']})")
    print(f"➜ 土壤體積含水量: {res['soil_moisture']}% (近10分鐘降雨: {res['rain_10m']} mm)")
    print(f"➜ 物理抗阻結論: {res['summary']}")
    print(f"➜ 風格加權係數: 前領 {res['Front']}x | 均速 {res['Mid']}x | 後追 {res['Closer']}x")
    print("=" * 60)

    def get_shatin_wind_bias(self):
        """相容舊版呼叫別名"""
        res = self.fetch_racecourse_weather()
        return {
            "Front": res["Front"],
            "Mid": res["Mid"],
            "Closer": res["Closer"],
            "desc": res["summary"]
        }
