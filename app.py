import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime
import base64

# 1. إعدادات المظهر (Dark Mode)
st.set_page_config(page_title="Expert 2M - Management System", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    [data-testid="stForm"] { border: 1px solid #444; border-radius: 15px; background-color: #1a1c23; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #1a1c23; border-radius: 10px 10px 0 0; }
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

# دالة العرض الداخلي (Preview) بدون تحميل
def display_pdf_preview(file_path):
    try:
        if not file_path:
            st.error("❌ لا يوجد ملف مسجل لهذه المعاينة")
            return
            
        filename = os.path.basename(file_path)
        actual_path = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.exists(actual_path):
            with open(actual_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            
            # عرض الملف جوه برواز (iframe) عشان ميعملش داونلود
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
            st.info(f"💡 نصيحة: لو عايز تحمل الملف فعلاً، استخدم زرار الطباعة أو التحميل اللي جوه عرض الـ PDF.")
        else:
            st.error(f"⚠️ الملف غير موجود على السيرفر: {filename}")
    except Exception as e:
        st.error(f"خطأ في المعاينة: {e}")

ALL_GOVS = ["القاهرة", "الجيزة", "الإسكندرية", "الدقهلية", "البحيرة", "القليوبية", "الغربية", "المنوفية", "الشرقية", "دمياط", "بورسعيد", "السويس", "الإسماعيلية", "كفر الشيخ", "الفيوم", "بني سويف", "المنيا", "أسيوط", "سوهاج", "قنا", "الأقصر", "أسوان"]

tab1, tab2, tab3 = st.tabs(["➕ تسجيل معاينة جديدة", "📊 سجل المعاينات والإدارة", "👥 إدارة الفنيين"])

# --- إدارة الفنيين ---
with tab3:
    st.subheader("👥 إدارة قاعدة بيانات الفنيين")
    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        with st.form("add_staff_form"):
            new_staff = st.text_input("اسم الفني الجديد")
            if st.form_submit_button("إضافة فني"):
                if new_staff:
                    try:
                        conn = get_db_connection()
                        conn.cursor().execute("INSERT INTO staff (name) VALUES (?)", (new_staff,))
                        conn.commit(); conn.close()
                        st.success(f"تم إضافة {new_staff}")
                        st.rerun()
                    except:
                        st.error("الاسم موجود بالفعل")
    with col_f2:
        conn = get_db_connection()
        staff_df = pd.read_sql_query("SELECT * FROM staff", conn)
        conn.close()
        if not staff_df.empty:
            for index, row in staff_df.iterrows():
                c_name, c_del = st.columns([3, 1])
                c_name.write(row['name'])
                if c_del.button("حذف", key=f"del_{row['id']}"):
                    conn = get_db_connection()
                    conn.cursor().execute("DELETE FROM staff WHERE id=?", (row['id'],))
                    conn.commit(); conn.close()
                    st.rerun()

staff_names = ["لم يتم التحديد"] + [r['name'] for _, r in staff_df.iterrows()] if 'staff_df' in locals() and not staff_df.empty else ["لم يتم التحديد"]

# --- تسجيل معاينة جديدة ---
with tab1:
    st.subheader("📝 إضافة بيانات العميل")
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("اسم العميل")
            phone = st.text_input("رقم التليفون")
            cost = st.text_input("التكلفة (EGP)")
        with c2:
            gov = st.selectbox("المحافظة", ALL_GOVS)
            addr = st.text_input("العنوان بالتفصيل")
            date_v = st.date_input("التاريخ", datetime.now())
        rep = st.text_area("وصف العطل")
        file = st.file_uploader("ارفع التقرير (PDF)", type=['pdf'])
        if st.form_submit_button("حفظ البيانات النهائية"):
            f_path = ""
            if file:
                f_path = os.path.join(UPLOAD_FOLDER, f"{name}_{file.name}")
                with open(f_path, "wb") as f: f.write(file.getbuffer())
            conn = get_db_connection()
            conn.cursor().execute("INSERT INTO repairs (client_name, phone, visit_date, governorate, address, report, file_path, cost, tech_name, assistant_name, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                 (name, phone, str(date_v), gov, addr, rep, f_path, cost, "", "", ""))
            conn.commit(); conn.close()
            st.success("✅ تم الحفظ بنجاح!")

# --- سجل المعاينات والإدارة ---
with tab2:
    st.subheader("📊 سجل المعاينات")
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT id, client_name as 'العميل', phone as 'التليفون', tech_name as 'الفني', cost as 'التكلفة', visit_date as 'التاريخ' FROM repairs ORDER BY id DESC", conn)
    conn.close()

    if not df.empty:
        search = st.text_input("🔍 بحث بالاسم أو التليفون...")
        if search:
            df = df[df['العميل'].str.contains(search, na=False) | df['التليفون'].str.contains(search, na=False)]
        
        event = st.dataframe(df.drop(columns=['id']), use_container_width=True, on_select="rerun", selection_mode="single-row")
        
        if event.selection.rows:
            sel_id = int(df.iloc[event.selection.rows[0]]['id'])
            conn = get_db_connection()
            row = conn.execute("SELECT * FROM repairs WHERE id=?", (sel_id,)).fetchone()
            conn.close()
            
            with st.form(f"edit_{sel_id}"):
                u_name = st.text_input("الاسم", row['client_name'])
                u_cost = st.text_input("التكلفة", row['cost'])
                st.write(f"المحافظة: {row['governorate']} | العنوان: {row['address']}")
                new_pdf = st.file_uploader("تحديث التقرير (اختياري)", type=['pdf'])
                
                b1, b2, b3 = st.columns(3)
                if b1.form_submit_button("💾 حفظ التعديلات"):
                    p = row['file_path']
                    if new_pdf:
                        p = os.path.join(UPLOAD_FOLDER, f"{u_name}_{new_pdf.name}")
                        with open(p, "wb") as f: f.write(new_pdf.getbuffer())
                    conn = get_db_connection()
                    conn.cursor().execute("UPDATE repairs SET client_name=?, cost=?, file_path=? WHERE id=?", (u_name, u_cost, p, sel_id))
                    conn.commit(); conn.close()
                    st.success("تم التحديث!")
                    st.rerun()
                
                if b2.form_submit_button("📄 معاينة التقرير (Preview)"):
                    display_pdf_preview(row['file_path'])
                
                if b3.form_submit_button("🗑️ حذف السجل"):
                    conn = get_db_connection()
                    conn.cursor().execute("DELETE FROM repairs WHERE id=?", (sel_id,))
                    conn.commit(); conn.close()
                    st.rerun()
    else:
        st.info("لا توجد سجلات حالياً.")
