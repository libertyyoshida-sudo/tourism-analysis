import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# --- 設定 ---
APP_ID = "YOUR_APP_ID_HERE"  # ★ここにIDを入力
API_VERSION = "3.0"
BASE_URL = f"http://api.e-stat.go.jp/rest/{API_VERSION}/app/json/getStatsData"

# 都道府県コード辞書（ユーザー選択用）
PREF_CODES = {
    "北海道": "01000", "宮城県": "04000", "東京都": "13000", 
    "石川県": "17000", "静岡県": "22000", "愛知県": "23000", 
    "京都府": "26000", "大阪府": "27000", "広島県": "34000", 
    "福岡県": "40000", "沖縄県": "47000"
    # 必要に応じて47都道府県を追加
}

# --- 関数: APIからデータを取得 ---
@st.cache_data # データをキャッシュして高速化
def fetch_estat_api(stats_data_id, area_code):
    params = {
        "appId": APP_ID,
        "statsDataId": stats_data_id,
        "cdArea": area_code,
        "cdTimeFrom": "20190101" # 2019年以降のデータを取得
    }
    
    response = requests.get(BASE_URL, params=params)
    if response.status_code != 200:
        return None
    
    data = response.json()
    try:
        # 深い階層から値を取り出す
        values = data['GET_STATS_DATA']['STATISTICAL_DATA']['DATA_INF']['VALUE']
        df = pd.DataFrame(values)
        return df
    except (KeyError, TypeError):
        return None

# --- メイン処理 ---
st.title("都道府県別 観光相関分析ツール (All API)")

# 1. サイドバーで都道府県を選択
selected_pref = st.sidebar.selectbox("分析したい都道府県を選択", list(PREF_CODES.keys()))
area_code = PREF_CODES[selected_pref]

st.write(f"### {selected_pref} のデータをAPIから取得中...")

# 2. データの取得（例として2つの統計IDを使用）
# 注意: 統計表IDは変更される可能性があるため、実際には検索API(getStatsList)を噛ませるのが堅牢ですが
# ここでは「宿泊旅行統計」の代表的なIDを仮定して実装します。

# ① 宿泊者数（需要）
# ※IDは例です。最新の月次データIDを探して設定する必要があります。
# 例: 0003322112 (延べ宿泊者数) と仮定
id_demand = st.text_input("宿泊旅行統計ID (需要)", "0003322112") 

# ② 客室稼働率（供給の圧迫度）
# ※IDは例です。
id_supply = st.text_input("客室稼働率統計ID (供給)", "0003322113")

if st.button("分析開始"):
    # APIコール
    df_demand = fetch_estat_api(id_demand, area_code)
    df_supply = fetch_estat_api(id_supply, area_code)

    if df_demand is not None and df_supply is not None:
        # --- データ加工 ---
        # 必要な列だけ抽出してリネーム（APIの仕様に合わせて調整が必要）
        # time_code: 年月, $: 数値
        df_demand['宿泊者数'] = pd.to_numeric(df_demand['$'], errors='coerce')
        df_supply['稼働率'] = pd.to_numeric(df_supply['$'], errors='coerce')
        
        # マージ（結合）
        df_merged = pd.merge(
            df_demand[['@time', '宿泊者数']], 
            df_supply[['@time', '稼働率']], 
            on='@time'
        )
        
        # 年月を見やすく変換 (20230101 -> 2023-01)
        df_merged['年月'] = df_merged['@time'].str[:6]

        # --- 可視化 ---
        st.success("取得成功！分析結果を表示します。")
        
        # 2軸グラフの作成
        fig = px.line(df_merged, x="年月", y=["宿泊者数", "稼働率"], 
                      title=f"{selected_pref}の需要と供給の推移")
        st.plotly_chart(fig)

        # 相関分析
        corr = df_merged['宿泊者数'].corr(df_merged['稼働率'])
        st.metric("宿泊者数と稼働率の相関係数", f"{corr:.3f}")
        
        if corr > 0.7:
            st.info("強い正の相関があります。宿泊客が増えると稼働率が素直に連動しています。")
        elif corr < 0.3:
            st.warning("相関が低いです。定員数が変化したか、データの定義が異なる可能性があります。")

    else:
        st.error("データの取得に失敗しました。IDまたはAPIキーを確認してください。")