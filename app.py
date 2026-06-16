import streamlit as st
import requests
import pandas as pd
from xml.etree import ElementTree
from datetime import datetime, timedelta
import urllib.parse

# 網頁基本設定
st.set_page_config(page_title="社群輿情監測系統 V11", page_icon="📱", layout="centered")

st.title("📱 社群輿情監測系統")
st.caption("版本：V11 (Streamlit 雲端 RSS 官方通道版)")

# 關鍵字說明
with st.expander("ℹ️ 關鍵字與語法說明（點擊展開）", expanded=True):
    st.markdown("""
    * **多組搜尋 (OR)**：用「半形逗號」隔開 (例：`基隆 台電, 停電`)
    * **組內包含 (AND)**：用「空格」隔開 (例：`基隆 台電`)。程式會精準篩選出標題內同時包含這些字詞的討論。
    """)

# 介面輸入欄位
platform = st.selectbox("搜尋平台:", ["全部", "PTT", "Dcard"])
kw_input = st.text_input("請輸入搜尋關鍵字:", value="基隆 台電, 停電")
hours_val = st.number_input("回溯小時:", min_value=1, max_value=720, value=24, step=1)

if st.button("執行即時輿情監測", type="primary"):
    if not kw_input.strip():
        st.warning("提示：請輸入搜尋關鍵字")
    else:
        # 拆解關鍵字組
        search_groups = [g.strip() for g in kw_input.replace('，', ',').split(',') if g.strip()]
        all_discussions = []
        
        # 統一使用本地時間計算
        limit_time = datetime.now() - timedelta(hours=int(hours_val))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 預設監測的熱門看板
        dcard_forums = ["trending", "gossiping", "news", "keelung", "xz"]
        disp_boards = ["Gossiping", "Keelung", "HatePolitics"]

        with st.spinner("透過官方安全通道檢索中..."):
            
            # --- 管道一：Dcard 官方 RSS 頻道 ---
            if platform in ["全部", "Dcard"]:
                for forum in dcard_forums:
                    url = f"https://www.dcard.tw/f/{forum}/.xml"
                    try:
                        res = requests.get(url, headers=headers, timeout=10)
                        if res.status_code == 200:
                            tree = ElementTree.fromstring(res.content)
                            for item in tree.findall('.//item'):
                                title = item.find('title').text if item.find('title') is not None else ""
                                pub_date_str = item.find('pubDate').text
                                
                                # 解析 Dcard 的時區時間 (例如: 2026-06-16T08:00:00.000Z)
                                # 轉換為無時區的 datetime
                                clean_date = pub_date_str.split('.')[0].replace('Z', '')
                                dt = datetime.strptime(clean_date, '%Y-%m-%dT%H:%M:%S') + timedelta(hours=8)
                                
                                if dt > limit_time:
                                    link = item.find('link').text if item.find('link') is not None else ""
                                    
                                    # 進行關鍵字匹配 (支援 AND 邏輯)
                                    for group in search_groups:
                                        words = group.split()
                                        if all(w.lower() in title.lower() for w in words):
                                            all_discussions.append({
                                                "關鍵字組合": group,
                                                "討論標題": f"[Dcard-{forum}] {title}",
                                                "發布時間": dt.strftime('%Y-%m-%d %H:%M'),
                                                "原始連結": link
                                            })
                    except:
                        continue

            # --- 管道二：Disp PTT 官方 RSS 頻道 ---
            if platform in ["全部", "PTT"]:
                for board in disp_boards:
                    url = f"https://disp.cc/b/{board}?xml"
                    try:
                        res = requests.get(url, headers=headers, timeout=10)
                        if res.status_code == 200:
                            tree = ElementTree.fromstring(res.content)
                            for item in tree.findall('.//item'):
                                title = item.find('title').text if item.find('title') is not None else ""
                                pub_date_str = item.find('pubDate').text # RFC822 格式
                                
                                # 解析 Disp 的時間格式
                                clean_date = pub_date_str.replace(' +0800', '')
                                dt = datetime.strptime(clean_date, '%a, %d %b %Y %H:%M:%S')
                                
                                if dt > limit_time:
                                    link = item.find('link').text if item.find('link') is not None else ""
                                    
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

        # --- 顯示結果與下載處理 ---
        if all_discussions:
            df = pd.DataFrame(all_discussions)
            df = df.drop_duplicates(subset=["原始連結"]) # 去除重複項
            
            st.success(f"監測完成！在過去 {hours_val} 小時內共發現 {len(df)} 筆相關輿情討論。")
            st.dataframe(df, use_container_width=True)
            
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 下載輿情報表 (CSV)",
                data=csv_data,
                file_name=f"社群即時追蹤_{datetime.now().strftime('%m%d%H%M')}.csv",
                mime='text/csv'
            )
        else:
            st.info(f"提示：監測的熱門看板中，過去 {hours_val} 小時內查無含有關鍵字的最新討論。")
