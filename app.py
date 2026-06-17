import streamlit as st
import requests
import pandas as pd

# 設定頁面標題
st.set_page_config(page_title="Dcard 資料爬取器", layout="wide")
st.title("Dcard 論壇文章即時檢索")

# 使用者輸入
forum_name = st.text_input("輸入看板名稱 (例如: funny, tech, job)", "funny")
limit = st.slider("抓取篇數", 10, 100, 30)

def fetch_dcard_posts(forum, limit):
    # Dcard API 網址
    url = f"https://www.dcard.tw/service/api/v2/forums/{forum}/posts?limit={limit}"
    
    # 模擬瀏覽器 Header，這點非常重要，不能用 Python 預設值
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://www.dcard.tw/f/{forum}",
        "Origin": "https://www.dcard.tw",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        return None

if st.button("開始抓取"):
    with st.spinner('正在從 Dcard API 獲取資料...'):
        data = fetch_dcard_posts(forum_name, limit)
        
        if data:
            # 整理資料
            processed_data = []
            for post in data:
                processed_data.append({
                    "標題": post.get("title"),
                    "看板": post.get("forumName"),
                    "心情數": post.get("likeCount"),
                    "留言數": post.get("commentCount"),
                    "連結": f"https://www.dcard.tw/f/{forum_name}/p/{post.get('id')}"
                })
            
            df = pd.DataFrame(processed_data)
            st.success(f"成功抓取 {len(df)} 篇文章")
            st.dataframe(df, use_container_width=True)
        else:
            st.error("無法取得資料，可能已被封鎖 IP 或看板名稱錯誤。")

st.info("提示：若頻繁刷新導致抓不到資料，代表 Streamlit 的伺服器 IP 已被 Cloudflare 列入觀察。")
