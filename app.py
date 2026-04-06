import streamlit as st
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
import requests
import io
import time
import math

# ==================== إعدادات Supabase ====================
SUPABASE_URL = "https://ahrhizgfcqmefcdjzskm.supabase.co"
SUPABASE_KEY = "sb_publishable_YaeiIPPa7mOt2az35yKKkQ_uKMpDACa"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ==================== إعدادات الصفحة ====================
st.set_page_config(page_title="Expert 2M - Management System", layout="wide")

# ==================== ستايل مخصص ====================
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        color: #ffffff;
        direction: rtl;
    }
    
    div, p, h1, h2, h3, h4, h5, h6, span, label {
        direction: rtl;
        text-align: right;
    }
    
    [data-testid="stForm"] {
        border: 1px solid #00b4d8;
        border-radius: 20px;
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        padding: 20px;
        box-shadow: 0 8px 32px rgba(0, 180, 216, 0.1);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        justify-content: flex-start;
        flex-wrap: wrap;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 15px 15px 0 0;
        padding: 10px 20px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: linear-gradient(135deg, #00b4d8, #0077b6);
        transform: translateY(-2px);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        border: 1px solid #00b4d8;
        box-shadow: 0 8px 32px rgba(0, 180, 216, 0.15);
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
    }
    
    .metric-card h3 {
        margin: 0;
        font-size: 16px;
        color: #90e0ef;
    }
    
    .metric-card h1 {
        margin: 10px 0 0 0;
        font-size: 36px;
        font-weight: bold;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #00b4d8, #0077b6);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 10px 20px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #48cae4, #0096c7);
        transform: scale(1.02);
        box-shadow: 0 4px 15px rgba(0, 180, 216, 0.3);
    }
    
    .stButton > button[data-baseweb="button-secondary"] {
        background: linear-gradient(135deg, #e63946, #c1121f);
    }
    
    .stTextInput > div > div > input, .stSelectbox > div > div, .stTextArea > div > textarea {
        background-color: #1a1a2e;
        border: 1px solid #00b4d8;
        border-radius: 12px;
        color: white;
    }
    
    .stDataFrame table {
        direction: rtl;
        text-align: right;
    }
    
    .stDataFrame th, .stDataFrame td {
        text-align: right !important;
    }
    
    .stPlotlyChart {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 20px;
        padding: 15px;
        border: 1px solid #00b4d8;
    }
    
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 12px;
        border: 1px solid #00b4d8;
    }
    
    .stAlert {
        border-radius: 12px;
        border-right: 4px solid #00b4d8;
    }
    
    .status-new { background: #00b4d8; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }
    .status-completed { background: #2ecc71; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }
    .status-delayed { background: #e67e22; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }
    
    .pagination {
        display: flex;
        justify-content: center;
        gap: 10px;
        margin-top: 20px;
        direction: ltr;
    }
    
    .whatsapp-link {
        background-color: #25D366;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        text-decoration: none;
        font-weight: bold;
        display: inline-block;
    }
    .whatsapp-link:hover {
        background-color: #128C7E;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== إعدادات المصادقة ====================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()

USERS = {
    "admin": {"password": ADMIN_PASSWORD_HASH, "role": "admin", "name": "المدير"},
}

def check_password():
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
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")
        return False
    return True

# ==================== مجلدات ====================
UPLOAD_FOLDER = "uploaded_reports"
BACKUP_FOLDER = "backups"

for folder in [UPLOAD_FOLDER, BACKUP_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# ==================== دوال Supabase ====================
def supabase_get(table):
    try:
        response = requests.get(f"{SUPABASE_URL}/rest/v1/{table}?select=*", headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def supabase_post(table, data):
    try:
        response = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, json=data)
        return response.status_code in [200, 201]
    except:
        return False

def supabase_put(table, id, data):
    try:
        response = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{id}", headers=HEADERS, json=data)
        return response.status_code in [200, 204]
    except:
        return False

def supabase_delete(table, id):
    try:
        response = requests.delete(f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{id}", headers=HEADERS)
        return response.status_code in [200, 204]
    except:
        return False

# ==================== دوال البيانات ====================
def get_repairs():
    data = supabase_get("repairs")
    if data and len(data) > 0:
        df = pd.DataFrame(data)
        # الحفاظ على الأسماء الإنجليزية للاستخدام الداخلي
        return df
    return pd.DataFrame()

def add_repair(data):
    return supabase_post("repairs", data)

def update_repair(repair_id, data):
    return supabase_put("repairs", repair_id, data)

def delete_repair(repair_id):
    return supabase_delete("repairs", repair_id)

def get_staff():
    data = supabase_get("staff")
    if data and len(data) > 0:
        return pd.DataFrame(data)
    return pd.DataFrame()

def add_staff(name):
    return supabase_post("staff", {"name": name})

def delete_staff(staff_id):
    return supabase_delete("staff", staff_id)

def get_customers():
    data = supabase_get("customers")
    if data and len(data) > 0:
        return pd.DataFrame(data)
    return pd.DataFrame()

def add_or_update_customer(name, phone, phone2, address, governorate):
    customers = get_customers()
    if not customers.empty and 'phone' in customers.columns:
        existing = customers[customers['phone'] == phone]
        if not existing.empty:
            customer = existing.iloc[0]
            supabase_put("customers", customer['id'], {
                "name": name, "phone2": phone2, "address": address,
                "governorate": governorate, "total_visits": customer.get('total_visits', 0) + 1
            })
        else:
            supabase_post("customers", {
                "name": name, "phone": phone, "phone2": phone2,
                "address": address, "governorate": governorate,
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "total_visits": 1, "total_cost": 0
            })
    else:
        supabase_post("customers", {
            "name": name, "phone": phone, "phone2": phone2,
            "address": address, "governorate": governorate,
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "total_visits": 1, "total_cost": 0
        })

def update_customer_cost(phone, cost):
    try:
        cost_val = float(cost) if cost else 0
        customers = get_customers()
        if not customers.empty and 'phone' in customers.columns:
            existing = customers[customers['phone'] == phone]
            if not existing.empty:
                customer = existing.iloc[0]
                current_cost = customer.get('total_cost', 0)
                supabase_put("customers", customer['id'], {"total_cost": current_cost + cost_val})
    except:
        pass

def get_inventory():
    data = supabase_get("inventory")
    if data and len(data) > 0:
        return pd.DataFrame(data)
    return pd.DataFrame()

def add_inventory_item(part_name, part_code, quantity, min_quantity, price, unit, supplier):
    return supabase_post("inventory", {
        "part_name": part_name, "part_code": part_code,
        "quantity": quantity, "min_quantity": min_quantity,
        "price": price, "unit": unit, "supplier": supplier,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

def update_inventory_quantity(part_id, quantity_change):
    inventory = get_inventory()
    if not inventory.empty:
        part = inventory[inventory['id'] == part_id]
        if not part.empty:
            new_quantity = part.iloc[0]['quantity'] + quantity_change
            supabase_put("inventory", part_id, {
                "quantity": new_quantity,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

def delete_inventory_item(part_id):
    return supabase_delete("inventory", part_id)

def get_low_stock_items():
    inventory = get_inventory()
    if not inventory.empty and 'quantity' in inventory.columns and 'min_quantity' in inventory.columns:
        return inventory[inventory['quantity'] <= inventory['min_quantity']]
    return pd.DataFrame()

def get_notifications():
    data = supabase_get("notifications")
    if data and len(data) > 0:
        df = pd.DataFrame(data)
        if 'is_read' in df.columns:
            return df[df['is_read'] == 0].sort_values('created_date', ascending=False)
        return df
    return pd.DataFrame()

def add_notification(title, message, type="info"):
    supabase_post("notifications", {
        "title": title, "message": message, "type": type,
        "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_read": 0
    })

def mark_notification_read(notif_id):
    supabase_put("notifications", notif_id, {"is_read": 1})

def delete_notification(notif_id):
    supabase_delete("notifications", notif_id)

def delete_all_notifications():
    notifs = get_notifications()
    if not notifs.empty:
        for _, notif in notifs.iterrows():
            supabase_delete("notifications", notif['id'])
        return True
    return False

# ==================== دالة عرض PDF ====================
def display_pdf_pdfjs(file_name):
    try:
        if not file_name:
            return
        
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        file_path = os.path.join(UPLOAD_FOLDER, file_name)
        
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))
        
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
                .controls {{ margin: 10px 0; text-align: center; direction: ltr; }}
                button {{ background-color: #00b4d8; color: white; border: none; padding: 8px 16px; margin: 0 5px; border-radius: 8px; cursor: pointer; }}
                button:hover {{ background-color: #0077b6; }}
                canvas {{ border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }}
            </style>
        </head>
        <body>
            <div class="controls">
                <button onclick="prevPage()">⬅️ السابق</button>
                <span>الصفحة <span id="page_num"></span> / <span id="page_count"></span></span>
                <button onclick="nextPage()">التالي ➡️</button>
            </div>
            <canvas id="pdf-canvas" style="width:100%; border-radius:12px;"></canvas>
            
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
        
    except Exception as e:
        st.error(f"خطأ في عرض الملف: {e}")

# ==================== دوال الإحصائيات ====================
def get_dashboard_stats():
    repairs_df = get_repairs()
    customers_df = get_customers()
    inventory_df = get_inventory()
    
    today = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%Y-%m")
    
    total = len(repairs_df)
    today_count = 0
    month_count = 0
    
    if not repairs_df.empty and 'visit_date' in repairs_df.columns:
        today_count = len(repairs_df[repairs_df['visit_date'] == today])
        month_count = len(repairs_df[repairs_df['visit_date'].str.startswith(current_month)])
    
    total_revenue = 0
    if not repairs_df.empty and 'cost' in repairs_df.columns:
        try:
            repairs_df['cost_clean'] = repairs_df['cost'].astype(str).str.replace('ج.م', '').str.replace('EGP', '').str.replace(' ', '').str.replace(',', '')
            repairs_df['cost_clean'] = pd.to_numeric(repairs_df['cost_clean'], errors='coerce').fillna(0)
            total_revenue = repairs_df['cost_clean'].sum()
        except:
            total_revenue = 0
    
    customers_count = len(customers_df)
    low_stock = len(get_low_stock_items())
    
    status_counts = {}
    if not repairs_df.empty and 'status' in repairs_df.columns:
        status_counts = repairs_df['status'].value_counts().to_dict()
    
    return {
        'total': total, 'today': today_count, 'month': month_count,
        'revenue': total_revenue, 'customers': customers_count,
        'low_stock': low_stock, 'status_counts': status_counts
    }

def show_dashboard():
    stats = get_dashboard_stats()
    
    st.markdown("## 📊 لوحة التحكم والإحصائيات")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📋 إجمالي المعاينات</h3>
            <h1 style="color: #00b4d8;">{stats['total']}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📅 معاينات اليوم</h3>
            <h1 style="color: #48cae4;">{stats['today']}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📆 هذا الشهر</h3>
            <h1 style="color: #90e0ef;">{stats['month']}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>💰 الإيرادات</h3>
            <h1 style="color: #2ecc71;">{stats['revenue']:,.0f} ج.م</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <h3>👥 العملاء</h3>
            <h1 style="color: #f39c12;">{stats['customers']}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        st.markdown(f"""
        <div class="metric-card">
            <h3>⚠️ مخزون منخفض</h3>
            <h1 style="color: #e74c3c;">{stats['low_stock']}</h1>
        </div>
        """, unsafe_allow_html=True)
    
    if stats['status_counts']:
        st.markdown("### 📊 توزيع حالات المعاينات")
        col_s1, col_s2, col_s3 = st.columns(3)
        
        with col_s1:
            new_count = stats['status_counts'].get('جديدة', 0)
            st.markdown(f"""
            <div class="metric-card">
                <h3>🟦 جديدة</h3>
                <h1 style="color: #00b4d8;">{new_count}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col_s2:
            completed_count = stats['status_counts'].get('تمت', 0)
            st.markdown(f"""
            <div class="metric-card">
                <h3>🟩 تمت</h3>
                <h1 style="color: #2ecc71;">{completed_count}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        with col_s3:
            delayed_count = stats['status_counts'].get('مؤجلة', 0)
            st.markdown(f"""
            <div class="metric-card">
                <h3>🟧 مؤجلة</h3>
                <h1 style="color: #e67e22;">{delayed_count}</h1>
            </div>
            """, unsafe_allow_html=True)
    
    repairs_df = get_repairs()
    if not repairs_df.empty and 'visit_date' in repairs_df.columns:
        repairs_df['visit_date'] = pd.to_datetime(repairs_df['visit_date'])
        daily_counts = repairs_df.groupby(repairs_df['visit_date'].dt.date).size().reset_index(name='count')
        daily_counts.columns = ['التاريخ', 'عدد المعاينات']
        
        fig = px.bar(daily_counts, x='التاريخ', y='عدد المعاينات', title='المعاينات اليومية', color_discrete_sequence=['#00b4d8'])
        fig.update_layout(plot_bgcolor='rgba(26,26,46,0.8)', paper_bgcolor='rgba(26,26,46,0.8)', font_color='white')
        st.plotly_chart(fig, use_container_width=True)

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

# ==================== حالات المعاينة ====================
STATUS_OPTIONS = ["جديدة", "تمت", "مؤجلة"]
STATUS_STYLES = {
    "جديدة": "🟦 جديدة",
    "تمت": "🟩 تمت",
    "مؤجلة": "🟧 مؤجلة"
}

# ==================== التحقق من تسجيل الدخول ====================
if not check_password():
    st.stop()

# ==================== الشريط الجانبي ====================
with st.sidebar:
    st.markdown(f"### 👤 مرحباً {st.session_state.user_name}")
    st.markdown(f"**الدور:** {st.session_state.user_role}")
    
    st.markdown("---")
    
    unread_notifs = get_notifications()
    if not unread_notifs.empty:
        st.markdown("### 🔔 الإشعارات")
        
        col_n1, col_n2 = st.columns([3, 1])
        with col_n2:
            if st.button("🗑️ مسح الكل", use_container_width=True):
                delete_all_notifications()
                st.rerun()
        
        for _, notif in unread_notifs.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.info(f"**{notif['title']}**\n\n{notif['message']}")
            with col2:
                if st.button("✔️", key=f"read_{notif['id']}"):
                    mark_notification_read(notif['id'])
                    st.rerun()
    
    st.markdown("---")
    st.markdown("### 💾 حفظ البيانات")
    st.success("✅ البيانات محفوظة في Supabase (سحابياً)")
    
    if st.button("🚪 تسجيل خروج", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ==================== التبويبات ====================
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 لوحة التحكم", "➕ تسجيل معاينة جديدة", "📋 سجل المعاينات",
    "👥 إدارة الفنيين", "📦 إدارة المخزون", "👤 إدارة العملاء"
])

# ==================== تبويب لوحة التحكم ====================
with tab0:
    show_dashboard()

# ==================== تبويب إدارة الفنيين ====================
with tab3:
    st.subheader("👥 إدارة قاعدة بيانات الفنيين")
    
    col_f1, col_f2 = st.columns([1, 1])
    
    with col_f1:
        with st.form("add_staff_form"):
            new_staff = st.text_input("✏️ اسم الفني الجديد")
            if st.form_submit_button("➕ إضافة فني", use_container_width=True):
                if new_staff:
                    if add_staff(new_staff):
                        st.success(f"✅ تم إضافة {new_staff}")
                        st.rerun()
                    else:
                        st.error("❌ حدث خطأ")
                else:
                    st.warning("⚠️ برجاء كتابة اسم")
    
    with col_f2:
        staff_df = get_staff()
        if not staff_df.empty:
            st.write("### 📋 قائمة الفنيين")
            for _, row in staff_df.iterrows():
                col_name, col_del = st.columns([3, 1])
                with col_name:
                    st.write(f"👨‍🔧 {row['name']}")
                with col_del:
                    if st.button("🗑️ حذف", key=f"del_staff_{row['id']}", use_container_width=True):
                        delete_staff(row['id'])
                        st.rerun()
        else:
            st.info("📭 لا يوجد فنيين مسجلين")

# جلب أسماء الفنيين
staff_df = get_staff()
staff_names = ["جميع الفنيين"] + staff_df['name'].tolist() if not staff_df.empty else ["جميع الفنيين"]

# ==================== تبويب تسجيل معاينة جديدة ====================
with tab1:
    st.subheader("📝 إضافة بيانات عميل جديد")
    
    if 'form_counter' not in st.session_state:
        st.session_state.form_counter = 0
    
    def get_form_key():
        return f"form_{st.session_state.form_counter}"
    
    with st.form(key=get_form_key()):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("👤 اسم العميل")
            phone = st.text_input("📞 رقم التليفون الأول", max_chars=11, help="11 رقم يبدأ بـ 01")
            phone2 = st.text_input("📞 رقم التليفون الثاني (اختياري)", max_chars=11, help="11 رقم يبدأ بـ 01")
            cost = st.text_input("💰 التكلفة (EGP)")
        with c2:
            gov = st.selectbox("📍 المحافظة", ALL_GOVS)
            addr = st.text_input("🏠 العنوان بالتفصيل")
            date_v = st.date_input("📅 التاريخ", datetime.now())
            status = st.selectbox("📌 حالة المعاينة", STATUS_OPTIONS)
        
        rep = st.text_area("📝 وصف العطل", height=100)
        file = st.file_uploader("📎 ارفع التقرير (PDF)", type=['pdf'])
        
        tech_name = st.selectbox("👨‍🔧 اسم الفني", ["لم يتم التحديد"] + staff_names[1:])
        
        with st.expander("🔧 استخدام قطع غيار (اختياري)"):
            parts_df = get_inventory()
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
        
        if st.form_submit_button("💾 حفظ البيانات", use_container_width=True):
            valid1, msg1 = validate_phone(phone)
            valid2, msg2 = validate_phone(phone2) if phone2 else (True, "")
            
            if not valid1:
                st.error(msg1)
            elif not valid2:
                st.error(msg2)
            else:
                file_name = ""
                if file:
                    if not os.path.exists(UPLOAD_FOLDER):
                        os.makedirs(UPLOAD_FOLDER)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_name = f"{name}_{timestamp}_{file.name}"
                    file_path = os.path.join(UPLOAD_FOLDER, file_name)
                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer())
                
                repair_data = {
                    "client_name": name, "phone": phone, "phone2": phone2,
                    "visit_date": str(date_v), "governorate": gov, "address": addr,
                    "report": rep, "file_name": file_name, "cost": cost,
                    "tech_name": tech_name if tech_name != "لم يتم التحديد" else "",
                    "assistant_name": "", "notes": "", "status": status,
                    "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                if add_repair(repair_data):
                    add_or_update_customer(name, phone, phone2, addr, gov)
                    update_customer_cost(phone, cost)
                    
                    time.sleep(0.3)
                    repairs_df = get_repairs()
                    if not repairs_df.empty:
                        repair_id = repairs_df.iloc[-1]['id']
                        for part in parts_usage:
                            use_inventory_part(repair_id, part["code"], part["qty"], f"استخدام في معاينة {name}")
                    
                    add_notification("معاينة جديدة", f"تم إضافة معاينة جديدة للعميل {name}", "info")
                    st.success("✅ تم الحفظ بنجاح!")
                    st.session_state.form_counter += 1
                    st.rerun()
                else:
                    st.error("❌ حدث خطأ في حفظ البيانات")

# ==================== تبويب سجل المعاينات ====================
with tab2:
    st.subheader("📋 سجل المعاينات")
    
    repairs_df = get_repairs()
    
    if not repairs_df.empty:
        st.markdown("### 🔍 بحث وتصفية متقدم")
        
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            search_query = st.text_input("🔍 بحث باسم العميل", placeholder="اكتب اسم العميل...")
        
        with col_f2:
            search_phone = st.text_input("📞 بحث برقم التليفون", placeholder="اكتب رقم التليفون...")
        
        with col_f3:
            selected_tech = st.selectbox("👨‍🔧 فلترة باسم الفني", staff_names)
        
        col_f4, col_f5, col_f6 = st.columns(3)
        
        with col_f4:
            start_date = st.date_input("📅 من تاريخ", value=None)
        
        with col_f5:
            end_date = st.date_input("📅 إلى تاريخ", value=None)
        
        with col_f6:
            selected_status = st.selectbox("📌 فلترة بالحالة", ["الكل"] + STATUS_OPTIONS)
        
        df = repairs_df.copy()
        
        # تطبيق الفلاتر (باستخدام الأسماء الإنجليزية)
        if search_query and 'client_name' in df.columns:
            df = df[df['client_name'].str.contains(search_query, na=False, case=False)]
        if search_phone and 'phone' in df.columns:
            df = df[df['phone'].str.contains(search_phone, na=False)]
        if selected_tech != "جميع الفنيين" and 'tech_name' in df.columns:
            df = df[df['tech_name'] == selected_tech]
        if start_date and 'visit_date' in df.columns:
            df = df[pd.to_datetime(df['visit_date']) >= pd.to_datetime(start_date)]
        if end_date and 'visit_date' in df.columns:
            df = df[pd.to_datetime(df['visit_date']) <= pd.to_datetime(end_date)]
        if selected_status != "الكل" and 'status' in df.columns:
            df = df[df['status'] == selected_status]
        
        if not df.empty:
            # إعادة تسمية الأعمدة للعرض فقط
            df_display = df.copy()
            df_display['العميل'] = df_display['client_name']
            df_display['التليفون'] = df_display['phone']
            df_display['تليفون 2'] = df_display['phone2'].fillna('') if 'phone2' in df_display else ""
            df_display['الفني'] = df_display['tech_name']
            df_display['التكلفة'] = df_display['cost']
            df_display['التاريخ'] = df_display['visit_date']
            df_display['المحافظة'] = df_display['governorate']
            df_display['العنوان'] = df_display['address']
            df_display['الحالة'] = df_display['status'].map(lambda x: STATUS_STYLES.get(x, x)) if 'status' in df_display else ""
            
            # دالة رابط واتساب
            def make_whatsapp_link(phone_num):
                if not phone_num or phone_num == "" or pd.isna(phone_num):
                    return "#"
                p = str(phone_num).strip()
                p = ''.join(filter(str.isdigit, p))
                if p:
                    num = p if p.startswith('2') else '2' + p
                    return f'<a href="https://wa.me/{num}" target="_blank" class="whatsapp-link">🟢 واتساب</a>'
                return "#"
            
            df_display['واتساب'] = df_display['phone'].apply(make_whatsapp_link) if 'phone' in df_display else "#"
            
            # ترتيب الأعمدة
            display_cols = ['العميل', 'التليفون', 'تليفون 2', 'الفني', 'التكلفة', 'التاريخ', 'المحافظة', 'العنوان', 'الحالة', 'واتساب']
            existing_cols = [col for col in display_cols if col in df_display.columns]
            df_display = df_display[existing_cols]
            
            # عرض الجدول
            st.write(f"🔎 تم العثور على {len(df_display)} سجل")
            st.dataframe(df_display, use_container_width=True)
            
            # جزء التعديل
            st.markdown("---")
            st.markdown("### ✏️ تعديل أو عرض معاينة")
            
            ids = df['id'].tolist()
            if ids:
                selected_id = st.selectbox("اختر معاينة للتعديل", ids)
                row = df[df['id'] == selected_id].iloc[0]
                
                # عرض PDF
                if row.get('file_name'):
                    with st.expander("📄 عرض التقرير"):
                        display_pdf_pdfjs(row['file_name'])
                
                # نموذج التعديل
                with st.form(f"edit_form_{selected_id}"):
                    col_l, col_r = st.columns(2)
                    with col_l:
                        u_name = st.text_input("اسم العميل", row['client_name'])
                        u_phone = st.text_input("رقم التليفون الأول", row['phone'], max_chars=11)
                        u_phone2 = st.text_input("رقم التليفون الثاني", row['phone2'] if row['phone2'] else "", max_chars=11)
                        current_tech_idx = staff_names.index(row['tech_name']) if row['tech_name'] in staff_names else 0
                        if current_tech_idx == 0 and "جميع الفنيين" in staff_names:
                            current_tech_idx = 0
                        u_tech = st.selectbox("اسم الفني", ["لم يتم التحديد"] + staff_names[1:], index=current_tech_idx if current_tech_idx > 0 else 0)
                    with col_r:
                        u_cost = st.text_input("التكلفة", row['cost'])
                        current_gov_idx = ALL_GOVS.index(row['governorate']) if row['governorate'] in ALL_GOVS else 0
                        u_gov = st.selectbox("المحافظة", ALL_GOVS, index=current_gov_idx)
                        u_addr = st.text_input("العنوان", row['address'])
                        u_date = st.date_input("تاريخ المعاينة", datetime.strptime(row['visit_date'], '%Y-%m-%d') if row.get('visit_date') else datetime.now())
                        u_status = st.selectbox("حالة المعاينة", STATUS_OPTIONS, index=STATUS_OPTIONS.index(row['status']) if row['status'] in STATUS_OPTIONS else 0)
                    
                    u_notes = st.text_area("ملاحظات إضافية", row['notes'] if row['notes'] else "")
                    st.write(f"**وصف العطل المسجل:** {row['report']}")
                    st.markdown("---")
                    new_pdf = st.file_uploader("تحديث التقرير (PDF)", type=['pdf'], key=f"pdf_up_{selected_id}")
                    
                    col_save, col_del = st.columns(2)
                    
                    with col_save:
                        if st.form_submit_button("💾 حفظ التعديلات", use_container_width=True):
                            valid1, msg1 = validate_phone(u_phone)
                            valid2, msg2 = validate_phone(u_phone2) if u_phone2 else (True, "")
                            
                            if not valid1:
                                st.error(msg1)
                            elif not valid2:
                                st.error(msg2)
                            else:
                                file_name = row.get('file_name', '')
                                if new_pdf:
                                    if not os.path.exists(UPLOAD_FOLDER):
                                        os.makedirs(UPLOAD_FOLDER)
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    file_name = f"{u_name}_{timestamp}_{new_pdf.name}"
                                    file_path = os.path.join(UPLOAD_FOLDER, file_name)
                                    with open(file_path, "wb") as f:
                                        f.write(new_pdf.getbuffer())
                                    if row.get('file_name'):
                                        old_path = os.path.join(UPLOAD_FOLDER, row['file_name'])
                                        if os.path.exists(old_path):
                                            try:
                                                os.remove(old_path)
                                            except:
                                                pass
                                
                                update_repair(selected_id, {
                                    "client_name": u_name, "phone": u_phone, "phone2": u_phone2,
                                    "tech_name": u_tech if u_tech != "لم يتم التحديد" else "",
                                    "cost": u_cost, "governorate": u_gov,
                                    "address": u_addr, "notes": u_notes, "visit_date": str(u_date),
                                    "status": u_status, "file_name": file_name
                                })
                                
                                add_or_update_customer(u_name, u_phone, u_phone2, u_addr, u_gov)
                                update_customer_cost(u_phone, u_cost)
                                
                                st.success("✅ تم التحديث بنجاح!")
                                st.rerun()
                    
                    with col_del:
                        if st.session_state.user_role == "admin":
                            if st.form_submit_button("🗑️ مسح المعاينة", type="secondary", use_container_width=True):
                                if row.get('file_name'):
                                    file_to_delete = os.path.join(UPLOAD_FOLDER, row['file_name'])
                                    if os.path.exists(file_to_delete):
                                        try:
                                            os.remove(file_to_delete)
                                        except:
                                            pass
                                delete_repair(selected_id)
                                add_notification("تم مسح معاينة", f"تم مسح معاينة العميل {row.get('client_name', '')}", "warning")
                                st.success("🗑️ تم المسح بنجاح!")
                                st.rerun()
        else:
            st.info("📭 لا توجد سجلات تطابق معايير البحث")
    else:
        st.info("📭 لا توجد سجلات حالياً.")

# ==================== تبويب إدارة المخزون ====================
with tab4:
    st.subheader("📦 إدارة المخزون (قطع الغيار)")
    
    tabs_inv = st.tabs(["➕ إضافة قطعة جديدة", "📋 قائمة المخزون", "⚠️ مخزون منخفض"])
    
    with tabs_inv[0]:
        with st.form("add_inventory_form"):
            col1, col2 = st.columns(2)
            with col1:
                part_name = st.text_input("📦 اسم القطعة")
                part_code = st.text_input("🏷️ الكود (فريد)")
                quantity = st.number_input("🔢 الكمية المتوفرة", min_value=0, value=0)
                min_quantity = st.number_input("⚠️ الحد الأدنى للتنبيه", min_value=0, value=5)
            with col2:
                price = st.number_input("💰 سعر القطعة (ج.م)", min_value=0.0, value=0.0)
                unit = st.text_input("📏 الوحدة", value="قطعة")
                supplier = st.text_input("🏭 المورد")
            
            if st.form_submit_button("➕ إضافة قطعة", use_container_width=True):
                if part_name and part_code:
                    if add_inventory_item(part_name, part_code, quantity, min_quantity, price, unit, supplier):
                        st.success("✅ تم إضافة القطعة بنجاح")
                        st.rerun()
                    else:
                        st.error("❌ حدث خطأ أو الكود موجود بالفعل")
                else:
                    st.warning("⚠️ اسم القطعة والكود مطلوبان")
    
    with tabs_inv[1]:
        inventory_df = get_inventory()
        if not inventory_df.empty:
            st.dataframe(inventory_df, use_container_width=True)
            
            st.markdown("### ✏️ تعديل أو حذف")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                part_options = [f"{row['part_name']} ({row['part_code']})" for _, row in inventory_df.iterrows()]
                selected_part = st.selectbox("اختر القطعة", part_options)
            with col2:
                quantity_change = st.number_input("تغير الكمية (+ للإضافة، - للخصم)", value=0)
            with col3:
                if st.button("تحديث الكمية", use_container_width=True):
                    part_code = selected_part.split("(")[1].split(")")[0]
                    part_id = inventory_df[inventory_df['part_code'] == part_code]['id'].values[0]
                    update_inventory_quantity(part_id, quantity_change)
                    st.success("✅ تم تحديث الكمية")
                    st.rerun()
            with col4:
                if st.button("🗑️ حذف القطعة", type="secondary", use_container_width=True):
                    part_code = selected_part.split("(")[1].split(")")[0]
                    part_id = inventory_df[inventory_df['part_code'] == part_code]['id'].values[0]
                    delete_inventory_item(part_id)
                    st.success("✅ تم حذف القطعة")
                    st.rerun()
        else:
            st.info("📭 لا توجد قطع غيار في المخزون")
    
    with tabs_inv[2]:
        low_stock = get_low_stock_items()
        if not low_stock.empty:
            st.warning("⚠️ القطع التالية تحتاج إلى إعادة طلب:")
            for _, item in low_stock.iterrows():
                st.markdown(f"- **{item['part_name']}** ({item['part_code']}): المتبقي {item['quantity']} (الحد الأدنى {item['min_quantity']})")
        else:
            st.success("✅ جميع قطع الغيار ضمن الحدود الآمنة")

# ==================== تبويب إدارة العملاء ====================
with tab5:
    st.subheader("👤 إدارة العملاء")
    
    customers_df = get_customers()
    
    if not customers_df.empty:
        st.dataframe(customers_df, use_container_width=True)
        
        st.markdown("### 🔍 البحث عن عميل")
        search_phone = st.text_input("ابحث برقم التليفون", max_chars=11)
        
        if search_phone and 'phone' in customers_df.columns:
            customer = customers_df[customers_df['phone'] == search_phone]
            if not customer.empty:
                st.markdown(f"### 👤 معلومات العميل: {customer.iloc[0]['name']}")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**📞 رقم التليفون:** {customer.iloc[0]['phone']}")
                    st.write(f"**📞 رقم تليفون ثاني:** {customer.iloc[0]['phone2']}")
                    st.write(f"**🏠 العنوان:** {customer.iloc[0]['address']}")
                with col2:
                    st.write(f"**📍 المحافظة:** {customer.iloc[0]['governorate']}")
                    st.write(f"**📊 عدد الزيارات:** {customer.iloc[0]['total_visits']}")
                    st.write(f"**💰 إجمالي المصروف:** {customer.iloc[0]['total_cost']} ج.م")
                
                st.markdown("### 📋 معاينات العميل")
                repairs_history = get_repairs()
                if not repairs_history.empty and 'phone' in repairs_history.columns:
                    customer_repairs = repairs_history[repairs_history['phone'] == search_phone]
                    if not customer_repairs.empty:
                        st.dataframe(customer_repairs[['visit_date', 'client_name', 'cost', 'tech_name', 'governorate', 'status']], use_container_width=True)
                    else:
                        st.info("📭 لا توجد معاينات سابقة")
                else:
                    st.info("📭 لا توجد معاينات سابقة")
            else:
                st.warning("⚠️ لا يوجد عميل بهذا الرقم")
    else:
        st.info("📭 لا توجد عملاء مسجلين")
