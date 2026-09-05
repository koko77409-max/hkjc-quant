import os
import requests
import json
import pandas as pd
import numpy as np

DB_PATH = 'hkjc_racing.db'

def get_upcoming_local_race():
    return '2026/09/06', 'ST'

EXACT_ODDS_QUERY = """query racing($date: String, $venueCode: String, $oddsTypes: [OddsType], $raceNo: Int) {
  raceMeetings(date: $date, venueCode: $venueCode) {
    pmPools(oddsTypes: $oddsTypes, raceNo: $raceNo) {
      id
      status
      sellStatus
      oddsType
      lastUpdateTime
      guarantee
      minTicketCost
      name_en
      name_ch
      leg {
        number
        races
      }
      cWinSelections {
        composite
        name_ch
        name_en
        starters
      }
      oddsNodes {
        combString
        oddsValue
        hotFavourite
        oddsDropValue
        bankerOdds {
          combString
          oddsValue
        }
      }
    }
  }
}"""

_CACHED_RUNNERS = {}

def get_base_runners(date_str: str, venue_code: str):
    """讀取全日基本排位資料"""
    global _CACHED_RUNNERS
    if _CACHED_RUNNERS:
        return _CACHED_RUNNERS

    url = 'https://info.cld.hkjc.com/graphql/base/'
    headers = {
        'accept': '*/*',
        'content-type': 'application/json',
        'origin': 'https://bet.hkjc.com',
        'referer': 'https://bet.hkjc.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36'
    }

    payload_file = os.path.join(os.path.dirname(__file__), 'gql_payload.json')
    if not os.path.exists(payload_file):
        payload_file = 'gql_payload.json'

    try:
        with open(payload_file, 'r', encoding='utf-8') as pf:
            payload = json.load(pf)
        payload['variables'] = {
            'date': date_str.replace('/', '-'),
            'venueCode': venue_code
        }
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        if r.status_code == 200:
            res_json = r.json()
            meetings = res_json.get('data', {}).get('raceMeetings', [])
            if meetings:
                for race in meetings[0].get('races', []):
                    r_no = int(race.get('no', 0))
                    runners_list = []
                    for runner in race.get('runners', []):
                        raw_no = str(runner.get('no', '')).strip()
                        clean_no = str(int(raw_no)) if raw_no.isdigit() else raw_no
                        runners_list.append({
                            'race_date': date_str,
                            'race_no': r_no,
                            'horse_no': clean_no,
                            'horse_name': runner.get('name_ch', ''),
                            'horse_code': runner.get('horse', {}).get('code', '') if runner.get('horse') else '',
                            'actual_weight': runner.get('handicapWeight'),
                            'jockey': runner.get('jockey', {}).get('name_ch', '') if runner.get('jockey') else '',
                            'draw': runner.get('barrierDrawNumber'),
                            'trainer': runner.get('trainer', {}).get('name_ch', '') if runner.get('trainer') else '',
                            'declared_weight': np.nan
                        })
                    _CACHED_RUNNERS[r_no] = runners_list
    except Exception as e:
        print(f"排位讀取異常: {e}")

    return _CACHED_RUNNERS

def fetch_race_data(date_str: str, race_no: int, venue_code: str = 'ST') -> pd.DataFrame:
    runners_map = get_base_runners(date_str, venue_code)
    base_list = runners_map.get(int(race_no), [])
    if not base_list:
        return pd.DataFrame()

    url = 'https://info.cld.hkjc.com/graphql/base/'
    headers = {
        'accept': '*/*',
        'content-type': 'application/json',
        'origin': 'https://bet.hkjc.com',
        'referer': 'https://bet.hkjc.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36'
    }

    target_date = date_str.replace('/', '-')
    odds_payload = {
        "operationName": "racing",
        "variables": {
            "date": target_date,
            "venueCode": venue_code,
            "raceNo": int(race_no),
            "oddsTypes": ["WIN", "PLA"]
        },
        "query": EXACT_ODDS_QUERY
    }

    win_odds_dict = {}
    try:
        r = requests.post(url, headers=headers, json=odds_payload, timeout=8)
        if r.status_code == 200:
            res_json = r.json()
            meetings = res_json.get('data', {}).get('raceMeetings', [])
            if meetings:
                pools = meetings[0].get('pmPools', [])
                for p in pools:
                    if p.get('oddsType') == 'WIN':
                        for node in p.get('oddsNodes', []):
                            c_str = str(node.get('combString', '')).strip()
                            if c_str:
                                try:
                                    f_val = float(node.get('oddsValue'))
                                    clean_hno = str(int(c_str))
                                    # 同步相容 '1' 與 '01' 兩種 key
                                    win_odds_dict[clean_hno] = f_val
                                    win_odds_dict[c_str] = f_val
                                except:
                                    pass
    except Exception as e:
        print(f"第 {race_no} 場賠率獲取異常: {e}")

    rows = []
    for r in base_list:
        row = dict(r)
        h_no = str(row['horse_no']).strip()
        clean_key = str(int(h_no)) if h_no.isdigit() else h_no
        row['win_odds'] = win_odds_dict.get(clean_key, win_odds_dict.get(h_no, np.nan))
        rows.append(row)

    return pd.DataFrame(rows)

