import streamlit as st
import requests
import pandas as pd
from xml.etree import ElementTree
from datetime import datetime, timedelta
import urllib.parse

# 網頁基本設定
st.set_page_config(page_title="社群平台監測 u272260 V4", page_icon="📱", layout="centered")

st.title("社群平台監測")
st.caption("版本：u272260 V4 (Streamlit 雲端網頁版)")

# 關鍵字說明區塊
with st.expander("ℹ️ 關鍵字與語法說明（點擊展開）", expanded=True):
    st.markdown("""
    * **同時包含 (AND)**：關鍵字之間用「空格」 (例：`基隆 台電`)
    * **多組搜尋 (OR)**：用「半形逗號」隔開 (例：`基隆 台電, 停電`)
    """)

# 介面輸入欄位
platform = st.selectbox("搜尋平台:", ["全部", "PTT", "Threads(停用)", "Dcard"])

kw_input = st.text_input("請輸入搜尋關鍵字:", value="基隆 台電, 停電")

# 時間選擇
hours_val = st.number_input("回溯小時:", min_value=1, max_value=720, value=24, step=1)

if st.button("執行抓取並產出 CSV", type="primary"):
    if not kw_input.strip():
        st.warning("提示：請輸入搜尋關鍵字")
    else:
        # 拆解關鍵字組
        search_groups = [g.strip() for g in kw_input.replace('，', ',').split(',') if g.strip()]
        all_news = []
        limit = datetime.now() - timedelta(hours=int(hours_val))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 【優化機制】如果選全部，後端自動輪流跑完三個平台，解決 Google RSS 的語法衝突限制
        if platform == "全部":
            target_platforms = ["site:ptt.cc", "site:threads.net", "site:dcard.tw"]
        else:
            p_map = {"PTT": "site:ptt.cc", "Threads": "site:threads.net", "Dcard": "site:dcard.tw"}
            target_platforms = [p_map[platform]]
        
        with st.spinner("社群資料檢索中..."):
            for group in search_groups:
                query_str = group.replace(' ', ' AND ')
                
                # 雙層迴圈：確保每個平台都各自獨立向 Google 查詢，絕不漏失
                for site_q in target_platforms:
                    try:
                        full_query = f"{query_str} {site_q}"
                        encoded_query = urllib.parse.quote(full_query)
                        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
                        
                        res = requests.get(url, timeout=10, headers=headers)
                        if res.status_code == 200:
                            try:
                                tree = ElementTree.fromstring(res.content)
                            except ElementTree.ParseError:
                                continue

                            for item in tree.findall('.//item'):
                                pub_date_str = item.find('pubDate').text
                                dt = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %Z')
                                
                                if dt > limit:
                                    title = item.find('title').text if item.find('title') is not None else "無標題"
                                    link = item.find('link').text if item.find('link') is not None else ""
                                    tw_time = (dt + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
                                    
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
            df = pd.DataFrame(all_news)
            # 以網址進行全網唯一去重，確保合併三大平台資料時不會有重複列
            df = df.drop_duplicates(subset=["連結"])
            
            st.success(f"執行成功！本次共抓取 {len(df)} 筆不重複社群輿情。")
            st.dataframe(df, use_container_width=True)
            
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            
            st.download_button(
                label="📥 下載社群報表 (CSV)",
                data=csv_data,
                file_name=f"社群追蹤_{datetime.now().strftime('%m%d%H%M')}.csv",
                mime='text/csv'
            )
        else:
            st.info("提示：查無相關資料")
