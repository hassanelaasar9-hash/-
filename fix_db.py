import streamlit as st
import sqlite3
import pandas as pd
import os

st.set_page_config(page_title="إصلاح قاعدة البيانات", layout="wide")

st.title("🔧 إصلاح قاعدة البيانات - ارفع ملفك هنا")

# زر رفع الملف
uploaded_file = st.file_uploader("ارفع ملف expert2m_v6.db", type=['db'])

if uploaded_file is not None:
    # حفظ الملف
    with open("expert2m_v6.db", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success("✅ تم رفع الملف بنجاح!")
    
    # فتح وتعديل قاعدة البيانات
    conn = sqlite3.connect("expert2m_v6.db")
    cursor = conn.cursor()
    
    # إضافة العمود الجديد
    try:
        cursor.execute("ALTER TABLE repairs ADD COLUMN phone2 TEXT")
        st.success("✅ تم إضافة عمود رقم التليفون الثاني")
    except:
        st.info("عمود phone2 موجود بالفعل")
    
    conn.commit()
    
    # عرض عدد السجلات
    df = pd.read_sql_query("SELECT COUNT(*) as count FROM repairs", conn)
    st.write(f"📊 عدد السجلات: {df['count'].values[0]}")
    
    conn.close()
    
    # تحميل الملف بعد التعديل
    with open("expert2m_v6.db", "rb") as f:
        st.download_button(
            label="📥 تحميل قاعدة البيانات بعد الإصلاح",
            data=f.read(),
            file_name="expert2m_v6_fixed.db",
            mime="application/octet-stream"
        )