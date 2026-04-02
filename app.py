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
from supabase import create_client, Client
import io

# ==================== إعدادات Supabase ====================
SUPABASE_URL = "https://ahrhizgfcqmefcdjzskm.supabase.co"
SUPABASE_KEY = "sb_publishable_YaeiIPPa7mOt2az35yKKkQ_uKMpDACa"  # anon key

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==================== إعدادات الصفحة ====================
st.set_page_config(page_title="Expert 2M - Management System", layout="wide")

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
    </style>
    """, unsafe_allow_html=True)

# ==================== مجلدات مؤقتة للملفات ====================
UPLOAD_FOLDER = "uploaded_reports"
BACKUP_FOLDER = "backups"

for folder in [UPLOAD_FOLDER, BACKUP_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# ==================== دوال Supabase ====================
def get_repairs():
    response = supabase.table("repairs").select("*").order("visit_date", desc=True).execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

def add_repair(data):
    response = supabase.table("repairs").insert(data).execute()
    return response.data

def update_repair(repair_id, data):
    response = supabase.table("repairs").update(data).eq("id", repair_id).execute()
    return response.data

def delete_repair(repair_id):
    response = supabase.table("repairs").delete().eq("id", repair_id).execute()
    return response.data

def get_staff():
    response = supabase.table("staff").select("*").order("name").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

def add_staff(name):
    try:
        response = supabase.table("staff").insert({"name": name}).execute()
        return True, "تم إضافة الفني بنجاح"
    except Exception as e:
        return False, str(e)

def delete_staff(staff_id):
    response = supabase.table("staff").delete().eq("id", staff_id).execute()
    return response.data

def get_customers():
    response = supabase.table("customers").select("*").order("total_visits", desc=True).execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

def add_or_update_customer(name, phone, phone2, address, governorate):
    existing = supabase.table("customers").select("*").eq("phone", phone).execute()
    
    if existing.data:
        customer = existing.data[0]
        supabase.table("customers").update({
            "name": name, "phone2": phone2, "address": address, 
            "governorate": governorate, "total_visits": customer['total_visits'] + 1
        }).eq("id", customer['id']).execute()
    else:
        supabase.table("customers").insert({
            "name": name, "phone": phone, "phone2": phone2,
            "address": address, "governorate": governorate,
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "total_visits": 1, "total_cost": 0
        }).execute()

def update_customer_cost(phone, cost):
    try:
        cost_val = float(cost) if cost else 0
        existing = supabase.table("customers").select("*").eq("phone", phone).execute()
        if existing.data:
            customer = existing.data[0]
            supabase.table("customers").update({
                "total_cost": customer['total_cost'] + cost_val
            }).eq("id", customer['id']).execute()
    except:
        pass

def get_customer_history(phone):
    response = supabase.table("repairs").select("*").eq("phone", phone).order("visit_date", desc=True).execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

def get_inventory():
    response = supabase.table("inventory").select("*").order("part_name").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

def add_inventory_item(part_name, part_code, quantity, min_quantity, price, unit, supplier):
    try:
        supabase.table("inventory").insert({
            "part_name": part_name, "part_code": part_code,
            "quantity": quantity, "min_quantity": min_quantity,
            "price": price, "unit": unit, "supplier": supplier,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
        return True, "تم إضافة القطعة بنجاح"
    except Exception as e:
        return False, str(e)

def update_inventory_quantity(part_id, quantity_change):
    inventory = get_inventory()
    part = inventory[inventory['id'] == part_id]
    if not part.empty:
        new_quantity = part.iloc[0]['quantity'] + quantity_change
        supabase.table("inventory").update({
            "quantity": new_quantity,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).eq("id", part_id).execute()
        
        if new_quantity <= part.iloc[0]['min_quantity']:
            add_notification(f"تنبيه: مخزون منخفض - {part.iloc[0]['part_name']}",
                           f"الكمية المتبقية: {new_quantity}", "warning")

def delete_inventory_item(part_id):
    supabase.table("inventory").delete().eq("id", part_id).execute()

def use_inventory_part(repair_id, part_code, quantity, notes=""):
    inventory = get_inventory()
    part = inventory[inventory['part_code'] == part_code]
    
    if part.empty:
        return False, "القطعة غير موجودة"
    
    if part.iloc[0]['quantity'] < quantity:
        return False, f"الكمية غير متوفرة. المتوفر: {part.iloc[0]['quantity']}"
    
    supabase.table("inventory_usage").insert({
        "repair_id": repair_id, "part_id": part.iloc[0]['id'],
        "quantity": quantity, "usage_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "notes": notes
    }).execute()
    
    new_quantity = part.iloc[0]['quantity'] - quantity
    supabase.table("inventory").update({
        "quantity": new_quantity,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }).eq("id", part.iloc[0]['id']).execute()
    
    return True, "تم تسجيل الاستخدام بنجاح"

def get_low_stock_items():
    inventory = get_inventory()
    if not inventory.empty:
        return inventory[inventory['quantity'] <= inventory['min_quantity']]
    return pd.DataFrame()

def get_notifications():
    response = supabase.table("notifications").select("*").eq("is_read", 0).order("created_date", desc=True).execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()

def add_notification(title, message, type="info"):
    supabase.table("notifications").insert({
        "title": title, "message": message, "type": type,
        "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_read": 0
    }).execute()

def mark_notification_read(notif_id):
    supabase.table("notifications").update({"is_read": 1}).eq("id", notif_id).execute()

def delete_notification(notif_id):
    supabase.table("notifications").delete().eq("id", notif_id).execute()

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
    repairs_df = get_repairs()
    customers_df = get_customers()
    inventory_df = get_inventory()
    
    today = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%Y-%m")
    
    total = len(repairs_df)
    today_count = len(repairs_df[repairs_df['visit_date'] == today]) if not repairs_df.empty else 0
    month_count = len(repairs_df[repairs_df['visit_date'].str.startswith(current_month)]) if not repairs_df.empty else 0
    
    total_revenue = 0
    if not repairs_df.empty and 'cost' in repairs_df.columns:
        try:
            repairs_df['cost_clean'] = repairs_df['cost'].astype(str).str.replace('ج.م', '').str.replace('EGP', '').str.replace(' ', '').str.replace(',', '')
            repairs_df['cost_clean'] = pd.to_numeric(repairs_df['cost_clean'], errors='coerce').fillna(0)
            total_revenue = repairs_df['cost_clean'].sum()
        except:
            total_revenue = 0
    
    customers_count = len(customers_df)
    low_stock = len(inventory_df[inventory_df['quantity'] <= inventory_df['min_quantity']]) if not inventory_df.empty else 0
    
    if not repairs_df.empty and 'tech_name' in repairs_df.columns:
        tech_counts = repairs_df[repairs_df['tech_name'] != '']['tech_name'].value_counts().head(5)
        top_tech = tech_counts.to_dict()
    else:
        top_tech = {}
    
    if not repairs_df.empty and 'governorate' in repairs_df.columns:
        gov_counts = repairs_df[repairs_df['governorate'] != '']['governorate'].value_counts().head(5)
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
    
    repairs_df = get_repairs()
    if not repairs_df.empty:
        repairs_df['visit_date'] = pd.to_datetime(repairs_df['visit_date'])
        daily_counts = repairs_df.groupby(repairs_df['visit_date'].dt.date).size().reset_index(name='count')
        daily_counts.columns = ['التاريخ', 'عدد المعاينات']
        
        fig = px.bar(daily_counts, x='التاريخ', y='عدد المعاينات', title='المعاينات اليومية', color_discrete_sequence=['#ff4b4b'])
        fig.update_layout(plot_bgcolor='#1a1c23', paper_bgcolor='#1a1c23', font_color='white')
        st.plotly_chart(fig, use_container_width=True)
    
    col7, col8 = st.columns(2)
    
    with col7:
        st.markdown("### 👨‍🔧 أكثر الفنيين شغلاً")
        if stats['top_tech']:
            max_val = max(stats['top_tech'].values()) if stats['top_tech'].values() else 1
            for name, count in list(stats['top_tech'].items())[:5]:
                st.progress(min(count / max_val, 1.0))
                st.write(f"**{name}**: {count} معاينة")
        else:
            st.info("لا توجد بيانات كافية")
    
    with col8:
        st.markdown("### 📍 أكثر المحافظات")
        if stats['top_gov']:
            max_val = max(stats['top_gov'].values()) if stats['top_gov'].values() else 1
            for name, count in list(stats['top_gov'].items())[:5]:
                st.progress(min(count / max_val, 1.0))
                st.write(f"**{name}**: {count} معاينة")
        else:
            st.info("لا توجد بيانات كافية")
    
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
    unread_notifs = get_notifications()
    if not unread_notifs.empty:
        with st.expander(f"🔔 إشعارات جديدة ({len(unread_notifs)})"):
            for _, notif in unread_notifs.iterrows():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.info(f"**{notif['title']}**\n\n{notif['message']}")
                with col2:
                    if st.button("🗑️", key=f"del_{notif['id']}"):
                        delete_notification(notif['id'])
                        st.rerun()
                if st.button("تحديد كمقروء", key=f"read_{notif['id']}"):
                    mark_notification_read(notif['id'])
                    st.rerun()
    
    st.markdown("---")
    st.markdown("### 💾 حفظ البيانات")
    st.info("البيانات محفوظة في Supabase (سحابياً)")
    
    if st.button("🚪 تسجيل خروج", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ==================== التبويبات ====================
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 لوحة التحكم", "➕ تسجيل معاينة جديدة", "📊 سجل المعاينات",
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
            new_staff = st.text_input("اسم الفني الجديد")
            if st.form_submit_button("➕ إضافة فني"):
                if new_staff:
                    success, msg = add_staff(new_staff)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("برجاء كتابة اسم")
    
    with col_f2:
        staff_df = get_staff()
        if not staff_df.empty:
            st.write("### قائمة الفنيين")
            for _, row in staff_df.iterrows():
                c_name, c_del = st.columns([3, 1])
                c_name.write(row['name'])
                if c_del.button("🗑️ حذف", key=f"del_staff_{row['id']}"):
                    delete_staff(row['id'])
                    st.rerun()
        else:
            st.info("لا يوجد فنيين مسجلين")

# جلب أسماء الفنيين للقوائم المنسدلة
staff_df = get_staff()
staff_names = ["لم يتم التحديد"] + staff_df['name'].tolist() if not staff_df.empty else ["لم يتم التحديد"]

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
        
        # اختيار الفني
        tech_name = st.selectbox("اسم الفني", staff_names)
        
        # استخدام قطع الغيار
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
        
        if st.form_submit_button("💾 حفظ البيانات النهائية"):
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
                
                # إضافة المعاينة إلى Supabase
                repair_data = {
                    "client_name": name, "phone": phone, "phone2": phone2,
                    "visit_date": str(date_v), "governorate": gov, "address": addr,
                    "report": rep, "file_name": file_name, "cost": cost,
                    "tech_name": tech_name, "assistant_name": "",
                    "notes": "", "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                result = add_repair(repair_data)
                
                if result:
                    repair_id = result[0]['id'] if result else None
                    
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
                    
                    st.success("✅ تم الحفظ بنجاح!")
                    st.session_state.form_counter += 1
                    st.rerun()
                else:
                    st.error("❌ حدث خطأ في حفظ البيانات")

# ==================== تبويب إدارة المخزون ====================
with tab4:
    st.subheader("📦 إدارة المخزون (قطع الغيار)")
    
    tabs_inv = st.tabs(["➕ إضافة قطعة جديدة", "📋 قائمة المخزون", "⚠️ مخزون منخفض"])
    
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
            
            if st.form_submit_button("➕ إضافة قطعة"):
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
                if st.button("تحديث الكمية"):
                    part_code = selected_part.split("(")[1].split(")")[0]
                    part_id = inventory_df[inventory_df['part_code'] == part_code]['id'].values[0]
                    update_inventory_quantity(part_id, quantity_change)
                    st.success("تم تحديث الكمية")
                    st.rerun()
            with col4:
                if st.button("🗑️ حذف القطعة", type="secondary"):
                    part_code = selected_part.split("(")[1].split(")")[0]
                    part_id = inventory_df[inventory_df['part_code'] == part_code]['id'].values[0]
                    delete_inventory_item(part_id)
                    st.success("تم حذف القطعة")
                    st.rerun()
        else:
            st.info("لا توجد قطع غيار في المخزون")
    
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
    
    repairs_df = get_repairs()
    
    if not repairs_df.empty:
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
        
        df = repairs_df.copy()
        
        if search_query:
            df = df[df['client_name'].str.contains(search_query, na=False, case=False)]
        if search_phone:
            df = df[df['phone'].str.contains(search_phone, na=False)]
        if start_date:
            df = df[pd.to_datetime(df['visit_date']) >= pd.to_datetime(start_date)]
        if end_date:
            df = df[pd.to_datetime(df['visit_date']) <= pd.to_datetime(end_date)]
        
        # إعادة تسمية الأعمدة للعرض
        if not df.empty:
            df_display = df.copy()
            df_display['العميل'] = df_display['client_name']
            df_display['التليفون'] = df_display['phone']
            df_display['تليفون 2'] = df_display['phone2'].fillna('')
            df_display['الفني'] = df_display['tech_name']
            df_display['التكلفة'] = df_display['cost']
            df_display['التاريخ'] = df_display['visit_date']
            df_display['المحافظة'] = df_display['governorate']
            df_display['العنوان'] = df_display['address']
            
            def make_wa_link(phone_num):
                if not phone_num or phone_num == "" or pd.isna(phone_num):
                    return "#"
                p = str(phone_num).strip()
                p = ''.join(filter(str.isdigit, p))
                if p:
                    num = p if p.startswith('2') else '2' + p
                    return f"https://wa.me/{num}"
                return "#"
            
            df_display['واتساب'] = df_display['phone'].apply(make_wa_link)
            
            st.write(f"🔎 تم العثور على {len(df_display)} سجل")
            
            df_display['التاريخ'] = pd.to_datetime(df_display['التاريخ'])
            unique_dates = df_display['التاريخ'].dt.date.unique()
            
            for date in unique_dates:
                st.markdown(f"### 📅 {date.strftime('%Y-%m-%d')}")
                df_day = df_display[df_display['التاريخ'].dt.date == date]
                
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
                    selected_id = df_day.iloc[selected_index]['id']
                    
                    st.divider()
                    st.subheader(f"🛠️ إجراءات التعديل: {df_day.iloc[selected_index]['العميل']}")
                    
                    row = df[df['id'] == selected_id].iloc[0]
                    
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
                                    
                                    update_repair(selected_id, {
                                        "client_name": u_name, "phone": u_phone, "phone2": u_phone2,
                                        "tech_name": u_tech, "cost": u_cost, "governorate": u_gov,
                                        "address": u_addr, "notes": u_notes, "visit_date": str(u_date),
                                        "file_name": file_name
                                    })
                                    
                                    add_or_update_customer(u_name, u_phone, u_phone2, u_addr, u_gov)
                                    update_customer_cost(u_phone, u_cost)
                                    
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
                                    delete_repair(selected_id)
                                    add_notification("تم مسح معاينة", f"تم مسح معاينة العميل {row['client_name']}", "warning")
                                    st.success("🗑️ تم المسح بنجاح!")
                                    st.rerun()
                    
                    st.markdown("---")
    else:
        st.info("لا توجد سجلات حالياً.")
