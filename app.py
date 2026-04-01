import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime
import base64

# 1. إعدادات المظهر
st.set_page_config(page_title="Expert 2M - Management System", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    [data-testid="stForm"] { border: 1px solid #444; border-radius: 15px; background-color: #1a1c23; }
    </style>
    """, unsafe_allow_html=True)

UPLOAD_FOLDER = "uploaded_reports"
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    conn = sqlite3.connect('expert2m_v6.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.cursor().execute('''CREATE TABLE IF NOT EXISTS repairs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, client_name TEXT, phone TEXT, 
                  tech_name TEXT, assistant_name TEXT, visit_date TEXT, 
                  governorate TEXT, address TEXT, report TEXT, 
                  notes TEXT, file_path TEXT, cost TEXT)''')
    conn.cursor().execute('''CREATE TABLE IF NOT EXISTS staff 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    conn.commit(); conn.close()

init_db()

def display_pdf_preview(file_path):
    try:
        if not file_path or pd.isna(file_path):
            st.error("❌ مفيش ملف مسجل للمعاونة دي.")
            return
            
        filename = os.path.basename(file_path)
        actual_path = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.exists(actual_path):
            with open(actual_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
        else:
            st.error(f"⚠️ الملف مش موجود على السيرفر: {filename}")
    except Exception as e:
        st.error(f"خطأ: {e}")

ALL_GOVS = ["القاهرة", "الجيزة", "الإسكندرية", "الدقهلية", "البحيرة", "القليوبية", "الغربية", "المنوفية", "الشرقية", "دمياط", "بورسعيد", "السويس", "الإسماعيلية", "كفر الشيخ", "الفيوم", "بني سويف", "المنيا", "أسيوط", "سوهاج", "قنا", "الأقصر", "أسوان"]

tab1, tab2, tab3 = st.tabs(["➕ تسجيل معاينة", "📊 السجل والإدارة", "👥 الفنيين"])

with tab3:
    st.subheader("إدارة الفنيين")
    with st.form("add_staff"):
        new_s = st.text_input("اسم الفني")
        if st.form_submit_button("إضافة"):
            if new_s:
                try:
                    conn = get_db_connection()
                    conn.cursor().execute("INSERT INTO staff (name) VALUES (?)", (new_s,))
                    conn.commit(); conn.close()
                    st.rerun()
                except: st.error("موجود فعلاً")

with tab1:
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("الاسم")
        phone = c1.text_input("التليفون")
        cost = c1.text_input("التكلفة")
        gov = c2.selectbox("المحافظة", ALL_GOVS)
        addr = c2.text_input("العنوان")
        date_v = c2.date_input("التاريخ", datetime.now())
        rep = st.text_area("العطل")
        file = st.file_uploader("التقرير (PDF)", type=['pdf'])
        if st.form_submit_button("حفظ"):
            f_path = ""
            if file:
                f_path = os.path.join(UPLOAD_FOLDER, f"{name}_{file.name}")
                with open(f_path, "wb") as f: f.write(file.getbuffer())
            conn = get_db_connection()
            conn.cursor().execute("INSERT INTO repairs (client_name, phone, visit_date, governorate, address, report, file_path, cost) VALUES (?,?,?,?,?,?,?,?)",
                                 (name, phone, str(date_v), gov, addr, rep, f_path, cost))
            conn.commit(); conn.close()
            st.success("تم الحفظ")

with tab2:
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT id, client_name as 'العميل', phone as 'التليفون', cost as 'التكلفة', visit_date as 'التاريخ' FROM repairs ORDER BY id DESC", conn)
    conn.close()

    if not df.empty:
        search = st.text_input("🔍 بحث")
        if search:
            df = df[df['العميل'].str.contains(search, na=False)]
        
        # اختيار السطر
        selection = st.dataframe(df.drop(columns=['id']), use_container_width=True, on_select="rerun", selection_mode="single-row")
        
        if selection.selection.rows:
            # هنا التأمين: بنجيب البيانات من الـ DataFrame الأصلي بناءً على الاختيار
            idx = selection.selection.rows[0]
            sel_id = int(df.iloc[idx]['id'])
            
            conn = get_db_connection()
            row = conn.execute("SELECT * FROM repairs WHERE id=?", (sel_id,)).fetchone()
            conn.close()
            
            if row:
                with st.form(f"edit_{sel_id}"):
                    st.write(f"تعديل: {row['client_name']}")
                    u_cost = st.text_input("التكلفة", row['cost'])
                    new_pdf = st.file_uploader("تحديث التقرير", type=['pdf'])
                    
                    b1, b2, b3 = st.columns(3)
                    if b1.form_submit_button("حفظ التعديل"):
                        p = row['file_path']
                        if new_pdf:
                            p = os.path.join(UPLOAD_FOLDER, f"{row['client_name']}_{new_pdf.name}")
                            with open(p, "wb") as f: f.write(new_pdf.getbuffer())
                        conn = get_db_connection()
                        conn.cursor().execute("UPDATE repairs SET cost=?, file_path=? WHERE id=?", (u_cost, p, sel_id))
                        conn.commit(); conn.close()
                        st.rerun()
                    
                    if b2.form_submit_button("📄 معاينة PDF"):
                        # تأكدنا إننا بنبعت القيمة صحيحة من الداتابيز
                        display_pdf_preview(row['file_path'])
                    
                    if b3.form_submit_button("🗑️ حذف"):
                        conn = get_db_connection()
                        conn.cursor().execute("DELETE FROM repairs WHERE id=?", (sel_id,))
                        conn.commit(); conn.close()
                        st.rerun()
