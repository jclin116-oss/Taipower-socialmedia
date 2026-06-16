import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import re

# 網頁基本設定
st.set_page_config(page_title="PTT 全方位輿情觀測站", page_icon="🕵️‍♂️", layout="centered")

st.title("🕵️‍♂️ PTT 輿情多板聯合觀測")
st.caption("Mentat 輿情哨兵 - PTT 跨板自動檢索版 v8.0")

# 這裡預設鎖定組織最關心的核心看板，你可以自由增減
BOARDS = ["Gossiping", "HatePolitics", "Lifeismoney", "Keelung", "Tech_Job"]

# 建立填寫欄位（已移除看板下拉選單）
keywords = st.text_input("請輸入關鍵字（空格=且，例如：基隆 台電）", "台電")
hours = st.slider("請選擇時間範圍（過去幾小時內）", min_value=1, max_value=72, value=24)

if st.button("🚀 開始全板檢索 PTT 輿情", type="primary"):
    check_words = [w.strip() for w in keywords.split() if w.strip()]
    if not check_words:
        st.warning("請先輸入關鍵字。")
        st.stop()

    all_posts = []
    
    # 計算時間截止點
    now = datetime.now()
    time_limit = now - timedelta(hours=hours)
    
    # 繞過 PTT 18歲限制的 Cookie
    session = requests.Session()
    session.cookies.set('over18', '1', domain='www.ptt.cc')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # 進度條提示
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, board_code in enumerate(BOARDS):
        status_text.markdown(f"🔄 正在檢索 **{board_code}** 板...")
        progress_bar.progress((idx) / len(BOARDS))
        
        current_url = f"https://www.ptt.cc/bbs/{board_code}/index.html"
        max_pages = 5 # 多板聯搜時，每板往回爬5頁即足夠涵蓋近期時段，避免過久
        stop_crawling = False
        
        for page in range(max_pages):
            if stop_crawling:
                break
                
            try:
                response = session.get(current_url, headers=headers, timeout=10)
                if response.status_code != 200:
                    break
                
                html = response.text
                prev_page_match = re.search(r'href="(/bbs/' + board_code + r'/index\d+\.html)">‹ 上頁', html)
                blocks = html.split('<div class="r-ent">')[1:]
                
                for block in reversed(blocks):
                    if '(本文已被刪除)' in block:
                        continue
                        
                    link_match = re.search(r'href="(/bbs/' + board_code + r'/M\.\d+\.A\.[A-Z0-9]+\.html)">([^<]+)</a>', block)
                    author_match = re.search(r'<div class="author">([^<]+)</div>', block)
                    
                    if link_match:
                        post_url = "https://www.ptt.cc" + link_match.group(1)
                        title = link_match.group(2).strip()
                        author = author_match.group(1).strip() if author_match else "未知"
                        
                        # 先初步過濾關鍵字
                        if all(word.lower() in title.lower() for word in check_words):
                            # 點進內文抓取精確時間
                            try:
                                post_res = session.get(post_url, headers=headers, timeout=5)
                                if post_res.status_code == 200:
                                    time_matches = re.findall(r'<span class="article-meta-value">([^<]+)</span>', post_res.text)
                                    
                                    if time_matches and len(time_matches) >= 4:
                                        full_date_str = time_matches[3]
                                        post_time = datetime.strptime(full_date_str, "%a %b %d %H:%M:%S %Y")
                                        
                                        if post_time >= time_limit:
                                            all_posts.append({
                                                "發布時間": post_time.strftime('%m-%d %H:%M'),
                                                "來源看板": board_code,
                                                "作者": author,
                                                "文章標題": title,
                                                "文章連結": post_url
                                            })
                                        else:
                                            # 該板已遇到過舊文章，停止該板搜尋
                                            stop_crawling = True
                                            break
                            except Exception:
                                continue
                                
                if prev_page_match and not stop_crawling:
                    current_url = "https://www.ptt.cc" + prev_page_match.group(1)
                else:
                    break
                    
            except Exception:
                break

    # 清除進度條提示
    progress_bar.empty()
    status_text.empty()

    # 顯示結果
    if all_posts:
        df = pd.DataFrame(all_posts)
        # 跨板混合後，統一依照時間由新到舊排序
        df = df.sort_values(by="發布時間", ascending=False)
        
        st.success(f"採集成功！過去 {hours} 小時內在各看板中共發現 {len(df)} 則符合條件的討論。")
        st.dataframe(df, use_container_width=True)
        
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="💾 下載跨板輿情報表",
            data=csv_data,
            file_name=f"PTT跨板輿情_{datetime.now().strftime('%m%d_%H%M')}.csv",
            mime='text/csv',
        )
    else:
        st.warning(f"❌ 檢索完成，過去 {hours} 小時內，指定看板中未發現任何標題包含「{keywords}」的文章。")
