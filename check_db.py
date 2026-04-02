import streamlit as st
import sqlite3
import pandas as pd
import os

st.set_page_config(page_title="فحص قاعدة البيانات", layout="wide")

st.title("🔍 فحص قاعدة البيانات - حالة طوارئ")

st.write("### 1. الملفات الموجودة في السيرفر:")
files = os.listdir('.')
for f in files:
    st.write(f"- {f}")

st.write("### 2. هل قاعدة البيانات موجودة؟")
if os.path.exists("expert2m_v6.db"):
    st.success("✅ نعم - قاعدة البيانات موجودة")
    
    conn = sqlite3.connect("expert2m_v6.db")
    df_count = pd.read_sql_query("SELECT COUNT(*) as count FROM repairs", conn)
    count = df_count['count'].values[0]
    st.write(f"### عدد السجلات في قاعدة البيانات: **{count}**")
    
    if count > 0:
        st.success(f"✅ البيانات موجودة! عدد السجلات: {count}")
        data = pd.read_sql_query("SELECT * FROM repairs", conn)
        st.dataframe(data)
    else:
        st.error("❌ قاعدة البيانات موجودة بس فاضية - مفيش سجلات")
    conn.close()
else:
    st.error("❌ لا - قاعدة البيانات مش موجودة")

st.write("### 3. مجلد الملفات المرفوعة:")
if os.path.exists("uploaded_reports"):
    reports = os.listdir("uploaded_reports")
    if reports:
        st.write(f"عدد ملفات PDF: {len(reports)}")
        for r in reports:
            st.write(f"- {r}")
    else:
        st.warning("مجلد uploaded_reports موجود بس فاضي")
else:
    st.warning("مجلد uploaded_reports مش موجود")

st.write("### 4. مجلد النسخ الاحتياطية:")
if os.path.exists("backups"):
    backups = os.listdir("backups")
    if backups:
        st.write("النسخ الاحتياطية الموجودة:")
        for b in backups:
            st.write(f"- {b}")
    else:
        st.warning("مجلد backups موجود بس فاضي")
else:
    st.warning("مجلد backups مش موجود")