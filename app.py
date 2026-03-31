import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime
import base64

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
if not os.path.exists(UPLOAD_FOLDER): 
    os.makedirs(UPLOAD_FOLDER)

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
                  notes TEXT, file_name TEXT, cost TEXT)''')
    conn.cursor().execute('''CREATE TABLE IF NOT EXISTS staff
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    conn.commit()
    conn.close()
init_db()

def get_pdf_base64(file_name):
    """قراءة الملف وتحويله إلى base64"""
    try:
        if not file_name:
            return None
        
        actual_path = os.path.join(UPLOAD_FOLDER, file_name)
       
        if not os.path.exists(actual_path):
            return None
        
        with open(actual_path, "rb") as f:
            pdf_bytes = f.read()
        
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        return base64_pdf
        
    except Exception as e:
        return None

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
                        conn.commit()
                        conn.close()
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
                    conn.commit()
                    conn.close()
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
            file_name = ""
            if file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"{name}_{timestamp}_{file.name}"
                file_path = os.path.join(UPLOAD_FOLDER, file_name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
            conn = get_db_connection()
            conn.cursor().execute("INSERT INTO repairs (client_name, phone, visit_date, governorate, address, report, file_name, cost, tech_name, assistant_name, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                 (name, phone, str(date_v), gov, addr, rep, file_name, cost, "", "", ""))
            conn.commit()
            conn.close()
            st.success("✅ تم الحفظ بنجاح!")

# --- التبويب الثاني: الإدارة ---
with tab2:
    st.subheader("📊 سجل المعاينات")
    conn = get_db_connection()
    df_raw = pd.read_sql_query("SELECT id, client_name as 'العميل', phone as 'التليفون', tech_name as 'الفني', cost as 'التكلفة', visit_date as 'التاريخ', file_name FROM repairs ORDER BY id DESC", conn)
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
            df.drop(columns=['id', 'file_name']),
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
            
            # عرض زر فتح PDF في تاب جديد
            if row['file_name']:
                st.info(f"📎 الملف المرفق: {row['file_name']}")
                
                # الحصول على base64 للملف
                pdf_base64 = get_pdf_base64(row['file_name'])
                
                if pdf_base64:
                    # إنشاء رابط لفتح PDF في تاب جديد
                    pdf_link = f'data:application/pdf;base64,{pdf_base64}'
                    
                    # زر لفتح PDF في تاب جديد
                    st.markdown(f'''
                        <a href="{pdf_link}" target="_blank" style="
                            display: inline-block;
                            background-color: #ff4b4b;
                            color: white;
                            padding: 8px 16px;
                            text-decoration: none;
                            border-radius: 5px;
                            font-weight: bold;
                            margin: 10px 0;
                        ">
                            📄 عرض التقرير (يفتح في تاب جديد)
                        </a>
                    ''', unsafe_allow_html=True)
                else:
                    st.error("⚠️ الملف غير موجود")
                
                st.markdown("---")
            else:
                st.info("📭 لا يوجد ملف مرفق")
                st.markdown("---")
           
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
                b_save, b_del = st.columns([1, 1])
               
                if b_save.form_submit_button("💾 حفظ التعديلات"):
                    file_name = row['file_name']
                    if new_pdf:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        file_name = f"{u_name}_{timestamp}_{new_pdf.name}"
                        file_path = os.path.join(UPLOAD_FOLDER, file_name)
                        with open(file_path, "wb") as f:
                            f.write(new_pdf.getbuffer())
                        if row['file_name']:
                            old_path = os.path.join(UPLOAD_FOLDER, row['file_name'])
                            if os.path.exists(old_path):
                                try:
                                    os.remove(old_path)
                                except:
                                    pass
                   
                    conn = get_db_connection()
                    conn.cursor().execute("UPDATE repairs SET client_name=?, phone=?, tech_name=?, assistant_name=?, cost=?, governorate=?, address=?, notes=?, visit_date=?, file_name=? WHERE id=?",
                                        (u_name, u_phone, u_tech, u_assist, u_cost, u_gov, u_addr, u_notes, str(u_date), file_name, selected_id))
                    conn.commit()
                    conn.close()
                    st.success("تم التحديث!")
                    st.rerun()
               
                if b_del.form_submit_button("🗑️ مسح المعاينة"):
                    if row['file_name']:
                        file_to_delete = os.path.join(UPLOAD_FOLDER, row['file_name'])
                        if os.path.exists(file_to_delete):
                            try:
                                os.remove(file_to_delete)
                            except:
                                pass
                    conn = get_db_connection()
                    conn.cursor().execute("DELETE FROM repairs WHERE id=?", (selected_id,))
                    conn.commit()
                    conn.close()
                    st.success("تم المسح!")
                    st.rerun()
    else:
        st.info("لا توجد سجلات حالياً.")
