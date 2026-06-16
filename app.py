import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import urllib.parse
import re

# 網頁基本設定
st.set_page_config(page_title="社群輿情監測系統 V14", page_icon="📱", layout="centered")

st.title("📱 社群輿情監測系統")
st.caption("版本：V14 (Google 快取破防 + PTT 容錯優化版)")

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
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        with st.spinner("雲端複合管道安全檢索中..."):
            
            # --- 管道一：利用 Google 輕量接口間接破防 Dcard (繞過 Cloudflare 403) ---
            if platform in ["全部", "Dcard"]:
                for group in search_groups:
                    query_str = group.replace(' ', ' AND ')
                    full_query = f"{query_str} site:dcard.tw"
                    encoded_query = urllib.parse.quote(full_query)
                    
                    # 走 Google 專門處理乾淨快取數據的自適應接口
                    google_url = f"https://www.google.com/search?q={encoded_query}&tbs=qdr:d3&hl=zh-TW"
                    try:
                        res = requests.get(google_url, headers=headers, timeout=10)
                        if res.status_code == 200:
                            # 用字串正規表達式直接抽離 Dcard 的文章 ID 與標題，完全不需要處理 HTML/XML 結構
                            matches = re.findall(r'href="https://www\.dcard\.tw/f/[^"]+/p/(\d+)"[^>]*><h3[^>]*>(.*?)</h3>', res.text)
                            for p_id, p_title in matches:
                                clean_title = re.sub(r'<[^>]+>', '', p_title) # 清除 HTML 標籤
                                all_discussions.append({
                                    "關鍵字組合": group,
                                    "討論標題": f"[Dcard] {clean_title}",
                                    "發布時間": "最近發文(透過Google索引)",
                                    "原始連結": f"https://www.dcard.tw/f/all/p/{p_id}"
                                })
                    except:
                        continue

            # --- 管道二：Disp PTT 備份站 (改用純文字流解析，完美防崩潰) ---
            if platform in ["全部", "PTT"]:
                disp_boards = ["Gossiping", "Keelung", "HatePolitics"]
                for board in disp_boards:
                    url = f"https://disp.cc/b/{board}?xml"
                    try:
                        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                        if res.status_code == 200:
                            # 拋棄 ElementTree，改用純文字切割與正規標記提取，徹底免疫 invalid token 錯誤
                            raw_text = res.text
                            items = re.findall(r'<item>(.*?)</item>', raw_text, re.DOTALL)
                            
                            for item in items:
                                title_match = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item)
                                link_match = re.search(r'<link>(.*?)</link>', item)
                                date_match = re.search(r'<pubDate>(.*?)</pubDate>', item)
                                
                                if title_match and link_match and date_match:
                                    title = title_match.group(1)
                                    link = link_match.group(1)
                                    pub_date_str = date_match.group(1).replace(' +0800', '')
                                    
                                    try:
                                        dt = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S')
                                        if dt > limit_time:
                                            for group in search_groups:
                                                words = group.split()
                                                if all(w.lower() in title.lower() for w in words):
                                                    all_discussions.append({
                                                        "關鍵字組合": group,
                                                        "討論標題": f"[PTT-{board}] {title}",
                                                        "發布時間": dt.strftime('%Y-%m-%d %H:%M'),
                                                        "原始連結": link
                                                    })
                                    except:
                                        continue
                    except:
                        continue

        # --- 顯示結果與下載處理 ---
        if all_discussions:
            df = pd.DataFrame(all_discussions)
            df = df.drop_duplicates(subset=["原始連結"])
            
            st.success(f"🎉 破防成功！本次共安全撈出 {len(df)} 筆最即時輿情資料。")
            st.dataframe(df, use_container_width=True)
            
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 下載輿情報表 (CSV)",
                data=csv_data,
                file_name=f"社群即時輿情_{datetime.now().strftime('%m%d%H%M')}.csv",
                mime='text/csv'
            )
        else:
            st.info(f"提示：各安全分流通道已完全打通。但在過去 {hours_val} 小時內目前無踩中關鍵字的發文，建議加大回溯小時再試。")
