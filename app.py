import streamlit as st
import sqlite3
import pandas as pd

st.title("Dcard 停電議題輿情監測")

def load_data():
    conn = sqlite3.connect('dcard_data.db')
    df = pd.read_sql("SELECT * FROM posts", conn)
    conn.close()
    return df

try:
    df = load_data()
    st.write(f"目前共收集 {len(df)} 篇相關文章")
    st.dataframe(df)
except:
    st.error("找不到資料庫檔案，請確認 dcard_data.db 是否已上傳至 GitHub。")
