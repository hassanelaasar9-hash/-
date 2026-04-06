import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime
import base64
import shutil
import json
import zipfile
import hashlib
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Expert 2M - Management System", layout="wide")

# إعدادات المصادقة
ADMIN_USERNAME = "admin"
# غير كلمة المرور دي بعد أول استخدام (SHA256)
ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()

def check_password():
    """التحقق من تسجيل الدخول"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🔐 تسجيل الدخول")
            username = st.text_input("اسم المستخدم")
            password = st.text_input("كلمة المرور", type="password")
            
            if st.button("دخول", use_container_width=True):
                if username == ADMIN_USERNAME and hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")
        return False
    return True

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    [data-testid="stForm"] { border: 1px solid #444; border-radius: 15px; background-color: #1a1c23; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #1a1c23; border-radius: 10px 10px 0 0; }
    .metric-card { background-color: #1a1c23; border-radius: 10px; padding: 15px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

UPLOAD_FOLDER = "uploaded_reports"
BACKUP_FOLDER = "backups"
AUTO_BACKUP_FOLDER = "auto_backups"

if not os.path.exists(UPLOAD_FOLDER): 
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(BACKUP_FOLDER): 
    os.makedirs(BACKUP_FOLDER)
if not os.path.exists(AUTO_BACKUP_FOLDER): 
    os.makedirs(AUTO_BACKUP_FOLDER)

def get_db_connection():
    conn = sqlite3.connect('expert2m_v6.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS repairs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, client_name TEXT, phone TEXT, phone2 TEXT,
                  tech_name TEXT, assistant_name TEXT, visit_date TEXT,
                  governorate TEXT, address TEXT, report TEXT,
                  notes TEXT, file_name TEXT, cost TEXT)''')
    
    try:
        cursor.execute("ALTER TABLE repairs ADD COLUMN phone2 TEXT")
    except:
        pass
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS staff
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    
    # إضافة بعض الفنيين افتراضياً
    default_staff = ["محمد احمد", "احمد محمد", "محمود على"]
    for staff in default_staff:
        try:
            cursor.execute("INSERT INTO staff (name) VALUES (?)", (staff,))
        except:
            pass
    
    conn.commit()
    conn.close()
init_db()

def auto_backup():
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(AUTO_BACKUP_FOLDER, f"auto_backup_{timestamp}.db")
        shutil.copy2('expert2m_v6.db', backup_file)
        
        backups = sorted([f for f in os.listdir(AUTO_BACKUP_FOLDER) if f.endswith('.db')])
        while len(backups) > 50:
            os.remove(os.path.join(AUTO_BACKUP_FOLDER, backups.pop(0)))
        return True
    except:
        return False

def create_backup():
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = os.path.join(BACKUP_FOLDER, backup_name)
        os.makedirs(backup_path)
        
        shutil.copy2('expert2m_v6.db', os.path.join(backup_path, 'expert2m_v6.db'))
        
        reports_backup = os.path.join(backup_path, 'reports')
        if os.path.exists(UPLOAD_FOLDER):
            shutil.copytree(UPLOAD_FOLDER, reports_backup)
        
        conn = get_db_connection()
        df_repairs = pd.read_sql_query("SELECT * FROM repairs", conn)
        df_staff = pd.read_sql_query("SELECT * FROM staff", conn)
        conn.close()
        
        df_repairs.to_json(os.path.join(backup_path, 'repairs.json'), orient='records', force_ascii=False)
        df_staff.to_json(os.path.join(backup_path, 'staff.json'), orient='records', force_ascii=False)
        
        info = {
            'backup_date': timestamp,
            'backup_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'repairs_count': len(df_repairs),
            'staff_count': len(df_staff),
            'pdf_files_count': len(os.listdir(UPLOAD_FOLDER)) if os.path.exists(UPLOAD_FOLDER) else 0
        }
        
        with open(os.path.join(backup_path, 'backup_info.json'), 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        
        zip_path = os.path.join(BACKUP_FOLDER, f"{backup_name}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, backup_path)
                    zipf.write(file_path, arcname)
        
        shutil.rmtree(backup_path)
        return zip_path, info
    except Exception as e:
        st.error(f"خطأ في إنشاء النسخة الاحتياطية: {e}")
        return None, None

def restore_backup(zip_file):
    try:
        extract_path = os.path.join(BACKUP_FOLDER, "temp_restore")
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
        
        with zipfile.ZipFile(zip_file, 'r') as zipf:
            zipf.extractall(extract_path)
        
        with open(os.path.join(extract_path, 'backup_info.json'), 'r', encoding='utf-8') as f:
            info = json.load(f)
        
        shutil.copy2(os.path.join(extract_path, 'expert2m_v6.db'), 'expert2m_v6.db')
        
        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER)
        shutil.copytree(os.path.join(extract_path, 'reports'), UPLOAD_FOLDER)
        
        shutil.rmtree(extract_path)
        return info
    except Exception as e:
        st.error(f"خطأ في استعادة النسخة: {e}")
        return None

def export_data_to_excel():
    try:
        conn = get_db_connection()
        df_repairs = pd.read_sql_query("SELECT * FROM repairs", conn)
        df_staff = pd.read_sql_query("SELECT * FROM staff", conn)
        conn.close()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = os.path.join(BACKUP_FOLDER, f"export_{timestamp}.xlsx")
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df_repairs.to_excel(writer, sheet_name='المعاينات', index=False)
            df_staff.to_excel(writer, sheet_name='الفنيين', index=False)
        
        return excel_path
    except Exception as e:
        st.error(f"خطأ في تصدير البيانات: {e}")
        return None

def display_pdf_pdfjs(file_name):
    try:
        if not file_name:
            return
        
        file_path = os.path.join(UPLOAD_FOLDER, file_name)
        if not os.path.exists(file_path):
            st.error(f"⚠️ الملف غير موجود: {file_name}")
            return
        
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
        
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        
        pdf_viewer = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .controls {{
                    margin: 10px 0;
                    text-align: center;
                }}
                button {{
                    background-color: #ff4b4b;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    margin: 0 5px;
                    border-radius: 5px;
                    cursor: pointer;
                }}
                button:hover {{
                    background-color: #ff6b6b;
                }}
            </style>
        </head>
        <body>
            <div class="controls">
                <button onclick="prevPage()">⬅️ السابق</button>
                <span>الصفحة <span id="page_num"></span> / <span id="page_count"></span></span>
                <button onclick="nextPage()">التالي ➡️</button>
            </div>
            <canvas id="pdf-canvas" style="width:100%; border:1px solid #ddd;"></canvas>
            
            <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js"></script>
            <script>
                pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
                
                let pdfDoc = null;
                let pageNum = 1;
                let pageRendering = false;
                let pageNumPending = null;
                let scale = 1.2;
                let canvas = document.getElementById('pdf-canvas');
                let ctx = canvas.getContext('2d');
                
                function renderPage(num) {{
                    pageRendering = true;
                    pdfDoc.getPage(num).then(function(page) {{
                        let viewport = page.getViewport({{scale: scale}});
                        canvas.height = viewport.height;
                        canvas.width = viewport.width;
                        
                        let renderContext = {{
                            canvasContext: ctx,
                            viewport: viewport
                        }};
                        let renderTask = page.render(renderContext);
                        
                        renderTask.promise.then(function() {{
                            pageRendering = false;
                            if (pageNumPending !== null) {{
                                renderPage(pageNumPending);
                                pageNumPending = null;
                            }}
                        }});
                    }});
                    
                    document.getElementById('page_num').textContent = num;
                }}
                
                function queueRenderPage(num) {{
                    if (pageRendering) {{
                        pageNumPending = num;
                    }} else {{
                        renderPage(num);
                    }}
                }}
                
                function prevPage() {{
                    if (pageNum <= 1) return;
                    pageNum--;
                    queueRenderPage(pageNum);
                }}
                
                function nextPage() {{
                    if (pageNum >= pdfDoc.numPages) return;
                    pageNum++;
                    queueRenderPage(pageNum);
                }}
                
                let pdfData = atob('{base64_pdf}');
                let loadingTask = pdfjsLib.getDocument({{data: pdfData}});
                loadingTask.promise.then(function(pdf) {{
                    pdfDoc = pdf;
                    document.getElementById('page_count').textContent = pdfDoc.numPages;
                    renderPage(pageNum);
                }});
            </script>
        </body>
        </html>
        '''
        
        st.components.v1.html(pdf_viewer, height=700, scrolling=True)
        
        st.download_button(
            label="📥 تحميل PDF",
            data=pdf_bytes,
            file_name=file_name,
            mime="application/pdf",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"خطأ في عرض الملف: {e}")

def get_dashboard_stats():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM repairs", conn)
    conn.close()
    
    today = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%Y-%m")
    
    total = len(df)
    today_count = len(df[df['visit_date'] == today]) if not df.empty else 0
    month_count = len(df[df['visit_date'].str.startswith(current_month)]) if not df.empty else 0
    
    total_revenue = df['cost'].astype(float).sum() if not df.empty and 'cost' in df.columns else 0
    
    # أكثر فني شغلاً
    if not df.empty and 'tech_name' in df.columns:
        tech_counts = df[df['tech_name'] != '']['tech_name'].value_counts().head(5)
        top_tech = tech_counts.to_dict()
    else:
        top_tech = {}
    
    # أكثر محافظة
    if not df.empty and 'governorate' in df.columns:
        gov_counts = df[df['governorate'] != '']['governorate'].value_counts().head(5)
        top_gov = gov_counts.to_dict()
    else:
        top_gov = {}
    
    return {
        'total': total,
        'today': today_count,
        'month': month_count,
        'revenue': total_revenue,
        'top_tech': top_tech,
        'top_gov': top_gov
    }

def show_dashboard():
    stats = get_dashboard_stats()
    
    st.markdown("## 📊 لوحة التحكم والإحصائيات")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📋 إجمالي المعاينات</h3>
            <h1 style="color: #ff4b4b;">{stats['total']}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📅 معاينات اليوم</h3>
            <h1 style="color: #ff4b4b;">{stats['today']}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📆 معاينات هذا الشهر</h3>
            <h1 style="color: #ff4b4b;">{stats['month']}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>💰 إجمالي الإيرادات</h3>
            <h1 style="color: #00ff00;">{stats['revenue']:,.0f} ج.م</h1>
        </div>
        """, unsafe_allow_html=True)
    
    # رسم بياني للمعاينات اليومية
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT visit_date, cost FROM repairs", conn)
    conn.close()
    
    if not df.empty:
        df['visit_date'] = pd.to_datetime(df['visit_date'])
        daily_counts = df.groupby(df['visit_date'].dt.date).size().reset_index(name='count')
        daily_counts.columns = ['التاريخ', 'عدد المعاينات']
        
        fig = px.bar(daily_counts, x='التاريخ', y='عدد المعاينات', title='المعاينات اليومية', color_discrete_sequence=['#ff4b4b'])
        fig.update_layout(plot_bgcolor='#1a1c23', paper_bgcolor='#1a1c23', font_color='white')
        st.plotly_chart(fig, use_container_width=True)
    
    col5, col6 = st.columns(2)
    
    with col5:
        st.markdown("### 👨‍🔧 أكثر الفنيين شغلاً")
        if stats['top_tech']:
            for name, count in list(stats['top_tech'].items())[:5]:
                st.progress(min(count / max(stats['top_tech'].values()) if stats['top_tech'].values() else 1, 1.0))
                st.write(f"**{name}**: {count} معاينة")
        else:
            st.info("لا توجد بيانات كافية")
    
    with col6:
        st.markdown("### 📍 أكثر المحافظات")
        if stats['top_gov']:
            for name, count in list(stats['top_gov'].items())[:5]:
                st.progress(min(count / max(stats['top_gov'].values()) if stats['top_gov'].values() else 1, 1.0))
                st.write(f"**{name}**: {count} معاينة")
        else:
            st.info("لا توجد بيانات كافية")

