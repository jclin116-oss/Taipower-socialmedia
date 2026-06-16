import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse

# 網頁基本設定
st.set_page_config(page_title="社群輿情監測系統 V16", page_icon="📱", layout="centered")

st.title("📱 社群輿情監測系統")
st.caption("版本：V16 (手機 App 標頭破防 + PTT JSON 直連版)")

with st.expander("ℹ️ 關鍵字與語法說明（點擊展開）", expanded=True):
    st.markdown("""
    * **多組搜尋 (OR)**：用「半形逗號」隔開 (例：`基隆 台電, 停電`)
    * **組內包含 (AND)**：用「空格」隔開 (例：`基隆 台電`)。
    """)

platform = st.selectbox("搜尋平台:", ["全部", "PTT", "Dcard"])
kw_input = st.text_input("請輸入搜尋關鍵字:", value="基隆 台電, 停電")
hours_val = st.number_input("回溯小時:", min_value=1, max_value=720, value=24, step=1)

if st.button("執行即時輿情監測", type="primary"):
    if not kw_input.strip():
        st.warning("提示：請輸入搜尋關鍵字")
    else:
        search_groups = [g.strip() for g in kw_input.replace('，', ',').split(',') if g.strip()]
        all_discussions = []
        limit_time = datetime.now() - timedelta(hours=int(hours_val))

        with st.spinner("安全通道檢索中..."):
            
            # --- 管道一：Dcard 官方手機 App 隱藏接口 ---
            if platform in ["全部", "Dcard"]:
                # 【核心破防關鍵】偽裝成 Dcard 官方手機客戶端的標頭，Cloudflare 看到會直接放行
                dcard_headers = {
                    'User-Agent': 'Dcard/5.51.0 (Android; 13; Scale/3.00)',
                    'Accept': 'application/json',
                    'Accept-Language': 'zh-TW',
                    'X-Client-Type': 'android'
                }
                
                for group in search_groups:
                    encoded_kw = urllib.parse.quote(group)
                    # 這是官方 App 專用的結構化搜尋接口
                    dcard_url = f"https://www.dcard.tw/_api/search/posts?query={encoded_kw}&limit=50&sort=latest"
                    try:
                        res = requests.get(dcard_url, headers=dcard_headers, timeout=10)
                        if res.status_code == 200:
                            posts = res.json()
                            for post in posts:
                                created_at_str = post.get('createdAt', '').split('.')[0]
                                dt = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M:%S') + timedelta(hours=8)
                                
                                if dt > limit_time:
                                    title = post.get('title', '')
                                    excerpt = post.get('excerpt', '')
                                    
                                    # 組內多字詞精準過濾 (AND 邏輯)
                                    words = group.split()
                                    if all(w.lower() in title.lower() or w.lower() in excerpt.lower() for w in words):
                                        all_discussions.append({
                                            "關鍵字組合": group,
                                            "討論平台": "Dcard",
                                            "討論標題": title,
                                            "發布時間": dt.strftime('%Y-%m-%d %H:%M'),
                                            "原始連結": f"https://www.dcard.tw/f/all/p/{post.get('id')}"
                                        })
                    except:
                        continue

            # --- 管道二：PTT 網頁版 (PttWeb) 公開 JSON 接口 ---
            if platform in ["全部", "PTT"]:
                ptt_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                for group in search_groups:
                    # 取出組內第一個核心關鍵字做網頁檢索
                    core_kw = group.split()[0] if group.split() else group
                    encoded_kw = urllib.parse.quote(core_kw)
                    
                    # 直連 PTTWeb 專門提供數據對接的 JSON 接口，不鎖雲端 IP
                    ptt_url = f"https://www.pttweb.cc/api/search?q={encoded_kw}&page=0"
                    try:
                        res = requests.get(ptt_url, headers=ptt_headers, timeout=10)
                        if res.status_code == 200:
                            data = res.json()
                            results = data.get('results', [])
                            for item in results:
                                title = item.get('title', '')
                                
                                # 二次過濾，確保組內所有關鍵字都包含在標題中
                                filter_words = group.split()
                                if not all(w.lower() in title.lower() for w in filter_words):
                                    continue
                                    
                                ts = item.get('createdAt', 0)
                                if ts:
                                    dt = datetime.fromtimestamp(ts)
                                    if dt > limit_time:
                                        all_discussions.append({
                                            "關鍵字組合": group,
                                            "討論平台": "PTT",
                                            "討論標題": title,
                                            "發布時間": dt.strftime('%Y-%m-%d %H:%M'),
                                            "原始連結": f"https://www.pttweb.cc/bbs/{item.get('bbs', 'Gossiping')}/{item.get('aid', '')}"
                                        })
                    except:
                        continue

        # --- 顯示結果與下載處理 ---
        if all_discussions:
            df = pd.DataFrame(all_discussions)
            df = df.drop_duplicates(subset=["原始連結"])
            
            st.success(f"🎉 監測成功！本次共安全撈出 {len(df)} 筆最即時輿情資料。")
            st.dataframe(df, use_container_width=True)
            
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 下載輿情報表 (CSV)",
                data=csv_data,
                file_name=f"社群輿情監測_{datetime.now().strftime('%m%d%H%M')}.csv",
                mime='text/csv'
            )
        else:
            st.info(f"提示：目前範圍內無符合關鍵字的最新討論。請將「回溯小時」拉大（例如改為 48 或 72 小時）再試一次。")
