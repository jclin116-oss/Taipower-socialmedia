import streamlit as st
import requests
import pandas as pd
from xml.etree import ElementTree
from datetime import datetime, timedelta
import urllib.parse

# 網頁基本設定
st.set_page_config(page_title="社群平台監測 u272260 V4", page_icon="📱", layout="centered")

st.title("📱 社群平台監測")
st.caption("版本：u272260 V4 (Streamlit 網頁版)")

# 關鍵字說明區塊
with st.expander("ℹ️ 關鍵字與語法說明（點擊展開）", expanded=True):
    st.markdown("""
    * **同時包含 (AND)**：關鍵字之間用「空格」 (例：`基隆 台電`)
    * **多組搜尋 (OR)**：用「半形逗號」隔開 (例：`基隆 台電, 停電`)
    """)

# 介面輸入欄位
platform = st.selectbox("搜尋平台:", ["全部", "PTT", "Threads", "Dcard"])

kw_input = st.text_input("請輸入搜尋關鍵字:", value="基隆 台電, 停電")

# 時間選擇（改用數字輸入框）
hours_val = st.number_input("回溯小時:", min_value=1, max_value=720, value=24, step=1)

if st.button("執行抓取並產出 CSV", type="primary"):
    if not kw_input.strip():
        st.warning("提示：請輸入搜尋關鍵字")
    else:
        # 平台過濾語法對應
        p_map = {
            "PTT": "site:ptt.cc",
            "Threads": "site:threads.net",
            "Dcard": "site:dcard.tw",
            "全部": "(site:ptt.cc OR site:threads.net OR site:dcard.tw)"
        }
        site_q = p_map.get(platform, p_map["全部"])
        
        search_groups = [g.strip() for g in kw_input.replace('，', ',').split(',') if g.strip()]
        all_news = []
        limit = datetime.now() - timedelta(hours=int(hours_val))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        with st.spinner("社群資料檢索中..."):
            for group in search_groups:
                try:
                    query_str = group.replace(' ', ' AND ')
                    # 結合關鍵字語法與社群網域篩選器
                    full_query = f"{query_str} {site_q}"
                    encoded_query = urllib.parse.quote(full_query)
                    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
                    
                    res = requests.get(url, timeout=10, headers=headers)
                    try:
                        tree = ElementTree.fromstring(res.content)
                    except ElementTree.ParseError:
                        continue

                    for item in tree.findall('.//item'):
                        pub_date = item.find('pubDate').text
                        # 沿用原版時間格式解析
                        dt = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %Z')
                        
                        if dt > limit:
                            title = item.find('title').text if item.find('title') is not None else "無標題"
                            link = item.find('link').text if item.find('link') is not None else ""
                            tw_time = (dt + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
                            
                            # 配合原版 CSV 的欄位資料架構
                            all_news.append({
                                "關鍵字組合": group,
                                "標題": title,
                                "時間": tw_time,
                                "連結": link
                            })
                except:
                    continue
        
        # 顯示結果與下載處理
        if all_news:
            # 沿用原版的「以連結作為唯一識別」去重機制
            df = pd.DataFrame(all_news)
            df = df.drop_duplicates(subset=["連結"])
            
            st.success(f"執行成功！本次共抓取 {len(df)} 筆不重複社群輿情。")
            
            # 在網頁上展示動態資料表
            st.dataframe(df, use_container_width=True)
            
            # 轉換為 utf-8-sig 格式（確保 Excel 開啟不亂碼）
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            
            # 安全的網頁下載按鈕
            st.download_button(
                label="📥 下載社群報表 (CSV)",
                data=csv_data,
                file_name=f"社群追蹤_{datetime.now().strftime('%m%d%H%M')}.csv",
                mime='text/csv'
            )
        else:
            st.info("提示：查無相關資料")
