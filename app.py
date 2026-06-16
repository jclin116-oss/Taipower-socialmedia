import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
import re

# 網頁基本設定
st.set_page_config(page_title="社群平台討論監測 V10", page_icon="📱", layout="centered")

st.title("📱 社群平台討論監測")
st.caption("版本：V10 (Streamlit 雲端網頁直連版 - 捨棄 Google 接口)")

# 關鍵字說明區塊
with st.expander("ℹ️ 關鍵字與語法說明（點擊展開）", expanded=True):
    st.markdown("""
    * **多組搜尋 (OR)**：用「半形逗號」隔開 (例：`基隆 台電, 停電`)
    * **組內字詞 (AND)**：目前直接搜尋採精準匹配。若輸入 `基隆 台電`，程式會自動尋找同時含有這兩個詞的貼文。
    """)

# 介面輸入欄位
platform = st.selectbox("搜尋平台:", ["全部", "PTT", "Dcard"])
kw_input = st.text_input("請輸入搜尋關鍵字:", value="基隆 台電, 停電")
hours_val = st.number_input("回溯小時:", min_value=1, max_value=720, value=24, step=1)

if st.button("執行抓取並產出 CSV", type="primary"):
    if not kw_input.strip():
        st.warning("提示：請輸入搜尋關鍵字")
    else:
        # 拆解關鍵字組
        search_groups = [g.strip() for g in kw_input.replace('，', ',').split(',') if g.strip()]
        all_discussions = []
        limit_time = datetime.now() - timedelta(hours=int(hours_val))
        
        # 雲端大廠乾淨的模擬標頭
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-TW,zh;q=0.9',
            'Referer': 'https://www.dcard.tw/'
        }
        
        with st.spinner("雲端原生數據檢索中..."):
            
            # --- 管道一：Dcard 網頁前端數據接口 ---
            if platform in ["全部", "Dcard"]:
                for group in search_groups:
                    encoded_kw = urllib.parse.quote(group)
                    # 改走 Dcard 網頁搜尋的公開前端 API
                    dcard_url = f"https://www.dcard.tw/_api/search/posts?query={encoded_kw}&limit=60&sort=latest"
                    try:
                        res = requests.get(dcard_url, headers=headers, timeout=12)
                        if res.status_code == 200:
                            posts = res.json()
                            for post in posts:
                                created_at_str = post.get('createdAt', '').split('.')[0]
                                post_time = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M:%S') + timedelta(hours=8)
                                
                                if post_time > limit_time:
                                    all_discussions.append({
                                        "關鍵字組合": group,
                                        "標題/討論串": f"[Dcard] {post.get('title')}",
                                        "時間": post_time.strftime('%Y-%m-%d %H:%M'),
                                        "連結": f"https://www.dcard.tw/f/all/p/{post.get('id')}"
                                    })
                    except Exception as e:
                        continue

            # --- 管道二：PTT 網頁版（PttWeb）結構檢索 ---
            if platform in ["全部", "PTT"]:
                for group in search_groups:
                    # 取出組內的第一個核心關鍵字做網頁檢索，後續再用程式篩選
                    core_kw = group.split()[0] if group.split() else group
                    encoded_kw = urllib.parse.quote(core_kw)
                    
                    # 透過 PttWeb 網頁版公開接口，抓取最新看板討論
                    ptt_url = f"https://www.pttweb.cc/api/search?q={encoded_kw}&page=0"
                    try:
                        res = requests.get(ptt_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=12)
                        if res.status_code == 200:
                            data = res.json()
                            results = data.get('results', [])
                            for item in results:
                                title = item.get('title', '')
                                
                                # 二次精準過濾：如果關鍵字組是「基隆 台電」，標題或內文摘要必須同時包含這兩個詞
                                filter_words = group.split()
                                if not all(w.lower() in title.lower() for w in filter_words):
                                    continue
                                    
                                # 解析時間戳
                                ts = item.get('createdAt', 0)
                                if ts:
                                    post_time = datetime.fromtimestamp(ts)
                                    if post_time > limit_time:
                                        all_discussions.append({
                                            "關鍵字組合": group,
                                            "標題/討論串": f"[PTT] {title}",
                                            "時間": post_time.strftime('%Y-%m-%d %H:%M'),
                                            "連結": f"https://www.pttweb.cc/bbs/{item.get('bbs', 'Gossiping')}/{item.get('aid', '')}"
                                        })
                    except Exception as e:
                        continue

        # --- 資料顯示與匯出 ---
        if all_discussions:
            df = pd.DataFrame(all_discussions)
            df = df.drop_duplicates(subset=["連結"]) # 移除重複網址
            
            st.success(f"執行成功！本次共撈出 {len(df)} 筆不重複的最新社群原生討論。")
            st.dataframe(df, use_container_width=True)
            
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            
            st.download_button(
                label="📥 下載社群報表 (CSV)",
                data=csv_data,
                file_name=f"社群原生監測_{datetime.now().strftime('%m%d%H%M')}.csv",
                mime='text/csv'
            )
        else:
            st.info("提示：這兩個平台上，在指定的時間範圍內目前沒有符合這些關鍵字的最新討論。")
