import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
# 引入能完美模擬瀏覽器 TLS 指紋的庫
from curl_cffi import requests

# 網頁基本設定
st.set_page_config(page_title="Dcard 輿情觀測站", page_icon="🕵️‍♂️", layout="centered")

st.title("🕵️‍♂️ Dcard 輿情即時觀測")
st.caption("Mentat 輿情哨兵 - 瀏覽器級偽裝版 v6.0")

# 建立網頁輸入欄位
keywords = st.text_input("請輸入關鍵字（空格=且，例如：基隆 台電）", "台電")
hours = st.slider("請選擇時間範圍（過去幾小時內）", min_value=1, max_value=72, value=24)

if st.button("🚀 開始檢索 Dcard 輿情", type="primary"):
    check_words = [w.strip() for w in keywords.split() if w.strip()]
    
    if not check_words:
        st.warning("請先輸入關鍵字。")
        st.stop()

    all_posts = []
    
    # 時間與時區設定
    tw_tz = pytz.timezone('Asia/Taipei')
    now_tw = datetime.now(tw_tz)
    time_limit = now_tw - timedelta(hours=hours)
    
    url = "https://www.dcard.tw/_api/posts?popular=false&limit=100"

    with st.spinner("正在進行安全特徵偽裝並對接數據庫..."):
        try:
            # 使用 impersonate="chrome120" 自動模擬真實 Chrome 瀏覽器的所有底層特徵
            response = requests.get(
                url, 
                impersonate="chrome120", 
                timeout=15
            )
            
            if response.status_code == 200:
                posts = response.json()
                
                for post in posts:
                    created_at_str = post.get('createdAt', '')
                    dt_utc = datetime.strptime(created_at_str[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=pytz.utc)
                    dt_tw = dt_utc.astimezone(tw_tz)
                    
                    if dt_tw > time_limit:
                        title = post.get('title', '')
                        excerpt = post.get('excerpt', '')
                        forum_name = post.get('forumName', '')
                        post_id = post.get('id', '')
                        post_url = f"https://www.dcard.tw/f/{post.get('forumAlias', 'trending')}/p/{post_id}"
                        
                        combined_text = (title + " " + excerpt).lower()
                        
                        if all(word.lower() in combined_text for word in check_words):
                            all_posts.append({
                                "發布時間": dt_tw.strftime('%m-%d %H:%M'),
                                "看板": forum_name,
                                "文章標題": title,
                                "內文摘要": excerpt[:60] + "...",
                                "文章連結": post_url
                            })
            else:
                st.error(f"Dcard 拒絕連線 (錯誤碼: {response.status_code})。防爬蟲機制未通過。")
        except Exception as e:
            st.error(f"連線異常: {e}")

    # 顯示結果
    if all_posts:
        df = pd.DataFrame(all_posts)
        st.success(f"採集成功！共發現 {len(df)} 則符合條件的 Dcard 討論。")
        st.dataframe(df, use_container_width=True)
        
        # 轉換成標準 CSV 供手機下載
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="💾 下載 Dcard 輿情報表",
            data=csv_data,
            file_name=f"Dcard輿情_{datetime.now().strftime('%m%d_%H%M')}.csv",
            mime='text/csv',
        )
    else:
        st.warning(f"❌ 過去 {hours} 小時內，Dcard 最新文章中未發現符合條件的討論。")
