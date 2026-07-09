import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="PTT輿情", layout="wide")
st.title("⚡PTT輿情")
st.caption("115.6.15 u272260")

# --- 操控區 ---
st.sidebar.header("設定搜尋條件")
# 讓使用者輸入多個關鍵字，用逗號隔開
keyword_input = st.sidebar.text_input("輸入關鍵字 (用逗號隔開)", "停電,台電")
logic_mode = st.sidebar.radio("篩選邏輯", ["包含任一 (OR)", "包含全部 (AND)"])
pages = st.sidebar.slider("往後查找幾頁", 1, 20, 1)

# --- 處理邏輯 ---
def filter_posts(df, keywords, mode):
    if df.empty:
        return df
    
    # 將輸入字串轉為列表
    kw_list = [k.strip() for k in keywords.split(',') if k.strip()]
    
    if not kw_list:
        return df
    
    if mode == "包含全部 (AND)":
        # 標題必須包含列表內所有的關鍵字
        mask = df['標題'].apply(lambda x: all(kw in x for kw in kw_list))
    else:
        # 標題只要包含列表內任一個關鍵字
        mask = df['標題'].apply(lambda x: any(kw in x for kw in kw_list))
        
    return df[mask]

def run_scraper(keyword, pages):
    all_posts = []
    # 以第一個關鍵字進行搜尋 (PTT 搜尋至少需要一個主關鍵字)
    main_kw = keyword.split(',')[0].strip()
    
    for i in range(pages):
        url = f"https://www.ptt.cc/bbs/Gossiping/search?q={main_kw}&page={i}"
        headers = {"cookie": "over18=1"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.select(".r-ent")
            for art in articles:
                title_tag = art.select_one(".title a")
                date_tag = art.select_one(".date")
                if title_tag:
                    all_posts.append({
                        "日期": date_tag.text.strip() if date_tag else "無",
                        "標題": title_tag.text.strip(),
                        "連結": "https://www.ptt.cc" + title_tag['href']
                    })
    return pd.DataFrame(all_posts)

# --- 執行區 ---
if st.sidebar.button("開始執行爬取"):
    with st.spinner('正在找資料...'):
        # 1. 先抓取大範圍資料
        df = run_scraper(keyword_input, pages)
        
        # 2. 進行篩選
        df_filtered = filter_posts(df, keyword_input, logic_mode)
        
        if not df_filtered.empty:
            st.success(f"篩選後共找到 {len(df_filtered)} 篇文章！")
            st.dataframe(df_filtered, use_container_width=True)
            
            csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
            st.download_button("下載搜尋結果 (CSV)", csv, "ptt_result.csv", "text/csv")
        else:
            st.warning("沒找到符合條件的資料，試著放寬關鍵字或增加頁數。")
