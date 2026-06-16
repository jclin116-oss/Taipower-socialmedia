import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import re

# 網頁基本設定
st.set_page_config(page_title="PTT 輿情觀測站", page_icon="🕵️‍♂️", layout="centered")

st.title("🕵️‍♂️ PTT 輿情即時觀測")
st.caption("Mentat 輿情哨兵 - PTT 行動網頁版 v7.0")

# 建立填寫欄位
target_board = st.selectbox("請選擇觀測看板", ["Gossiping (八卦)", "HatePolitics (政黑)", "Lifeismoney (省錢)", "Tech_Job (科技職涯)"], index=0)
keywords = st.text_input("請輸入關鍵字（空格=且，例如：基隆 台電）", "台電")
pages_to_crawl = st.slider("請選擇檢索深度（往回搜幾頁）", min_value=1, max_value=20, value=5)

# 提取實際的看板英文代號
board_code = target_board.split()[0]

if st.button("🚀 開始檢索 PTT 輿情", type="primary"):
    check_words = [w.strip() for w in keywords.split() if w.strip()]
    if not check_words:
        st.warning("請先輸入關鍵字。")
        st.stop()

    all_posts = []
    
    # 關鍵設定：繞過 PTT 18歲限制的 Cookie
    session = requests.Session()
    session.cookies.set('over18', '1', domain='www.ptt.cc')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
    }

    # 取得最新頁面的網址
    base_url = f"https://www.ptt.cc/bbs/{board_code}/index.html"
    
    with st.spinner(f"正在對接 PTT {board_code} 板，數據分析中..."):
        current_url = base_url
        
        for page in range(pages_to_crawl):
            try:
                response = session.get(current_url, headers=headers, timeout=10)
                if response.status_code != 200:
                    break
                
                # 簡單利用正則表達式解析網頁，完全不依賴 bs4 減少報錯率
                html = response.text
                
                # 尋找前一頁的網址
                prev_page_match = re.search(r'href="(/bbs/' + board_code + r'/index\d+\.html)">‹ 上頁', html)
                
                # 抓取文章區塊
                # PTT 文章結構：<div class="r-ent">...</div>
                blocks = html.split('<div class="r-ent">')[1:]
                
                for block in blocks:
                    # 排除已被刪除的文章
                    if '(本文已被刪除)' in block:
                        continue
                        
                    # 擷取連結與標題
                    link_match = re.search(r'href="(/bbs/' + board_code + r'/M\.\d+\.A\.[A-Z0-9]+\.html)">([^<]+)</a>', block)
                    date_match = re.search(r'<div class="date">([^<]+)</div>', block)
                    author_match = re.search(r'<div class="author">([^<]+)</div>', block)
                    
                    if link_match and date_match:
                        post_url = "https://www.ptt.cc" + link_match.group(1)
                        title = link_match.group(2).strip()
                        date_str = date_match.group(1).strip()
                        author = author_match.group(1).strip() if author_match else "未知"
                        
                        # 關鍵字條件過濾（必須包含所有輸入的字）
                        if all(word.lower() in title.lower() for word in check_words):
                            all_posts.append({
                                "日期": date_str,
                                "作者": author,
                                "文章標題": title,
                                "文章連結": post_url
                            })
                            
                # 切換到上一頁網址，繼續往回爬
                if prev_page_match:
                    current_url = "https://www.ptt.cc" + prev_page_match.group(1)
                else:
                    break
                    
            except Exception as e:
                st.error(f"掃描分頁時發生異常: {e}")
                break

    # 顯示結果
    if all_posts:
        df = pd.DataFrame(all_posts)
        st.success(f"採集成功！在過去 {pages_to_crawl} 頁中發現 {len(df)} 則符合條件的 PTT 討論。")
        st.dataframe(df, use_container_width=True)
        
        # 轉換成標準 CSV 供手機下載
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="💾 下載 PTT 輿情報表",
            data=csv_data,
            file_name=f"PTT輿情_{board_code}_{datetime.now().strftime('%m%d_%H%M')}.csv",
            mime='text/csv',
        )
    else:
        st.warning(f"❌ 檢索完成，在 {board_code} 板前 {pages_to_crawl} 頁中，未發現標題包含「{keywords}」的文章。")