def enrich_ranker_features(
    live_df: pd.DataFrame, conn: sqlite3.Connection
) -> pd.DataFrame:
    """從歷史特徵庫匹配統計數據並計算場內相對離差"""
    hist_features = pd.read_sql_query('SELECT * FROM model_features', conn)
    enriched_rows = []

    for _, row in live_df.iterrows():
        h_code = row['horse_code']
        jockey = row['jockey']
        trainer = row['trainer']

        h_hist = hist_features[hist_features['horse_code'] == h_code]
        if not h_hist.empty:
            last_race = h_hist.iloc[-1]
            horse_prev_tb = (
                last_race['time_behind']
                if 'time_behind' in last_race
                else last_race.get('horse_prev_tb', 1.5)
            )
            horse_prev_rank = (
                last_race['rank_num']
                if 'rank_num' in last_race
                else last_race.get('horse_prev_rank', 7.0)
            )
            horse_career_runs = len(h_hist)
        else:
            horse_prev_tb = 1.5
            horse_prev_rank = 7.0
            horse_career_runs = 0

        j_hist = hist_features[hist_features['jockey'] == jockey]
        jockey_place_rate = (
            j_hist['is_place'].mean() if not j_hist.empty else 0.20
        )

        t_hist = hist_features[hist_features['trainer'] == trainer]
        trainer_place_rate = (
            t_hist['is_place'].mean() if not t_hist.empty else 0.20
        )

        row_dict = row.to_dict()
        row_dict.update({
            'horse_prev_tb': float(horse_prev_tb),
            'horse_prev_rank': float(horse_prev_rank),
            'jockey_place_rate': float(jockey_place_rate),
            'trainer_place_rate': float(trainer_place_rate),
            'draw': float(row['draw']) if pd.notnull(row['draw']) else 7.0,
            'actual_weight': (
                float(row['actual_weight'])
                if pd.notnull(row['actual_weight'])
                else 120.0
            ),
            'horse_career_runs': int(horse_career_runs),
        })
        enriched_rows.append(row_dict)

    df_res = pd.DataFrame(enriched_rows)

    df_res['rel_weight'] = df_res['actual_weight'] - df_res.groupby('race_no')[
        'actual_weight'
    ].transform('mean')
    df_res['rel_draw'] = df_res['draw'] - df_res.groupby('race_no')[
        'draw'
    ].transform('mean')
    df_res['rel_jockey_rate'] = df_res['jockey_place_rate'] - df_res.groupby(
        'race_no'
    )['jockey_place_rate'].transform('mean')
    df_res['rel_trainer_rate'] = df_res['trainer_place_rate'] - df_res.groupby(
        'race_no'
    )['trainer_place_rate'].transform('mean')
    df_res['rel_prev_tb'] = df_res['horse_prev_tb'] - df_res.groupby(
        'race_no'
    )['horse_prev_tb'].transform('mean')

    return df_res


