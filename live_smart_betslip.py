from datetime import datetime, timedelta
import io
import re
import sqlite3
import time
import joblib
import numpy as np
import pandas as pd
import requests

MODEL_PATH = 'hkjc_model.pkl'
DB_PATH = 'hkjc_racing.db'

try:
    ranker = joblib.load(MODEL_PATH)
except Exception as e:
    print(f'❌ 無法載入模型檔案 {MODEL_PATH}，請確認檔案存在。錯誤：{e}')
    exit()

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,'
        ' like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx',
}

FEATURES = [
    'rel_weight',
    'rel_draw',
    'rel_jockey_rate',
    'rel_trainer_rate',
    'rel_prev_tb',
    'horse_prev_tb',
    'horse_prev_rank',
    'jockey_place_rate',
    'trainer_place_rate',
    'draw',
    'actual_weight',
    'horse_career_runs',
]


def fetch_race_data(
    race_date_str: str, race_no: int, venue_code: str = 'ST'
) -> pd.DataFrame:
    """精準抓取香港本地排位表（只對準沙田 ST 或跑馬地 HV）"""
    clean_date = race_date_str.replace('/', '')

    candidate_urls = [
        f'https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx?RaceDate={race_date_str}&Racecourse={venue_code}&RaceNo={race_no}',
        f'https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx?RaceDate={clean_date}&Racecourse={venue_code}&RaceNo={race_no}',
        f'https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx?RaceDate={race_date_str}&RaceNo={race_no}',
    ]

    for url in candidate_urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8'

            if res.status_code != 200:
                continue

            # 嚴格過濾海外轉播賽事標籤
            if any(
                tag in res.text
                for tag in ['越洋轉播賽事', 'S1-', 'S2-', 'S3-', '海外賽事']
            ):
                continue

            dfs = pd.read_html(io.StringIO(res.text))
            for df in dfs:
                if isinstance(df.columns, pd.MultiIndex):
                    flat_cols = []
                    for col in df.columns:
                        valid_levels = [
                            str(c).strip()
                            for c in col
                            if str(c).strip() and 'Unnamed' not in str(c)
                        ]
                        flat_cols.append(
                            valid_levels[-1] if valid_levels else str(col[0])
                        )
                    df.columns = flat_cols
                else:
                    df.columns = [str(c).strip() for c in df.columns]

                has_name = any('馬名' in c for c in df.columns)
                has_jockey = any('騎師' in c for c in df.columns)
                has_no = any(
                    '馬號' in c or c == '號' or (c.endswith('號') and '烙' not in c)
                    for c in df.columns
                )

                if has_name and has_jockey and has_no:
                    col_map = {}
                    for c in df.columns:
                        c_str = str(c).strip()
                        if (
                            c_str in ['馬號', '號']
                            or (c_str.endswith('號') and '烙' not in c_str)
                        ) and 'horse_no' not in col_map:
                            col_map['horse_no'] = c
                        elif '馬名' in c_str and 'horse_name' not in col_map:
                            col_map['horse_name'] = c
                        elif (
                            '烙號' in c_str or '編號' in c_str or '烙' in c_str
                        ) and 'horse_code' not in col_map:
                            col_map['horse_code'] = c
                        elif (
                            '負磅' in c_str or '配磅' in c_str
                        ) and 'actual_weight' not in col_map:
                            col_map['actual_weight'] = c
                        elif '騎師' in c_str and 'jockey' not in col_map:
                            col_map['jockey'] = c
                        elif (
                            c_str in ['檔位', '檔'] or c_str.endswith('檔位')
                        ) and 'draw' not in col_map:
                            col_map['draw'] = c
                        elif '練馬師' in c_str and 'trainer' not in col_map:
                            col_map['trainer'] = c
                        elif (
                            '排位體重' in c_str or '體重' in c_str
                        ) and 'declared_weight' not in col_map:
                            col_map['declared_weight'] = c
                        elif (
                            '獨贏' in c_str or '賠率' in c_str
                        ) and 'win_odds' not in col_map:
                            col_map['win_odds'] = c

                    if 'horse_no' not in col_map or 'horse_name' not in col_map:
                        continue

                    records = []
                    for _, row in df.iterrows():
                        h_no_val = str(row[col_map['horse_no']]).strip()
                        if not h_no_val.isdigit():
                            continue

                        raw_name = str(row[col_map['horse_name']]).strip()
                        match = re.search(
                            r'^(.*?)\s*[\(\（]([A-Z0-9]+)[\)\）]', raw_name
                        )
                        if match:
                            h_name = match.group(1).strip()
                            h_code = match.group(2).strip()
                        else:
                            h_name = raw_name
                            h_code = (
                                str(row[col_map['horse_code']]).strip()
                                if 'horse_code' in col_map
                                and pd.notnull(row[col_map['horse_code']])
                                else h_name
                            )

                        jock_raw = str(
                            row.get(col_map.get('jockey', ''), '')
                        ).strip()
                        jock_clean = re.sub(
                            r'\s*[\(\（].*?[\)\）]', '', jock_raw
                        ).strip()

                        trnr_raw = str(
                            row.get(col_map.get('trainer', ''), '')
                        ).strip()
                        trnr_clean = re.sub(
                            r'\s*[\(\（].*?[\)\）]', '', trnr_raw
                        ).strip()

                        win_odds = np.nan
                        if 'win_odds' in col_map:
                            try:
                                raw_odds = (
                                    str(row[col_map['win_odds']])
                                    .replace(',', '')
                                    .strip()
                                )
                                val = float(raw_odds)
                                if val > 1.0:
                                    win_odds = val
                            except Exception:
                                win_odds = np.nan

                        act_wt = (
                            pd.to_numeric(
                                row.get(col_map.get('actual_weight', ''), 120),
                                errors='coerce',
                            )
                            or 120.0
                        )
                        drw = (
                            pd.to_numeric(
                                row.get(col_map.get('draw', ''), 7),
                                errors='coerce',
                            )
                            or 7.0
                        )
                        dec_wt = (
                            pd.to_numeric(
                                row.get(
                                    col_map.get('declared_weight', ''), 1100
                                ),
                                errors='coerce',
                            )
                            or 1100.0
                        )

                        records.append({
                            'race_date': race_date_str,
                            'race_no': race_no,
                            'horse_no': h_no_val,
                            'horse_name': h_name,
                            'horse_code': h_code,
                            'actual_weight': act_wt,
                            'jockey': jock_clean,
                            'draw': drw,
                            'trainer': trnr_clean,
                            'declared_weight': dec_wt,
                            'win_odds': win_odds,
                        })

                    if len(records) >= 4:
                        return pd.DataFrame(records)
        except Exception:
            continue

    return pd.DataFrame()


