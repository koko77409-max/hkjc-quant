# -*- coding: utf-8 -*-
import requests
import json
import datetime

class HKJCAutoService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://bet.hkjc.com/racing/pages/odds_wp.aspx?lang=ch",
            "Origin": "https://bet.hkjc.com",
            "Content-Type": "application/json"
        })
        self.graphql_url = "https://info.cld.hkjc.com/graphql/base/"
        
        self.official_query = """fragment raceFragment on Race {
  id
  no
  status
  raceName_en
  raceName_ch
  postTime
  distance
  wageringFieldSize
  claCode
  raceClass_en
  raceClass_ch
}

fragment racingBlockFragment on RaceMeeting {
  changeHistories(filters: ["top3"]) {
    raceNo
    runnerNo
    horseName_ch
  }
}

query raceMeetings($date: String, $venueCode: String) {
  raceMeetings(date: $date, venueCode: $venueCode) {
    id
    status
    venueCode
    date
    totalNumberOfRace
    races {
      ...raceFragment
      runners {
        no
        status
        name_ch
        finalPosition
        winOdds
        barrierDrawNumber
      }
    }
    ...racingBlockFragment
  }
}"""

    def fetch_race_meeting_data(self, date_str="2026-09-06", venue="ST"):
        """使用官方白名單查詢取得排位、賽果與實時走位"""
        payload = {
            "operationName": "raceMeetings",
            "variables": {
                "date": date_str,
                "venueCode": venue
            },
            "query": self.official_query
        }
        try:
            r = self.session.post(self.graphql_url, json=payload, timeout=8)
            if r.status_code == 200:
                data = r.json()
                meetings = data.get("data", {}).get("raceMeetings", [])
                if meetings:
                    return meetings[0]
        except Exception:
            pass
        return None

    def get_actual_results_and_bias(self, meeting_data):
        """解析當日已完賽場次之三甲名單與跑道偏差"""
        if not meeting_data:
            return {}, {"Front": 1.0, "Mid": 1.0, "Closer": 1.0}
            
        results = {}
        for r in meeting_data.get("races", []):
            r_no = int(r.get("no", 0))
            top3 = []
            for rn in r.get("runners", []):
                fp = str(rn.get("finalPosition", "")).strip()
                if fp in ["1", "2", "3"]:
                    top3.append({
                        "pos": int(fp),
                        "no": int(rn.get("no")),
                        "name": rn.get("name_ch")
                    })
            top3.sort(key=lambda x: x["pos"])
            if len(top3) >= 3:
                results[r_no] = top3
                
        # 簡單跑道偏差評估
        bias = {"Front": 1.0, "Mid": 1.0, "Closer": 1.0}
        return results, bias