def run_smart_betslip(
    target_date: str = None,
    venue_code: str = None,
    bankroll: float = 10000.0,
):
    if not target_date or not venue_code:
        target_date, venue_code = get_upcoming_local_race()

    venue_name = '沙田 (ST)' if venue_code == 'ST' else '跑馬地 (HV)'
    print(f'🚀 正在抓取香港本地賽事【 {target_date} {venue_name} 】排位量化分析...')
    conn = sqlite3.connect(DB_PATH)

    all_races_list = []
    seen_horse_sets = []

    for r_no in range(1, 12):
        df_race = fetch_race_data(target_date, r_no, venue_code)

        if df_race.empty:
            if r_no == 1:
                print(f'⚠️ 未能抓取到 {target_date} 香港第 1 場排位。')
                conn.close()
                return
            break

        current_horses = set(df_race['horse_name'].tolist())
        if current_horses in seen_horse_sets:
            break

        seen_horse_sets.append(current_horses)
        all_races_list.append(df_race)

        preview_horses = [
            f"{r['horse_no']}號 {r['horse_name']}"
            for _, r in df_race.head(3).iterrows()
        ]
        print(
            f"  ✓ 成功讀取第 {r_no:2d} 場排位（共 {len(df_race)} 匹馬，前三名單："
            f" {', '.join(preview_horses)}）"
        )
        time.sleep(0.4)

    raw_all_df = pd.concat(all_races_list, ignore_index=True)
    full_df = enrich_ranker_features(raw_all_df, conn)
    conn.close()

    full_df['rank_score'] = ranker.predict(full_df[FEATURES])
    max_score = full_df.groupby('race_no')['rank_score'].transform('max')
    full_df['exp_score'] = np.exp(full_df['rank_score'] - max_score)
    sum_exp = full_df.groupby('race_no')['exp_score'].transform('sum')
    full_df['model_prob'] = full_df['exp_score'] / sum_exp

    valid_odds_series = full_df['win_odds'].dropna()
    is_odds_live = bool(
        len(valid_odds_series) >= (len(full_df) * 0.8)
        and (valid_odds_series.std() > 0.5)
    )

    if is_odds_live:
        print('\n🟢 【狀態】即時賠率已上線：啟動 Benter 對數融合與 +EV 狙擊模型。')
        full_df['inv_odds'] = 1.0 / full_df['win_odds'].replace(0, np.nan)
        race_takeout = full_df.groupby('race_no')['inv_odds'].transform('sum')
        full_df['fair_market_prob'] = full_df['inv_odds'] / race_takeout

        p_mkt = full_df['fair_market_prob'].clip(lower=1e-5)
        p_ml = full_df['model_prob'].clip(lower=1e-5)
        full_df['log_score'] = 0.70 * np.log(p_mkt) + 0.30 * np.log(p_ml)

        max_log = full_df.groupby('race_no')['log_score'].transform('max')
        full_df['exp_log'] = np.exp(full_df['log_score'] - max_log)
        sum_exp_log = full_df.groupby('race_no')['exp_log'].transform('sum')
        full_df['final_prob'] = full_df['exp_log'] / sum_exp_log

        full_df['edge'] = full_df['final_prob'] / full_df['fair_market_prob']
        full_df['ev'] = (full_df['final_prob'] * full_df['win_odds']) - 1.0
    else:
        print(
            '\n🟡 【狀態】馬會彩池未開售（暫無賠率）：啟動「純體育實力模式」。'
        )
        print('   └ 忠實展示模型純客觀實力，Edge 與 EV 將於開盤後自動鎖定。')
        full_df['fair_market_prob'] = np.nan
        full_df['final_prob'] = full_df['model_prob']
        full_df['edge'] = np.nan
        full_df['ev'] = np.nan

    full_df['model_rank'] = (
        full_df.groupby('race_no')['model_prob']
        .rank(ascending=False, method='first')
        .astype(int)
    )

    print('\n' + '=' * 84)
    print(
        f'       📋 【 {target_date} {venue_name} 】各場賽事馬匹勝率由高至低完整排行榜'
    )
    print('=' * 84)

    for race_no, group in full_df.groupby('race_no'):
        sorted_group = group.sort_values('model_rank')
        print(f'\n🏇【 第 {race_no} 場 】（共 {len(sorted_group)} 匹馬）')
        print('-' * 84)
        print(
            f"{'預測名次':<8} {'馬號':<6} {'馬名':<10} {'檔位':<6} {'騎師':<8} {'賠率':<8}"
            f" {'模型勝率':<10} {'市場勝率':<10} {'優勢 Edge':<8}"
        )
        print('-' * 84)

        for _, r in sorted_group.iterrows():
            m_pct = f"{r['model_prob'] * 100:5.1f}%"
            mkt_pct = (
                f"{r['fair_market_prob'] * 100:5.1f}%"
                if pd.notnull(r['fair_market_prob'])
                else '  --  '
            )
            edge_str = (
                f"{r['edge']:5.2f}" if pd.notnull(r['edge']) else '  --  '
            )
            odds_str = (
                f"{r['win_odds']:5.1f}"
                if pd.notnull(r['win_odds'])
                else '未開盤'
            )
            draw_str = f"{int(r['draw']) if pd.notnull(r['draw']) else '-'}"

            print(
                f"  第 {r['model_rank']:2d} 名   {r['horse_no']:<6}"
                f" {r['horse_name']:<10} {draw_str:<6} {r['jockey']:<8}"
                f' {odds_str:<8} {m_pct:<10} {mkt_pct:<10} {edge_str:<8}'
            )

    print('\n' + '=' * 84)
    print(
        f"          🎫 香港本地賽馬實戰指南 (Smart Bet Slip) - {target_date} ({venue_name})"
    )
    print(f'          總本金池: ${bankroll:,.0f} | 策略核心: 815 場跨季回測實證模型')
    print('=' * 84)

    print('\n【 🎯 策略一：+EV 獨贏精選單注 (回測 ROI +2.24% 甜蜜點) 】')
    if is_odds_live:
        value_bets = full_df[
            (full_df['model_rank'] == 1)
            & (full_df['win_odds'] >= 1.5)
            & (full_df['win_odds'] <= 3.0)
            & (full_df['model_prob'] >= 0.25)
            & (full_df['edge'] >= 1.00)
        ].copy()

        if not value_bets.empty:
            for _, b in value_bets.iterrows():
                stake = int(min(bankroll * 0.02, 300.0) // 10 * 10)
                stake = max(10, stake)
                m_pct_val = b['model_prob'] * 100
                edge_val = b['edge']
                print(
                    f"第 {b['race_no']:2d} 場 | {b['horse_no']:2s} 號"
                    f" {b['horse_name']:6s} | 賠率: {b['win_odds']:4.1f} |"
                    f' 模型勝率: {m_pct_val:4.1f}% | 優勢 Edge: {edge_val:4.2f} |'
                    f' 建議投注: ${stake}'
                )
        else:
            print(
                '  今日暫無符合「賠率 1.5-3.0 且 勝率 >= 25%」的極致穩健獨贏標的。'
            )
    else:
        print('  ⏳ 彩池尚未開售（暫無即時賠率）。')
        print(
            '  └ +EV 獨贏單注需在「賠率 1.5-3.0 且 Edge >='
            ' 1.00」甜蜜點下注，待開盤後自動計算。'
        )

    print(
        '\n【 ⚡ 策略二：每場 Top 3 互串（位置 Q 互串 3 注 + 單 T 1 注小博大） 】'
    )
    print(
        '  說明：815 場回測證實 QP 互串命中率達 36.2%（每 2.8 場中 1 次），單 T'
        ' 具備極佳高賠率槓桿。'
    )

    for race_no, group in full_df.groupby('race_no'):
        top3 = group.sort_values('model_rank').head(3)
        h_nos = top3['horse_no'].tolist()
        h_names = top3['horse_name'].tolist()

        label_list = [f'{n}號 {m}' for n, m in zip(h_nos, h_names)]
        combo_str = ' + '.join(label_list)

        qp_pairs = (
            f'{h_nos[0]}-{h_nos[1]}, {h_nos[0]}-{h_nos[2]},'
            f' {h_nos[1]}-{h_nos[2]}'
        )
        trio_combo = f'{h_nos[0]}+{h_nos[1]}+{h_nos[2]}'

        print(f'\n第 {race_no:2d} 場核心三甲 : {combo_str}')
        print(f'   ├ 🥈 位置 Q 互串 (QP Box) : [{qp_pairs}] (共 3 注，建議每注 $10，共 $30)')
        print(f'   └ 🥇 單 T (Trio)          : [{trio_combo}] (共 1 注，建議每注 $10)')

    print(
        '\n【 🛡️ 策略三：超級穩膽場次（Top 1 勝率 >= 28% 單膽連贏 Q / QP） 】'
    )
    banker_races = (
        full_df[
            (full_df['model_rank'] == 1) & (full_df['model_prob'] >= 0.28)
        ]
        .sort_values('race_no')['race_no']
        .tolist()
    )

    if banker_races:
        for r_no in banker_races:
            r_horses = full_df[full_df['race_no'] == r_no].sort_values(
                'model_rank'
            )
            banker = r_horses.iloc[0]
            legs = r_horses.iloc[1:3]
            legs_str = ' + '.join(
                [f"{leg['horse_no']}號 {leg['horse_name']}" for _, leg in legs.iterrows()]
            )
            b_pct = banker['model_prob'] * 100
            print(
                f"第 {r_no:2d} 場 | 超強單膽: {banker['horse_no']}號"
                f" {banker['horse_name']} (純勝率: {b_pct:.1f}%)"
            )
            print(
                f'   └ 單膽拖腳: {legs_str} (Q 及 QP 各買 2 注，每注 $20，共 $80)'
            )
    else:
        print('  今日無勝率超過 28% 的超級單膽場次。')

    print('\n【 🚀 策略四：穩健位置過關 (3 串 4 All-up) 】')
    top_3_overall = full_df.sort_values('model_prob', ascending=False).head(3)
    if len(top_3_overall) == 3:
        for _, h in top_3_overall.iterrows():
            h_pct = h['model_prob'] * 100
            print(
                f"關次: 第 {h['race_no']} 場 | {h['horse_no']} 號 {h['horse_name']:6s}"
                f' (純勝率: {h_pct:.1f}%)'
            )
        print(
            '注數: 3 串 4（3 注 2 關 + 1 注 3 關）位置 (PLACE) | 建議每注 $50'
            ' (總成本 $200)'
        )

    print('=' * 84 + '\n')


if __name__ == '__main__':
    run_smart_betslip()