def get_upcoming_local_race() -> tuple[str, str]:
    """三層防護：嚴格鎖定香港本地賽事 (沙田 ST 或 跑馬地 HV)，排除海外賽事

    返回: (race_date 'YYYY/MM/DD', venue_code 'ST'|'HV')
    """
    today_str = datetime.now().strftime('%Y/%m/%d')

    # 策略 1：從馬會官方賽期表 (Fixture.aspx) 獲取本地賽日曆
    try:
        fixture_url = 'https://racing.hkjc.com/racing/information/Chinese/Racing/Fixture.aspx'
        f_res = requests.get(fixture_url, headers=headers, timeout=10)
        f_res.encoding = 'utf-8'

        dfs = pd.read_html(io.StringIO(f_res.text))
        fixture_candidates = []
        for df in dfs:
            for _, row in df.iterrows():
                row_str = ' '.join([str(v) for v in row.values])
                if any(
                    w in row_str
                    for w in [
                        '越洋',
                        'S1',
                        'S2',
                        'S3',
                        'S4',
                        '海外',
                        '轉播',
                        'Simulcast',
                    ]
                ):
                    continue

                venue = None
                if '沙田' in row_str or 'Sha Tin' in row_str:
                    venue = 'ST'
                elif (
                    '跑馬地' in row_str
                    or '快活谷' in row_str
                    or 'Happy Valley' in row_str
                ):
                    venue = 'HV'

                if venue:
                    m_d1 = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', row_str)
                    m_d2 = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', row_str)
                    m_d3 = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', row_str)

                    d_fmt = None
                    if m_d1:
                        d_fmt = f'{m_d1.group(3)}/{int(m_d1.group(2)):02d}/{int(m_d1.group(1)):02d}'
                    elif m_d2:
                        d_fmt = f'{m_d2.group(1)}/{int(m_d2.group(2)):02d}/{int(m_d2.group(3)):02d}'
                    elif m_d3:
                        d_fmt = f'{m_d3.group(1)}/{int(m_d3.group(2)):02d}/{int(m_d3.group(3)):02d}'

                    if d_fmt and d_fmt >= today_str:
                        fixture_candidates.append((d_fmt, venue))

        if fixture_candidates:
            fixture_candidates.sort(key=lambda x: x[0])
            return fixture_candidates[0]
    except Exception:
        pass

    # 策略 2：從即時排位首頁解析中文賽期
    try:
        url = 'https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx'
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        html = res.text

        is_overseas = any(
            w in html for w in ['越洋轉播', '海外賽事', 'S1-', 'S2-', 'S3-']
        )
        if not is_overseas:
            venue = (
                'HV'
                if any(
                    w in html
                    for w in ['跑馬地', '快活谷', 'Happy Valley', 'Racecourse=HV']
                )
                else 'ST'
            )
            m_cn = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', html)
            if m_cn:
                d_str = f'{m_cn.group(1)}/{int(m_cn.group(2)):02d}/{int(m_cn.group(3)):02d}'
                if d_str >= today_str:
                    return d_str, venue
    except Exception:
        pass

    # 策略 3：終極實體驗證 - 往後探測未來 7 天內真正有香港排位的賽事日
    for offset in range(0, 8):
        test_date = (datetime.now() + timedelta(days=offset)).strftime(
            '%Y/%m/%d'
        )
        for v in ['ST', 'HV']:
            test_df = fetch_race_data(test_date, 1, v)
            if not test_df.empty and len(test_df) >= 4:
                return test_date, v

    return '2026/09/06', 'ST'


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