import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 網頁基本設定
st.set_page_config(page_title="Dcard 輿情觀測站", page_icon="🕵️‍♂️", layout="centered")

st.title("🕵️‍♂️ Dcard 輿情即時觀測")
st.caption("Mentat 輿情哨兵 - Dcard 行動網頁版 v5.0")

# 建立直覺的網頁輸入欄位
keywords = st.text_input("請輸入關鍵字（空格=且，例如：基隆 台電）", "台電")
hours = st.slider("請選擇時間範圍（過去幾小時內）", min_value=1, max_value=72, value=24)

if st.button("🚀 開始檢索 Dcard 輿情", type="primary"):
    # 解析關鍵字（空格代表 AND 邏輯）
    check_words = [w.strip() for w in keywords.split() if w.strip()]
    
    if not check_words:
        st.warning("請先輸入關鍵字。")
        st.stop()

    all_posts = []
    
    # 計算時間限制（設定為台灣時間）
    tw_tz = pytz.timezone('Asia/Taipei')
    now_tw = datetime.now(tw_tz)
    time_limit = now_tw - timedelta(hours=hours)
    
    # Dcard 全站最新文章 API 節點
    url = "https://www.dcard.tw/_api/posts?popular=false&limit=100"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
    }

    with st.spinner("Dcard 數據庫安全對接中，請稍候..."):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                posts = response.json()
                
                for post in posts:
                    # 抓取 Dcard 文章發布時間並轉換成台灣時間
                    created_at_str = post.get('createdAt', '')
                    # Dcard API 回傳格式為 '2026-06-16T02:45:00.000Z'
                    dt_utc = datetime.strptime(created_at_str[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=pytz.utc)
                    dt_tw = dt_utc.astimezone(tw_tz)
                    
                    # 時間篩選
                    if dt_tw > time_limit:
                        title = post.get('title', '')
                        excerpt = post.get('excerpt', '') # 內文摘要
                        forum_name = post.get('forumName', '') # 看板名稱
                        post_id = post.get('id', '')
                        post_url = f"https://www.dcard.tw/f/{post.get('forumAlias', 'trending')}/p/{post_id}"
                        
                        # 合併標題與內文進行關鍵字檢查（必須同時包含所有輸入的字）
                        combined_text = (title + " " + excerpt).lower()
                        
                        if all(word.lower() in combined_text for word in check_words):
                            all_posts.append({
                                "發布時間": dt_tw.strftime('%m-%d %H:%M'),
                                "看板": forum_name,
                                "文章標題": title,
                                "內文摘要": excerpt[:60] + "...", # 只截取前 60 字方便手機閱讀
                                "文章連結": post_url
                            })
            else:
                st.error(f"Dcard 伺服器拒絕連線 (錯誤碼: {response.status_code})")
        except Exception as e:
            st.error(f"連線異常: {e}")

    # 顯示結果
    if all_posts:
        df = pd.DataFrame(all_posts)
        st.success(f"採集成功！共發現 {len(df)} 則符合條件的 Dcard 討論。")
        
        # 在網頁上渲染數據
        st.dataframe(df, use_container_width=True)
        
        # 提供 CSV 下載
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="💾 下載 Dcard 輿情報表",
            data=csv_data,
            file_name=f"Dcard輿情_{datetime.now().strftime('%m%d_%H%M')}.csv",
            mime='text/csv',
        )
    else:
        st.warning(f"❌ 過去 {hours} 小時內，Dcard 全站最新文章中未發現包含「{keywords}」的討論。")
