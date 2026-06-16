import streamlit as st
import requests
import pandas as pd
from xml.etree import ElementTree
from datetime import datetime, timedelta
import urllib.parse

st.set_page_config(page_title="社群輿情監測系統 V13_偵錯版", page_icon="📱", layout="centered")

st.title("📱 社群輿情監測系統 (驗證診斷版)")
st.caption("版本：V13 (帶有 Cloudflare 驗證牆攔截偵測)")

platform = st.selectbox("搜尋平台:", ["全部", "PTT", "Dcard"])
kw_input = st.text_input("請輸入搜尋關鍵字:", value="基隆 台電")
hours_val = st.number_input("回溯小時:", min_value=1, max_value=720, value=48, step=1)

if st.button("執行即時輿情監測", type="primary"):
    search_groups = [g.strip() for g in kw_input.replace('，', ',').split(',') if g.strip()]
    all_discussions = []
    limit_time = datetime.now() - timedelta(hours=int(hours_val))
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # 建立一個區域用來顯示連線診斷報告
    st.subheader("🌐 伺服器連線狀態診斷")
    
    # --- Dcard 診斷 ---
    if platform in ["全部", "Dcard"]:
        test_url = "https://www.dcard.tw/_api/search/posts?query=%E5%8F%B0%E9%9B%BB&limit=1"
        try:
            res = requests.get(test_url, headers=headers, timeout=10)
            if res.status_code == 200:
                st.success(f"✅ Dcard 連線成功 (狀態碼: 200)")
                # 嘗試解析資料
                posts = res.json()
                for post in posts:
                    created_at_str = post.get('createdAt', '').split('.')[0]
                    dt = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M:%S') + timedelta(hours=8)
                    if dt > limit_time:
                        title = post.get('title', '')
                        all_discussions.append({"關鍵字組合": kw_input, "討論標題": f"[Dcard] {title}", "發布時間": dt.strftime('%Y-%m-%d %H:%M'), "原始連結": f"https://www.dcard.tw/f/all/p/{post.get('id')}"})
            elif res.status_code in [403, 503]:
                st.error(f"❌ Dcard 連線失敗 (狀態碼: {res.status_code})：已被 Cloudflare 驗證牆封鎖（要求圖形驗證）。")
            else:
                st.warning(f"⚠️ Dcard 回傳異常狀態碼: {res.status_code}")
        except Exception as e:
            st.error(f"❌ Dcard 連線異常: {str(e)}")

    # --- PTT (Disp) 診斷 ---
    if platform in ["全部", "PTT"]:
        test_url = "https://disp.cc/b/Gossiping?xml"
        try:
            res = requests.get(test_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if res.status_code == 200:
                st.success(f"✅ PTT (Disp) 連線成功 (狀態碼: 200)")
                tree = ElementTree.fromstring(res.content)
                for item in tree.findall('.//item'):
                    title = item.find('title').text if item.find('title') is not None else ""
                    pub_date_str = item.find('pubDate').text
                    clean_date = pub_date_str.replace(' +0800', '')
                    dt = datetime.strptime(clean_date, '%a, %d %b %Y %H:%M:%S')
                    if dt > limit_time:
                        link = item.find('link').text if item.find('link') is not None else ""
                        all_discussions.append({"關鍵字組合": kw_input, "討論標題": f"[PTT] {title}", "發布時間": dt.strftime('%Y-%m-%d %H:%M'), "原始連結": link})
            elif res.status_code in [403, 503]:
                st.error(f"❌ PTT (Disp) 連線失敗 (狀態碼: {res.status_code})：已被安全防禦牆攔截。")
            else:
                st.warning(f"⚠️ PTT (Disp) 回傳異常狀態碼: {res.status_code}")
        except Exception as e:
            st.error(f"❌ PTT 連線異常: {str(e)}")

    # --- 結果輸出 ---
    st.markdown("---")
    if all_discussions:
        df = pd.DataFrame(all_discussions)
        st.success(f"資料撈取成功，共 {len(df)} 筆。")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("診斷結果：未取得任何符合時間範圍內的資料。若上方顯示 403/503，代表雲端機房已被目標網站全面封鎖。")