ALL_GOVS = ["القاهرة", "الجيزة", "الإسكندرية", "الدقهلية", "البحيرة", "القليوبية", "الغربية", "المنوفية", "الشرقية", "دمياط", "بورسعيد", "السويس", "الإسماعيلية", "كفر الشيخ", "الفيوم", "بني سويف", "المنيا", "أسيوط", "سوهاج", "قنا", "الأقصر", "أسوان"]

def validate_phone(phone):
    """التحقق من رقم التليفون (11 رقم مصري)"""
    if not phone or phone == "":
        return True, ""
    phone_str = str(phone).strip()
    phone_digits = ''.join(filter(str.isdigit, phone_str))
    if len(phone_digits) != 11:
        return False, "رقم التليفون يجب أن يكون 11 رقم"
    if not phone_digits.startswith('01'):
        return False, "رقم التليفون يجب أن يبدأ بـ 01"
    return True, ""

if not check_password():
    st.stop()

# عرض معلومات المستخدم في الشريط الجانبي
with st.sidebar:
    st.markdown(f"### 👤 مرحباً {st.session_state.username}")
    if st.button("🚪 تسجيل خروج", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# تبويب إضافي للوحة التحكم
tab0, tab1, tab2, tab3, tab4 = st.tabs(["📊 لوحة التحكم", "➕ تسجيل معاينة جديدة", "📊 سجل المعاينات والإدارة", "👥 إدارة الفنيين", "💾 النسخ الاحتياطي"])

with tab0:
    show_dashboard()

with tab4:
    st.subheader("💾 نظام النسخ الاحتياطي والاستعادة")
    st.warning("⚠️ هذه الإعدادات متاحة للمدير فقط")
    
    auto_backups = sorted([f for f in os.listdir(AUTO_BACKUP_FOLDER) if f.endswith('.db')], reverse=True)
    if auto_backups:
        st.info(f"📁 يوجد {len(auto_backups)} نسخة احتياطية تلقائية")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📤 إنشاء نسخة احتياطية يدوية")
        if st.button("🔄 إنشاء نسخة احتياطية جديدة", type="primary", use_container_width=True):
            with st.spinner("جاري إنشاء النسخة الاحتياطية..."):
                zip_path, info = create_backup()
                if zip_path and info:
                    st.success("✅ تم إنشاء النسخة الاحتياطية بنجاح!")
                    st.json(info)
                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label="📥 تحميل النسخة الاحتياطية",
                            data=f.read(),
                            file_name=os.path.basename(zip_path),
                            mime="application/zip",
                            use_container_width=True
                        )
    
    with col2:
        st.markdown("### 📥 استعادة نسخة احتياطية")
        st.warning("⚠️ تحذير: استعادة النسخة ستحل محل البيانات الحالية!")
        uploaded_backup = st.file_uploader("اختر ملف النسخة الاحتياطية (.zip)", type=['zip'])
        if uploaded_backup:
            if st.button("⚠️ استعادة البيانات", type="secondary", use_container_width=True):
                with st.spinner("جاري استعادة البيانات..."):
                    temp_zip = os.path.join(BACKUP_FOLDER, "temp_restore.zip")
                    with open(temp_zip, "wb") as f:
                        f.write(uploaded_backup.getbuffer())
                    
                    info = restore_backup(temp_zip)
                    if info:
                        st.success("✅ تم استعادة البيانات بنجاح!")
                        st.json(info)
                        st.warning("⚠️ يرجى تحديث الصفحة (F5) لرؤية التغييرات")
                    
                    if os.path.exists(temp_zip):
                        os.remove(temp_zip)
    
    st.divider()
    
    st.markdown("### 📊 تصدير البيانات")
    if st.button("📎 تصدير إلى Excel", use_container_width=True):
        with st.spinner("جاري تصدير البيانات..."):
            excel_path = export_data_to_excel()
            if excel_path:
                with open(excel_path, "rb") as f:
                    st.download_button(
                        label="📥 تحميل ملف Excel",
                        data=f.read(),
                        file_name=os.path.basename(excel_path),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

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

with tab1:
    st.subheader("📝 إضافة بيانات العميل")
    
    if 'form_counter' not in st.session_state:
        st.session_state.form_counter = 0
    
    def get_form_key():
        return f"form_{st.session_state.form_counter}"
    
    with st.form(key=get_form_key()):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("اسم العميل")
            phone = st.text_input("رقم التليفون الأول", max_chars=11, help="11 رقم يبدأ بـ 01")
            phone2 = st.text_input("رقم التليفون الثاني (اختياري)", max_chars=11, help="11 رقم يبدأ بـ 01")
            cost = st.text_input("التكلفة (EGP)")
        with c2:
            gov = st.selectbox("المحافظة", ALL_GOVS)
            addr = st.text_input("العنوان بالتفصيل")
            date_v = st.date_input("التاريخ", datetime.now())
       
        rep = st.text_area("وصف العطل")
        file = st.file_uploader("ارفع التقرير (PDF)", type=['pdf'])
       
        if st.form_submit_button("حفظ البيانات النهائية"):
            # التحقق من الأرقام
            valid1, msg1 = validate_phone(phone)
            valid2, msg2 = validate_phone(phone2) if phone2 else (True, "")
            
            if not valid1:
                st.error(msg1)
            elif not valid2:
                st.error(msg2)
            else:
                file_name = ""
                if file:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_name = f"{name}_{timestamp}_{file.name}"
                    file_path = os.path.join(UPLOAD_FOLDER, file_name)
                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer())
                
                conn = get_db_connection()
                conn.cursor().execute("INSERT INTO repairs (client_name, phone, phone2, visit_date, governorate, address, report, file_name, cost, tech_name, assistant_name, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                     (name, phone, phone2, str(date_v), gov, addr, rep, file_name, cost, "", "", ""))
                conn.commit()
                conn.close()
                st.success("✅ تم الحفظ بنجاح!")
                
                auto_backup()
                
                st.session_state.form_counter += 1
                st.rerun()

with tab2:
    st.subheader("📊 سجل المعاينات")
    conn = get_db_connection()
    
    try:
        df_raw = pd.read_sql_query("SELECT id, client_name as 'العميل', phone as 'التليفون', phone2 as 'تليفون 2', tech_name as 'الفني', cost as 'التكلفة', visit_date as 'التاريخ', governorate as 'المحافظة', address as 'العنوان', file_name FROM repairs ORDER BY visit_date DESC, id DESC", conn)
    except:
        df_raw = pd.read_sql_query("SELECT id, client_name as 'العميل', phone as 'التليفون', tech_name as 'الفني', cost as 'التكلفة', visit_date as 'التاريخ', governorate as 'المحافظة', address as 'العنوان', file_name FROM repairs ORDER BY visit_date DESC, id DESC", conn)
        df_raw['تليفون 2'] = ""
    
    conn.close()
    
    if not df_raw.empty:
        # بحث متقدم
        st.markdown("### 🔍 بحث متقدم")
        search_col1, search_col2, search_col3 = st.columns(3)
        
        with search_col1:
            search_query = st.text_input("🔍 بحث بالاسم أو التليفون", placeholder="اكتب للبحث...")
        with search_col2:
            start_date = st.date_input("من تاريخ", value=None)
        with search_col3:
            end_date = st.date_input("إلى تاريخ", value=None)
        
        df = df_raw.copy()
        
        if search_query:
            df = df[df['العميل'].str.contains(search_query, na=False, case=False) |
                    df['التليفون'].str.contains(search_query, na=False) |
                    df['الفني'].str.contains(search_query, na=False, case=False)]
        
        if start_date:
            df = df[pd.to_datetime(df['التاريخ']) >= pd.to_datetime(start_date)]
        if end_date:
            df = df[pd.to_datetime(df['التاريخ']) <= pd.to_datetime(end_date)]
        
        st.write(f"🔎 تم العثور على {len(df)} سجل")
        
        def make_wa_link(phone_num):
            if not phone_num or phone_num == "" or pd.isna(phone_num):
                return "#"
            p = str(phone_num).strip()
            p = ''.join(filter(str.isdigit, p))
            if p:
                num = p if p.startswith('2') else '2' + p
                return f"https://wa.me/{num}"
            return "#"
       
        df['واتساب'] = df['التليفون'].apply(make_wa_link)
        
        if not df.empty:
            df['التاريخ'] = pd.to_datetime(df['التاريخ'])
            unique_dates = df['التاريخ'].dt.date.unique()
            
            for date in unique_dates:
                st.markdown(f"### 📅 {date.strftime('%Y-%m-%d')}")
                df_day = df[df['التاريخ'].dt.date == date]
                
                display_cols = ['العميل', 'التليفون', 'تليفون 2', 'الفني', 'التكلفة', 'المحافظة', 'العنوان', 'واتساب']
                cols_to_show = [col for col in display_cols if col in df_day.columns]
                
                event = st.dataframe(
                    df_day[cols_to_show],
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
                    selected_id = int(df_day.iloc[selected_index]['id'])
                    
                    st.divider()
                    st.subheader(f"🛠️ إجراءات التعديل: {df_day.iloc[selected_index]['العميل']}")
                    
                    conn = get_db_connection()
                    row = conn.execute("SELECT * FROM repairs WHERE id=?", (selected_id,)).fetchone()
                    conn.close()
                    
                    if row['file_name']:
                        st.info(f"📎 الملف المرفق: {row['file_name']}")
                        display_pdf_pdfjs(row['file_name'])
                        st.markdown("---")
                    else:
                        st.info("📭 لا يوجد ملف مرفق")
                        st.markdown("---")
                    
                    with st.form(f"edit_form_{selected_id}"):
                        col_l, col_r = st.columns(2)
                        with col_l:
                            u_name = st.text_input("اسم العميل", row['client_name'])
                            u_phone = st.text_input("التليفون الأول", row['phone'], max_chars=11, help="11 رقم يبدأ بـ 01")
                            u_phone2 = st.text_input("التليفون الثاني", row['phone2'] if row['phone2'] else "", max_chars=11, help="11 رقم يبدأ بـ 01")
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
                            # التحقق من الأرقام
                            valid1, msg1 = validate_phone(u_phone)
                            valid2, msg2 = validate_phone(u_phone2) if u_phone2 else (True, "")
                            
                            if not valid1:
                                st.error(msg1)
                            elif not valid2:
                                st.error(msg2)
                            else:
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
                                conn.cursor().execute("UPDATE repairs SET client_name=?, phone=?, phone2=?, tech_name=?, assistant_name=?, cost=?, governorate=?, address=?, notes=?, visit_date=?, file_name=? WHERE id=?",
                                                    (u_name, u_phone, u_phone2, u_tech, u_assist, u_cost, u_gov, u_addr, u_notes, str(u_date), file_name, selected_id))
                                conn.commit()
                                conn.close()
                                st.success("✅ تم التحديث بنجاح!")
                                st.rerun()
                       
                        if b_del.form_submit_button("🗑️ مسح المعاينة"):
                            st.warning("⚠️ هذا الإجراء لا يمكن التراجع عنه!")
                            if st.button("تأكيد المسح"):
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
                                st.success("🗑️ تم المسح بنجاح!")
                                st.rerun()
                    
                    st.markdown("---")
    else:
        st.info("لا توجد سجلات حالياً.")
