import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta
import base64
import shutil
import json
import zipfile
import hashlib
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
import io
from PIL import Image as PILImage
import qrcode
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests

# ==================== إعدادات الصفحة ====================
st.set_page_config(page_title="Expert 2M - Management System", layout="wide")

# ==================== إعدادات المصادقة ====================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()

# قائمة المستخدمين (يمكن تخزينها في قاعدة بيانات لاحقاً)
USERS = {
    "admin": {"password": ADMIN_PASSWORD_HASH, "role": "admin", "name": "المدير"},
    "supervisor": {"password": hashlib.sha256("super123".encode()).hexdigest(), "role": "supervisor", "name": "مشرف"},
    "tech1": {"password": hashlib.sha256("tech123".encode()).hexdigest(), "role": "tech", "name": "فني 1", "tech_name": "محمد احمد"},
    "tech2": {"password": hashlib.sha256("tech123".encode()).hexdigest(), "role": "tech", "name": "فني 2", "tech_name": "احمد محمد"},
}

def check_password():
    """التحقق من تسجيل الدخول"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.username = None
        st.session_state.user_name = None
    
    if not st.session_state.authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🔐 نظام إدارة الصيانة - Expert 2M")
            st.markdown("---")
            username = st.text_input("اسم المستخدم")
            password = st.text_input("كلمة المرور", type="password")
            
            if st.button("دخول", use_container_width=True):
                if username in USERS and hashlib.sha256(password.encode()).hexdigest() == USERS[username]["password"]:
                    st.session_state.authenticated = True
                    st.session_state.user_role = USERS[username]["role"]
                    st.session_state.username = username
                    st.session_state.user_name = USERS[username]["name"]
                    if "tech_name" in USERS[username]:
                        st.session_state.tech_name = USERS[username]["tech_name"]
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")
        return False
    return True

# ==================== ستايل الصفحة ====================
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    [data-testid="stForm"] { border: 1px solid #444; border-radius: 15px; background-color: #1a1c23; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #1a1c23; border-radius: 10px 10px 0 0; }
    .metric-card { background-color: #1a1c23; border-radius: 10px; padding: 15px; text-align: center; border: 1px solid #333; }
    .metric-card h3 { margin: 0; font-size: 14px; color: #888; }
    .metric-card h1 { margin: 10px 0 0 0; font-size: 32px; }
    .inventory-card { background-color: #1a1c23; border-radius: 10px; padding: 15px; margin: 10px 0; }
    .low-stock { border-right: 3px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# ==================== إعدادات المجلدات ====================
UPLOAD_FOLDER = "uploaded_reports"
BACKUP_FOLDER = "backups"
AUTO_BACKUP_FOLDER = "auto_backups"
INVOICES_FOLDER = "invoices"
CUSTOMERS_FOLDER = "customers_data"

for folder in [UPLOAD_FOLDER, BACKUP_FOLDER, AUTO_BACKUP_FOLDER, INVOICES_FOLDER, CUSTOMERS_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# ==================== دوال قاعدة البيانات ====================
def get_db_connection():
    conn = sqlite3.connect('expert2m_v6.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جدول المعاينات
    cursor.execute('''CREATE TABLE IF NOT EXISTS repairs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  client_name TEXT, phone TEXT, phone2 TEXT,
                  tech_name TEXT, assistant_name TEXT, visit_date TEXT,
                  governorate TEXT, address TEXT, report TEXT,
                  notes TEXT, file_name TEXT, cost TEXT, 
                  invoice_sent INTEGER DEFAULT 0, whatsapp_sent INTEGER DEFAULT 0)''')
    
    # جدول الفنيين
    cursor.execute('''CREATE TABLE IF NOT EXISTS staff
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    
    # جدول العملاء
    cursor.execute('''CREATE TABLE IF NOT EXISTS customers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, phone TEXT, phone2 TEXT, 
                  address TEXT, governorate TEXT, 
                  created_date TEXT, total_visits INTEGER DEFAULT 0, 
                  total_cost REAL DEFAULT 0)''')
    
    # جدول قطع الغيار (المخزون)
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  part_name TEXT, part_code TEXT UNIQUE,
                  quantity INTEGER DEFAULT 0, min_quantity INTEGER DEFAULT 5,
                  price REAL DEFAULT 0, unit TEXT DEFAULT 'قطعة',
                  supplier TEXT, last_updated TEXT)''')
    
    # جدول استخدام قطع الغيار
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory_usage
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  repair_id INTEGER, part_id INTEGER, quantity INTEGER,
                  usage_date TEXT, notes TEXT,
                  FOREIGN KEY (repair_id) REFERENCES repairs(id),
                  FOREIGN KEY (part_id) REFERENCES inventory(id))''')
    
    # جدول الإشعارات
    cursor.execute('''CREATE TABLE IF NOT EXISTS notifications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT, message TEXT, type TEXT,
                  created_date TEXT, is_read INTEGER DEFAULT 0)''')
    
    # إضافة الأعمدة الجديدة إذا لم تكن موجودة
    try:
        cursor.execute("ALTER TABLE repairs ADD COLUMN phone2 TEXT")
    except: pass
    try:
        cursor.execute("ALTER TABLE repairs ADD COLUMN invoice_sent INTEGER DEFAULT 0")
    except: pass
    try:
        cursor.execute("ALTER TABLE repairs ADD COLUMN whatsapp_sent INTEGER DEFAULT 0")
    except: pass
    
    # إضافة الفنيين الافتراضيين
    default_staff = ["محمد احمد", "احمد محمد", "محمود علي", "سيد مصطفى", "خالد حسن"]
    for staff in default_staff:
        try:
            cursor.execute("INSERT INTO staff (name) VALUES (?)", (staff,))
        except: pass
    
    # إضافة قطع غيار افتراضية
    default_parts = [
        ("محرك كهربائي", "MTR-001", 10, 3, 450, "قطعة", "الشركة العربية"),
        ("طلمبة مياه", "PMP-001", 8, 2, 320, "قطعة", "شركة النيل"),
        ("كيبورد", "KBD-001", 15, 5, 150, "قطعة", "سامسونج"),
        ("شاشة", "SCR-001", 5, 2, 850, "قطعة", "ال جي"),
        ("باور سبلاي", "PSU-001", 7, 3, 280, "قطعة", "دلتا"),
        ("مكثف", "CAP-001", 50, 10, 25, "قطعة", "المتحدة"),
        ("ريموت كنترول", "RMT-001", 20, 5, 45, "قطعة", "يونيفرسال"),
    ]
    for part in default_parts:
        try:
            cursor.execute("INSERT INTO inventory (part_name, part_code, quantity, min_quantity, price, unit, supplier) VALUES (?,?,?,?,?,?,?)", part)
        except: pass
    
    conn.commit()
    conn.close()
init_db()

# ==================== دوال النسخ الاحتياطي ====================
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
        df_customers = pd.read_sql_query("SELECT * FROM customers", conn)
        df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
        conn.close()
        
        df_repairs.to_json(os.path.join(backup_path, 'repairs.json'), orient='records', force_ascii=False)
        df_staff.to_json(os.path.join(backup_path, 'staff.json'), orient='records', force_ascii=False)
        df_customers.to_json(os.path.join(backup_path, 'customers.json'), orient='records', force_ascii=False)
        df_inventory.to_json(os.path.join(backup_path, 'inventory.json'), orient='records', force_ascii=False)
        
        info = {
            'backup_date': timestamp,
            'backup_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'repairs_count': len(df_repairs),
            'staff_count': len(df_staff),
            'customers_count': len(df_customers),
            'inventory_count': len(df_inventory),
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
        df_customers = pd.read_sql_query("SELECT * FROM customers", conn)
        df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
        conn.close()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = os.path.join(BACKUP_FOLDER, f"export_{timestamp}.xlsx")
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df_repairs.to_excel(writer, sheet_name='المعاينات', index=False)
            df_staff.to_excel(writer, sheet_name='الفنيين', index=False)
            df_customers.to_excel(writer, sheet_name='العملاء', index=False)
            df_inventory.to_excel(writer, sheet_name='المخزون', index=False)
        
        return excel_path
    except Exception as e:
        st.error(f"خطأ في تصدير البيانات: {e}")
        return None

# ==================== دوال العملاء ====================
def add_or_update_customer(name, phone, phone2, address, governorate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # البحث عن عميل موجود
    existing = cursor.execute("SELECT id FROM customers WHERE phone = ?", (phone,)).fetchone()
    
    if existing:
        # تحديث بيانات العميل
        cursor.execute("UPDATE customers SET name=?, phone2=?, address=?, governorate=?, total_visits=total_visits+1 WHERE id=?", 
                      (name, phone2, address, governorate, existing['id']))
    else:
        # إضافة عميل جديد
        cursor.execute("INSERT INTO customers (name, phone, phone2, address, governorate, created_date, total_visits, total_cost) VALUES (?,?,?,?,?,?,?,?)",
                      (name, phone, phone2, address, governorate, datetime.now().strftime("%Y-%m-%d"), 1, 0))
    
    conn.commit()
    conn.close()

def update_customer_cost(phone, cost):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE customers SET total_cost = total_cost + ? WHERE phone = ?", (float(cost) if cost else 0, phone))
    conn.commit()
    conn.close()

def get_customer_history(phone):
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM repairs WHERE phone = ? ORDER BY visit_date DESC", conn, params=(phone,))
    conn.close()
    return df

# ==================== دوال المخزون ====================
def add_inventory_item(part_name, part_code, quantity, min_quantity, price, unit, supplier):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO inventory (part_name, part_code, quantity, min_quantity, price, unit, supplier, last_updated) VALUES (?,?,?,?,?,?,?,?)",
                      (part_name, part_code, quantity, min_quantity, price, unit, supplier, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True, "تم إضافة القطعة بنجاح"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "الكود موجود بالفعل"

def update_inventory_quantity(part_id, quantity_change):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE inventory SET quantity = quantity + ?, last_updated = ? WHERE id = ?", 
                  (quantity_change, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), part_id))
    conn.commit()
    
    # التحقق من المخزون المنخفض
    part = cursor.execute("SELECT part_name, quantity, min_quantity FROM inventory WHERE id = ?", (part_id,)).fetchone()
    if part and part['quantity'] <= part['min_quantity']:
        add_notification(f"تنبيه: مخزون منخفض - {part['part_name']}", 
                        f"الكمية المتبقية: {part['quantity']} (الحد الأدنى: {part['min_quantity']})", "warning")
    
    conn.close()

def use_inventory_part(repair_id, part_code, quantity, notes=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    part = cursor.execute("SELECT id, quantity, price FROM inventory WHERE part_code = ?", (part_code,)).fetchone()
    
    if not part:
        conn.close()
        return False, "القطعة غير موجودة"
    
    if part['quantity'] < quantity:
        conn.close()
        return False, f"الكمية غير متوفرة. المتوفر: {part['quantity']}"
    
    # تسجيل الاستخدام
    cursor.execute("INSERT INTO inventory_usage (repair_id, part_id, quantity, usage_date, notes) VALUES (?,?,?,?,?)",
                  (repair_id, part['id'], quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), notes))
    
    # تحديث الكمية
    cursor.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ?", (quantity, part['id']))
    conn.commit()
    conn.close()
    return True, "تم تسجيل الاستخدام بنجاح"

def get_low_stock_items():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM inventory WHERE quantity <= min_quantity", conn)
    conn.close()
    return df

# ==================== دوال الإشعارات ====================
def add_notification(title, message, type="info"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notifications (title, message, type, created_date, is_read) VALUES (?,?,?,?,?)",
                  (title, message, type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0))
    conn.commit()
    conn.close()

def get_unread_notifications():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM notifications WHERE is_read = 0 ORDER BY created_date DESC", conn)
    conn.close()
    return df

def mark_notification_read(notif_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notif_id,))
    conn.commit()
    conn.close()

# ==================== دوال الفواتير ====================
def generate_invoice_pdf(repair_data):
    """إنشاء فاتورة PDF للمعاينة"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    
    # ستايل مخصص للعربية
    arabic_style = ParagraphStyle(
        'ArabicStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        alignment=1,  # مركز
        spaceAfter=10,
    )
    
    story = []
    
    # العنوان
    title = Paragraph("Expert 2M - فاتورة معاينة", arabic_style)
    story.append(title)
    story.append(Spacer(1, 20))
    
    # بيانات الفاتورة
    data = [
        ["اسم العميل:", repair_data['client_name']],
        ["رقم التليفون:", repair_data['phone']],
        ["التاريخ:", repair_data['visit_date']],
        ["المحافظة:", repair_data['governorate']],
        ["العنوان:", repair_data['address']],
        ["وصف العطل:", repair_data['report']],
        ["التكلفة:", f"{repair_data['cost']} ج.م" if repair_data['cost'] else "لم تحدد"],
        ["الفني:", repair_data['tech_name'] if repair_data['tech_name'] else "لم يحدد"],
    ]
    
    table = Table(data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(table)
    
    # تذييل
    story.append(Spacer(1, 30))
    footer = Paragraph("شكراً لثقتكم في Expert 2M", arabic_style)
    story.append(footer)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def send_whatsapp_message(phone, message):
    """إرسال رسالة واتساب (يتطلب Twilio API أو WhatsApp Business API)"""
    # هذه دالة أساسية - للتشغيل الفعلي تحتاج API من Twilio
    # للتوضيح فقط - نعيد True كتجربة
    try:
        # إعداد رابط واتساب
        whatsapp_link = f"https://wa.me/2{phone}?text={message.replace(' ', '%20')}"
        return True, whatsapp_link
    except Exception as e:
        return False, str(e)

# ==================== دالة عرض PDF ====================
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
                .controls {{ margin: 10px 0; text-align: center; }}
                button {{ background-color: #ff4b4b; color: white; border: none; padding: 8px 16px; margin: 0 5px; border-radius: 5px; cursor: pointer; }}
                button:hover {{ background-color: #ff6b6b; }}
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
                
                let pdfDoc = null, pageNum = 1, pageRendering = false, pageNumPending = null, scale = 1.2;
                let canvas = document.getElementById('pdf-canvas');
                let ctx = canvas.getContext('2d');
                
                function renderPage(num) {{
                    pageRendering = true;
                    pdfDoc.getPage(num).then(function(page) {{
                        let viewport = page.getViewport({{scale: scale}});
                        canvas.height = viewport.height;
                        canvas.width = viewport.width;
                        let renderContext = {{ canvasContext: ctx, viewport: viewport }};
                        let renderTask = page.render(renderContext);
                        renderTask.promise.then(function() {{
                            pageRendering = false;
                            if (pageNumPending !== null) {{ renderPage(pageNumPending); pageNumPending = null; }}
                        }});
                    }});
                    document.getElementById('page_num').textContent = num;
                }}
                
                function queueRenderPage(num) {{
                    if (pageRendering) pageNumPending = num;
                    else renderPage(num);
                }}
                
                function prevPage() {{ if (pageNum <= 1) return; pageNum--; queueRenderPage(pageNum); }}
                function nextPage() {{ if (pageNum >= pdfDoc.numPages) return; pageNum++; queueRenderPage(pageNum); }}
                
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
        st.download_button(label="📥 تحميل PDF", data=pdf_bytes, file_name=file_name, mime="application/pdf", use_container_width=True)
        
    except Exception as e:
        st.error(f"خطأ في عرض الملف: {e}")

# ==================== دوال الإحصائيات ====================
def get_dashboard_stats():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM repairs", conn)
    df_customers = pd.read_sql_query("SELECT * FROM customers", conn)
    df_inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    
    today = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%Y-%m")
    
    total = len(df)
    today_count = len(df[df['visit_date'] == today]) if not df.empty else 0
    month_count = len(df[df['visit_date'].str.startswith(current_month)]) if not df.empty else 0
    total_revenue = df['cost'].astype(float).sum() if not df.empty and 'cost' in df.columns else 0
    customers_count = len(df_customers)
    low_stock = len(df_inventory[df_inventory['quantity'] <= df_inventory['min_quantity']]) if not df_inventory.empty else 0
    
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
        'total': total, 'today': today_count, 'month': month_count,
        'revenue': total_revenue, 'customers': customers_count,
        'low_stock': low_stock, 'top_tech': top_tech, 'top_gov': top_gov
    }

def show_dashboard():
    stats = get_dashboard_stats()
    
    st.markdown("## 📊 لوحة التحكم والإحصائيات")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📋 المعاينات</h3>
            <h1 style="color: #ff4b4b;">{stats['total']}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📅 اليوم</h3>
            <h1 style="color: #ff4b4b;">{stats['today']}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📆 هذا الشهر</h3>
            <h1 style="color: #ff4b4b;">{stats['month']}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>💰 الإيرادات</h3>
            <h1 style="color: #00ff00;">{stats['revenue']:,.0f} ج.م</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <h3>👥 العملاء</h3>
            <h1 style="color: #ffa500;">{stats['customers']}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        st.markdown(f"""
        <div class="metric-card">
            <h3>⚠️ مخزون منخفض</h3>
            <h1 style="color: #ff4b4b;">{stats['low_stock']}</h1>
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
    
    col7, col8 = st.columns(2)
    
    with col7:
        st.markdown("### 👨‍🔧 أكثر الفنيين شغلاً")
        if stats['top_tech']:
            for name, count in list(stats['top_tech'].items())[:5]:
                st.progress(min(count / max(stats['top_tech'].values()), 1.0))
                st.write(f"**{name}**: {count} معاينة")
        else:
            st.info("لا توجد بيانات كافية")
    
    with col8:
        st.markdown("### 📍 أكثر المحافظات")
        if stats['top_gov']:
            for name, count in list(stats['top_gov'].items())[:5]:
                st.progress(min(count / max(stats['top_gov'].values()), 1.0))
                st.write(f"**{name}**: {count} معاينة")
        else:
            st.info("لا توجد بيانات كافية")
    
    # إشعارات المخزون المنخفض
    low_stock_items = get_low_stock_items()
    if not low_stock_items.empty:
        st.markdown("### ⚠️ تنبيهات المخزون")
        for _, item in low_stock_items.iterrows():
            st.warning(f"**{item['part_name']}** - الكود: {item['part_code']} - المتبقي: {item['quantity']} (الحد الأدنى: {item['min_quantity']})")

# ==================== دالة التحقق من رقم التليفون ====================
def validate_phone(phone):
    if not phone or phone == "":
        return True, ""
    phone_str = str(phone).strip()
    phone_digits = ''.join(filter(str.isdigit, phone_str))
    if len(phone_digits) != 11:
        return False, "رقم التليفون يجب أن يكون 11 رقم"
    if not phone_digits.startswith('01'):
        return False, "رقم التليفون يجب أن يبدأ بـ 01"
    return True, ""

# ==================== قائمة المحافظات ====================
ALL_GOVS = ["القاهرة", "الجيزة", "الإسكندرية", "الدقهلية", "البحيرة", "القليوبية", "الغربية", "المنوفية", "الشرقية", "دمياط", "بورسعيد", "السويس", "الإسماعيلية", "كفر الشيخ", "الفيوم", "بني سويف", "المنيا", "أسيوط", "سوهاج", "قنا", "الأقصر", "أسوان"]

# ==================== التحقق من تسجيل الدخول ====================
if not check_password():
    st.stop()

# ==================== الشريط الجانبي ====================
with st.sidebar:
    st.markdown(f"### 👤 مرحباً {st.session_state.user_name}")
    st.markdown(f"**الدور:** {st.session_state.user_role}")
    
    # عرض الإشعارات
    unread_notifs = get_unread_notifications()
    if not unread_notifs.empty:
        with st.expander(f"🔔 إشعارات جديدة ({len(unread_notifs)})"):
            for _, notif in unread_notifs.iterrows():
                st.info(f"**{notif['title']}**\n\n{notif['message']}")
                if st.button("تحديد كمقروء", key=f"read_{notif['id']}"):
                    mark_notification_read(notif['id'])
                    st.rerun()
    
    if st.button("🚪 تسجيل خروج", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ==================== التبويبات ====================
tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 لوحة التحكم", "➕ تسجيل معاينة جديدة", "📊 سجل المعاينات", 
    "👥 إدارة الفنيين", "📦 إدارة المخزون", "👤 إدارة العملاء", "💾 النسخ الاحتياطي"
])

# ==================== تبويب لوحة التحكم ====================
with tab0:
    show_dashboard()

# ==================== تبويب النسخ الاحتياطي (للمدير فقط) ====================
with tab6:
    if st.session_state.user_role == "admin":
        st.subheader("💾 نظام النسخ الاحتياطي والاستعادة")
        
        auto_backups_list = sorted([f for f in os.listdir(AUTO_BACKUP_FOLDER) if f.endswith('.db')], reverse=True)
        if auto_backups_list:
            st.info(f"📁 يوجد {len(auto_backups_list)} نسخة احتياطية تلقائية")
        
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
                            st.download_button(label="📥 تحميل النسخة الاحتياطية", data=f.read(), file_name=os.path.basename(zip_path), mime="application/zip", use_container_width=True)
        
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
                        st.download_button(label="📥 تحميل ملف Excel", data=f.read(), file_name=os.path.basename(excel_path), mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    else:
        st.error("⛔ هذه الصفحة متاحة للمدير فقط")

# ==================== تبويب إدارة الفنيين ====================
with tab3:
    if st.session_state.user_role in ["admin", "supervisor"]:
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
    else:
        st.error("⛔ هذه الصفحة متاحة للمدير والمشرف فقط")

# جلب أسماء الفنيين
conn = get_db_connection()
staff_list = pd.read_sql_query("SELECT * FROM staff", conn)
conn.close()
staff_names = ["لم يتم التحديد"] + [row['name'] for _, row in staff_list.iterrows()] if not staff_list.empty else ["لم يتم التحديد"]

# ==================== تبويب تسجيل معاينة جديدة ====================
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
        
        # استخدام قطع الغيار
        with st.expander("🔧 استخدام قطع غيار (اختياري)"):
            conn = get_db_connection()
            parts_df = pd.read_sql_query("SELECT id, part_name, part_code, quantity, price FROM inventory WHERE quantity > 0", conn)
            conn.close()
            
            if not parts_df.empty:
                parts_list = [f"{row['part_name']} ({row['part_code']}) - متوفر: {row['quantity']}" for _, row in parts_df.iterrows()]
                selected_parts = st.multiselect("اختر قطع الغيار المستخدمة", parts_list)
                
                parts_usage = []
                for part_str in selected_parts:
                    part_code = part_str.split("(")[1].split(")")[0]
                    part_info = parts_df[parts_df['part_code'] == part_code].iloc[0]
                    qty = st.number_input(f"الكمية المستخدمة من {part_info['part_name']}", min_value=1, max_value=part_info['quantity'], value=1, key=f"qty_{part_code}")
                    parts_usage.append({"code": part_code, "qty": qty, "price": part_info['price']})
            else:
                st.info("لا توجد قطع غيار متاحة في المخزون")
                parts_usage = []
        
        if st.form_submit_button("حفظ البيانات النهائية"):
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
                cursor = conn.cursor()
                cursor.execute("INSERT INTO repairs (client_name, phone, phone2, visit_date, governorate, address, report, file_name, cost, tech_name, assistant_name, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                             (name, phone, phone2, str(date_v), gov, addr, rep, file_name, cost, "", "", ""))
                repair_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                # إضافة/تحديث العميل
                add_or_update_customer(name, phone, phone2, addr, gov)
                update_customer_cost(phone, cost)
                
                # تسجيل استخدام قطع الغيار
                total_parts_cost = 0
                for part in parts_usage:
                    success, msg = use_inventory_part(repair_id, part["code"], part["qty"], f"استخدام في معاينة {name}")
                    if success:
                        total_parts_cost += part["qty"] * part["price"]
                        st.success(f"✅ {msg}")
                    else:
                        st.warning(f"⚠️ {msg}")
                
                if total_parts_cost > 0:
                    st.info(f"💰 إجمالي تكلفة قطع الغيار: {total_parts_cost} ج.م")
                
                # إضافة إشعار
                add_notification("معاينة جديدة", f"تم إضافة معاينة جديدة للعميل {name}", "info")
                
                # نسخ احتياطي تلقائي
                auto_backup()
                
                st.success("✅ تم الحفظ بنجاح!")
                st.session_state.form_counter += 1
                st.rerun()

# ==================== تبويب إدارة المخزون ====================
with tab4:
    if st.session_state.user_role in ["admin", "supervisor"]:
        st.subheader("📦 إدارة المخزون (قطع الغيار)")
        
        tabs_inv = st.tabs(["➕ إضافة قطعة جديدة", "📋 قائمة المخزون", "📊 استخدامات المخزون", "⚠️ مخزون منخفض"])
        
        with tabs_inv[0]:
            with st.form("add_inventory_form"):
                col1, col2 = st.columns(2)
                with col1:
                    part_name = st.text_input("اسم القطعة")
                    part_code = st.text_input("الكود (فريد)")
                    quantity = st.number_input("الكمية المتوفرة", min_value=0, value=0)
                    min_quantity = st.number_input("الحد الأدنى للتنبيه", min_value=0, value=5)
                with col2:
                    price = st.number_input("سعر القطعة (ج.م)", min_value=0.0, value=0.0)
                    unit = st.text_input("الوحدة", value="قطعة")
                    supplier = st.text_input("المورد")
                
                if st.form_submit_button("إضافة قطعة"):
                    if part_name and part_code:
                        success, msg = add_inventory_item(part_name, part_code, quantity, min_quantity, price, unit, supplier)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("اسم القطعة والكود مطلوبان")
        
        with tabs_inv[1]:
            conn = get_db_connection()
            inventory_df = pd.read_sql_query("SELECT * FROM inventory ORDER BY part_name", conn)
            conn.close()
            
            if not inventory_df.empty:
                st.dataframe(inventory_df, use_container_width=True)
                
                # تعديل الكميات
                st.markdown("### ✏️ تعديل الكميات")
                col1, col2, col3 = st.columns(3)
                with col1:
                    part_options = [f"{row['part_name']} ({row['part_code']})" for _, row in inventory_df.iterrows()]
                    selected_part = st.selectbox("اختر القطعة", part_options)
                with col2:
                    quantity_change = st.number_input("تغير الكمية (+ للإضافة، - للخصم)", value=0)
                with col3:
                    if st.button("تحديث الكمية"):
                        part_code = selected_part.split("(")[1].split(")")[0]
                        part_id = inventory_df[inventory_df['part_code'] == part_code]['id'].values[0]
                        update_inventory_quantity(part_id, quantity_change)
                        st.success("تم تحديث الكمية")
                        st.rerun()
            else:
                st.info("لا توجد قطع غيار في المخزون")
        
        with tabs_inv[2]:
            conn = get_db_connection()
            usage_df = pd.read_sql_query("""
                SELECT iu.*, inv.part_name, inv.part_code, r.client_name 
                FROM inventory_usage iu 
                JOIN inventory inv ON iu.part_id = inv.id 
                LEFT JOIN repairs r ON iu.repair_id = r.id 
                ORDER BY iu.usage_date DESC LIMIT 100
            """, conn)
            conn.close()
            
            if not usage_df.empty:
                st.dataframe(usage_df, use_container_width=True)
            else:
                st.info("لا توجد استخدامات مسجلة")
        
        with tabs_inv[3]:
            low_stock = get_low_stock_items()
            if not low_stock.empty:
                st.warning("⚠️ القطع التالية تحتاج إلى إعادة طلب:")
                for _, item in low_stock.iterrows():
                    st.markdown(f"- **{item['part_name']}** ({item['part_code']}): المتبقي {item['quantity']} (الحد الأدنى {item['min_quantity']})")
            else:
                st.success("✅ جميع قطع الغيار ضمن الحدود الآمنة")
    else:
        st.error("⛔ هذه الصفحة متاحة للمدير والمشرف فقط")

# ==================== تبويب إدارة العملاء ====================
with tab5:
    st.subheader("👤 إدارة العملاء")
    
    conn = get_db_connection()
    customers_df = pd.read_sql_query("SELECT * FROM customers ORDER BY total_visits DESC", conn)
    conn.close()
    
    if not customers_df.empty:
        st.dataframe(customers_df, use_container_width=True)
        
        # البحث عن عميل
        st.markdown("### 🔍 البحث عن عميل")
        search_phone = st.text_input("ابحث برقم التليفون", max_chars=11)
        
        if search_phone:
            customer = customers_df[customers_df['phone'] == search_phone]
            if not customer.empty:
                st.markdown(f"### معلومات العميل: {customer.iloc[0]['name']}")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**رقم التليفون:** {customer.iloc[0]['phone']}")
                    st.write(f"**رقم تليفون ثاني:** {customer.iloc[0]['phone2']}")
                    st.write(f"**العنوان:** {customer.iloc[0]['address']}")
                with col2:
                    st.write(f"**المحافظة:** {customer.iloc[0]['governorate']}")
                    st.write(f"**عدد الزيارات:** {customer.iloc[0]['total_visits']}")
                    st.write(f"**إجمالي المصروف:** {customer.iloc[0]['total_cost']} ج.م")
                
                # عرض معاينات العميل
                st.markdown("### 📋 معاينات العميل")
                repairs_history = get_customer_history(search_phone)
                if not repairs_history.empty:
                    st.dataframe(repairs_history[['visit_date', 'client_name', 'cost', 'tech_name', 'governorate']], use_container_width=True)
                else:
                    st.info("لا توجد معاينات سابقة")
            else:
                st.warning("لا يوجد عميل بهذا الرقم")
    else:
        st.info("لا توجد عملاء مسجلين")

# ==================== تبويب سجل المعاينات ====================
with tab2:
    st.subheader("📊 سجل المعاينات")
    
    # تصفية حسب الدور
    if st.session_state.user_role == "tech" and hasattr(st.session_state, 'tech_name'):
        conn = get_db_connection()
        df_raw = pd.read_sql_query("SELECT id, client_name as 'العميل', phone as 'التليفون', phone2 as 'تليفون 2', tech_name as 'الفني', cost as 'التكلفة', visit_date as 'التاريخ', governorate as 'المحافظة', address as 'العنوان', file_name FROM repairs WHERE tech_name = ? ORDER BY visit_date DESC, id DESC", conn, params=(st.session_state.tech_name,))
        conn.close()
        st.info(f"🔍 عرض معاينات الفني: {st.session_state.tech_name}")
    else:
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
        search_col1, search_col2, search_col3, search_col4 = st.columns(4)
        
        with search_col1:
            search_query = st.text_input("🔍 اسم العميل", placeholder="اكتب للبحث...")
        with search_col2:
            search_phone = st.text_input("📞 رقم التليفون", placeholder="ابحث برقم الهاتف")
        with search_col3:
            start_date = st.date_input("من تاريخ", value=None)
        with search_col4:
            end_date = st.date_input("إلى تاريخ", value=None)
        
        df = df_raw.copy()
        
        if search_query:
            df = df[df['العميل'].str.contains(search_query, na=False, case=False)]
        if search_phone:
            df = df[df['التليفون'].str.contains(search_phone, na=False)]
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
                    column_config={"واتساب": st.column_config.LinkColumn("واتساب", display_text="💬 مراسلة")}
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
                    
                    # عرض الفاتورة
                    if st.button("📄 إنشاء فاتورة PDF", key=f"invoice_{selected_id}"):
                        invoice_pdf = generate_invoice_pdf(row)
                        st.download_button(label="📥 تحميل الفاتورة", data=invoice_pdf, file_name=f"invoice_{selected_id}.pdf", mime="application/pdf")
                    
                    # إرسال واتساب
                    if st.button("📱 إرسال رابط واتساب", key=f"whatsapp_{selected_id}"):
                        message = f"مرحباً {row['client_name']}\nتم تسجيل معاينة في Expert 2M\nالتاريخ: {row['visit_date']}\nالتكلفة: {row['cost']} ج.م"
                        success, result = send_whatsapp_message(row['phone'], message)
                        if success:
                            st.markdown(f"[اضغط هنا لفتح واتساب]({result})", unsafe_allow_html=True)
                    
                    # عرض PDF
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
                            u_phone = st.text_input("التليفون الأول", row['phone'], max_chars=11)
                            u_phone2 = st.text_input("التليفون الثاني", row['phone2'] if row['phone2'] else "", max_chars=11)
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
                        
                        col_save, col_del = st.columns(2)
                        
                        with col_save:
                            if st.form_submit_button("💾 حفظ التعديلات"):
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
                                    
                                    # تحديث بيانات العميل
                                    add_or_update_customer(u_name, u_phone, u_phone2, u_addr, u_gov)
                                    
                                    st.success("✅ تم التحديث بنجاح!")
                                    st.rerun()
                        
                        with col_del:
                            if st.session_state.user_role == "admin":
                                if st.form_submit_button("🗑️ مسح المعاينة", type="secondary"):
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
                                    add_notification("تم مسح معاينة", f"تم مسح معاينة العميل {row['client_name']}", "warning")
                                    st.success("🗑️ تم المسح بنجاح!")
                                    st.rerun()
                    
                    st.markdown("---")
    else:
        st.info("لا توجد سجلات حالياً.")
