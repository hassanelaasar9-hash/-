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

UPLOAD_FOLDER = os.path.abspath("uploaded_reports")
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    conn = sqlite3.connect('expert2m_v6.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # جدول المعاينات
    conn.cursor().execute('''CREATE TABLE IF NOT EXISTS repairs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, client_name TEXT, phone TEXT,
                  tech_name TEXT, assistant_name TEXT, visit_date TEXT,
                  governorate TEXT, address TEXT, report TEXT,
                  notes TEXT, file_path TEXT, cost TEXT)''')
    # جدول الفنيين الجديد
    conn.cursor().execute('''CREATE TABLE IF NOT EXISTS staff
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    conn.commit(); conn.close()
init_db()

# التعديل الوحيد: دالة عرض الـ PDF (تم تحسينها عشان Chrome على السيرفر)
def display_pdf(file_path):
    try:
        filename = os.path.basename(file_path)
        actual_path = os.path.join(UPLOAD_FOLDER, filename)
       
        if os.path.exists(actual_path):
            with open(actual_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            
            # استخدام st.components.v1.iframe مع sandbox فارغ عشان نتجنب حظر Chrome
            html = f'''
            <iframe 
                src="data:application/pdf;base64,{base64_pdf}" 
                width="100%" 
                height="700" 
                type="application/pdf"
                sandbox="">
            </iframe>
            '''
            st.components.v1.html(html, height=720, scrolling=True)
        else:
            st.error(f"الملف غير موجود في المسار: {actual_path}")
    except Exception as e:
        st.error(f"خطأ في عرض الملف: {e}")

ALL_GOVS = ["القاهرة", "الجيزة", "الإسكندرية", "الدقهلية", "البحيرة", "القليوبية", "الغربية", "المنوفية", "الشرقية", "دمياط", "بورسعيد", "السويس", "الإسماعيلية", "كفر الشيخ", "الفيوم", "بني سويف", "المنيا", "أسيوط", "سوهاج", "قنا", "الأقصر", "أسوان"]
tab1, tab2, tab3 = st.tabs(["➕ تسجيل معاينة جديدة", "📊 سجل المعاينات والإدارة", "👥 إدارة الفنيين"])
# --- التبويب الثالث: إدارة الفنيين ---
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
                else:
                    st.warning("برجاء كتابة اسم")
    with col_f2:
        conn = get_db_connection()
        staff_list = pd.read_sql_query("SELECT * FROM staff", conn)
        conn.close()
        if not staff_list.empty:
            st.write("الفنيين المسجلين:")
            for index, row in staff_list.iterrows():
                c_name, c_del = st.columns([3, 1])
                c_name.write(row['name'])
                if c_del.button("حذف", key=f"del_st_{row['id']}"):
                    conn = get_db_connection()
                    conn.cursor().execute("DELETE FROM staff WHERE id=?", (row['id'],))
                    conn.commit(); conn.close()
                    st.rerun()
staff_names = ["لم يتم التحديد"] + [row['name'] for _, row in staff_list.iterrows()] if not staff_list.empty else ["لم يتم التحديد"]
# --- التبويب الأول: التسجيل ---
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
# --- التبويب الثاني: الإدارة ---
with tab2:
    st.subheader("📊 سجل المعاينات")
    conn = get_db_connection()
    df_raw = pd.read_sql_query("SELECT id, client_name as 'العميل', phone as 'التليفون', tech_name as 'الفني', cost as 'التكلفة', visit_date as 'التاريخ' FROM repairs ORDER BY id DESC", conn)
    conn.close()
    if not df_raw.empty:
        search_col1, search_col2 = st.columns([2, 1])
        with search_col1:
            search_query = st.text_input("🔍 ابحث بالاسم، التليفون، أو الفني", placeholder="اكتب للبحث...")
        with search_col2:
            date_filter = st.date_input("📅 فلترة بالتاريخ", value=None)
        df = df_raw.copy()
       
        def make_wa_link(phone_num):
            p = str(phone_num).strip()
            num = p if p.startswith('2') else '2' + p
            return f"https://wa.me/{num}"
       
        df['واتساب'] = df['التليفون'].apply(make_wa_link)
        if search_query:
            df = df[df['العميل'].str.contains(search_query, na=False, case=False) |
                    df['التليفون'].str.contains(search_query, na=False) |
                    df['الفني'].str.contains(search_query, na=False, case=False)]
        if date_filter:
            df = df[df['التاريخ'] == str(date_filter)]
        st.write(f"🔎 تم العثور على {len(df)} سجل")
       
        event = st.dataframe(
            df.drop(columns=['id']),
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "واتساب": st.column_config.LinkColumn("واتساب", display_text="💬 مراسلة")
            }
        )
       
        selected_rows = event.selection.rows
        if selected_rows:
            selected_index = selected_rows[0]
            selected_id = int(df.iloc[selected_index]['id'])
           
            st.divider()
            st.subheader(f"🛠️ إجراءات التعديل: {df.iloc[selected_index]['العميل']}")
           
            conn = get_db_connection()
            row = conn.execute("SELECT * FROM repairs WHERE id=?", (selected_id,)).fetchone()
            conn.close()
           
            with st.form(f"edit_form_{selected_id}"):
                col_l, col_r = st.columns(2)
                with col_l:
                    u_name = st.text_input("اسم العميل", row['client_name'])
                    u_phone = st.text_input("التليفون", row['phone'])
                    current_tech_idx = staff_names.index(row['tech_name']) if row['tech_name'] in staff_names else 0
                    u_tech = st.selectbox("اسم الفني", staff_names, index=current_tech_idx)
                    current_assist_idx = staff_names.index(row['assistant_name']) if row['assistant_name'] in staff_names else 0
                    u_assist = st.selectbox("المساعد", staff_names, index=current_assist_idx)
                with col_r:
                    u_cost = st.text_input("التكلفة", row['cost'])
                    u_gov = st.selectbox("المحافظة", ALL_GOVS, index=ALL_GOVS.index(row['governorate']))
                    u_addr = st.text_input("العنوان", row['address'])
                    u_date = st.date_input("تاريخ المعاينة", datetime.strptime(row['visit_date'], '%Y-%m-%d'))
               
                u_notes = st.text_area("ملاحظات إضافية", row['notes'])
                st.write(f"**وصف العطل المسجل:** {row['report']}")
                st.markdown("---")
                new_pdf = st.file_uploader("تحديث التقرير (PDF)", type=['pdf'], key=f"pdf_up_{selected_id}")
                b_save, b_del, b_pdf = st.columns([1, 1, 2])
               
                if b_save.form_submit_button("💾 حفظ التعديلات"):
                    f_path = row['file_path']
                    if new_pdf:
                        f_path = os.path.join(UPLOAD_FOLDER, f"{u_name}_{new_pdf.name}")
                        with open(f_path, "wb") as f: f.write(new_pdf.getbuffer())
                   
                    conn = get_db_connection()
                    conn.cursor().execute("UPDATE repairs SET client_name=?, phone=?, tech_name=?, assistant_name=?, cost=?, governorate=?, address=?, notes=?, visit_date=?, file_path=? WHERE id=?",
                                        (u_name, u_phone, u_tech, u_assist, u_cost, u_gov, u_addr, u_notes, str(u_date), f_path, selected_id))
                    conn.commit(); conn.close()
                    st.success("تم التحديث!")
                    st.rerun()
               
                if b_del.form_submit_button("🗑️ مسح المعاينة"):
                    conn = get_db_connection()
                    conn.cursor().execute("DELETE FROM repairs WHERE id=?", (selected_id,))
                    conn.commit(); conn.close()
                    st.rerun()
                   
                if b_pdf.form_submit_button("📄 عرض ملف الـ PDF"):
                    if row['file_path']:
                        display_pdf(row['file_path'])
                    else:
                        st.error("❌ لا يوجد ملف مرفق")
    else:
        st.info("لا توجد سجلات حالياً.")
