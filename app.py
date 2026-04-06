import streamlit as st
import pandas as pd
from datetime import datetime
import os
import time
import math
import plotly.express as px

# ==================== إعدادات الصفحة والـ CSS (iOS Style) ====================
st.set_page_config(page_title="Expert 2m - System", layout="wide")

st.markdown("""
    <style>
    /* الخط والألوان العامة */
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; }
    
    /* ستايل الكروت الإحصائية */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        text-align: center;
        transition: transform 0.3s ease;
        margin-bottom: 15px;
    }
    .metric-card:hover { transform: translateY(-5px); border-color: #00b4d8; }
    .metric-card h3 { font-size: 0.9rem; color: #888; margin-bottom: 10px; }
    .metric-card h1 { font-size: 1.8rem; margin: 0; }

    /* تحسين شكل التبويبات (Tabs) */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e1e1e;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        color: white;
    }
    
    /* روابط الواتساب */
    .whatsapp-link {
        text-decoration: none;
        color: #25d366;
        font-weight: bold;
        border: 1px solid #25d366;
        padding: 2px 8px;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# ==================== دوال افتراضية (يجب ربطها بـ Supabase من الجزء الأول) ====================
# ملاحظة: استبدل هذه الدوال بدوال الاتصال الحقيقية بـ Supabase التي قمت ببرمجتها سابقاً
UPLOAD_FOLDER = "reports"

def check_password(): return True # مؤقت لغرض العرض
def get_repairs(): return pd.DataFrame() # استبدلها بـ Supabase query
def get_customers(): return pd.DataFrame() # استبدلها بـ Supabase query
def get_inventory(): return pd.DataFrame() # استبدلها بـ Supabase query
def get_staff(): return pd.DataFrame(columns=['id', 'اسم الفني'])
def get_low_stock_items(): return pd.DataFrame()
def get_notifications(): return pd.DataFrame()

# ==================== دوال الإحصائيات ====================
def get_dashboard_stats():
    repairs_df = get_repairs()
    customers_df = get_customers()
    
    today = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().strftime("%Y-%m")
    
    total = len(repairs_df)
    today_count = 0
    month_count = 0
    
    if not repairs_df.empty and 'تاريخ المعاينة' in repairs_df.columns:
        today_count = len(repairs_df[repairs_df['تاريخ المعاينة'] == today])
        month_count = len(repairs_df[repairs_df['تاريخ المعاينة'].str.startswith(current_month)])
    
    total_revenue = 0
    if not repairs_df.empty and 'التكلفة' in repairs_df.columns:
        try:
            repairs_df['cost_clean'] = repairs_df['التكلفة'].astype(str).str.replace('ج.م', '').str.replace('EGP', '').str.replace(' ', '').str.replace(',', '')
            repairs_df['cost_clean'] = pd.to_numeric(repairs_df['cost_clean'], errors='coerce').fillna(0)
            total_revenue = repairs_df['cost_clean'].sum()
        except: total_revenue = 0
    
    return {
        'total': total, 'today': today_count, 'month': month_count,
        'revenue': total_revenue, 'customers': len(customers_df),
        'low_stock': len(get_low_stock_items()),
        'status_counts': repairs_df['الحالة'].value_counts().to_dict() if not repairs_df.empty else {}
    }

def show_dashboard():
    stats = get_dashboard_stats()
    st.markdown("## 📊 لوحة التحكم والإحصائيات")
    
    # صف المؤشرات الرئيسي
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    metrics = [
        (m1, "📋 إجمالي المعاينات", stats['total'], "#00b4d8"),
        (m2, "📅 معاينات اليوم", stats['today'], "#48cae4"),
        (m3, "📆 هذا الشهر", stats['month'], "#90e0ef"),
        (m4, "💰 الإيرادات", f"{stats['revenue']:,.0f}", "#2ecc71"),
        (m5, "👥 العملاء", stats['customers'], "#f39c12"),
        (m6, "⚠️ مخزون منخفض", stats['low_stock'], "#e74c3c")
    ]
    for col, title, val, color in metrics:
        with col:
            st.markdown(f'<div class="metric-card"><h3>{title}</h3><h1 style="color:{color}">{val}</h1></div>', unsafe_allow_html=True)

    # الرسم البياني
    repairs_df = get_repairs()
    if not repairs_df.empty and 'تاريخ المعاينة' in repairs_df.columns:
        repairs_df['تاريخ المعاينة'] = pd.to_datetime(repairs_df['تاريخ المعاينة'])
        daily = repairs_df.groupby(repairs_df['تاريخ المعاينة'].dt.date).size().reset_index(name='count')
        fig = px.bar(daily, x='تاريخ المعاينة', y='count', title='المعاينات اليومية', color_discrete_sequence=['#00b4d8'])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='white')
        st.plotly_chart(fig, use_container_width=True)

# ==================== القوائم الثابتة والتحقق ====================
ALL_GOVS = ["القاهرة", "الجيزة", "الإسكندرية", "الدقهلية", "البحيرة", "القليوبية", "الغربية", "المنوفية", "الشرقية", "دمياط", "بورسعيد", "السويس", "الإسماعيلية", "كفر الشيخ", "الفيوم", "بني سويف", "المنيا", "أسيوط", "سوهاج", "قنا", "الأقصر", "أسوان"]
STATUS_OPTIONS = ["جديدة", "تمت", "مؤجلة"]
STATUS_STYLES = {"جديدة": "🟦 جديدة", "تمت": "🟩 تمت", "مؤجلة": "🟧 مؤجلة"}

def validate_phone(phone):
    if not phone: return True, ""
    p = str(phone).strip()
    if len(p) == 11 and p.startswith('01') and p.isdigit(): return True, ""
    return False, "رقم التليفون غير صحيح (يجب أن يكون 11 رقم يبدأ بـ 01)"

# ==================== الهيكل الرئيسي للتطبيق ====================
if not check_password(): st.stop()

# الجلسة (Session State) للأسماء
if 'user_name' not in st.session_state: st.session_state.user_name = "أحمد حسن"
if 'user_role' not in st.session_state: st.session_state.user_role = "Admin"

with st.sidebar:
    st.markdown(f"### 👤 مرحباً {st.session_state.user_name}")
    st.info(f"**الدور:** {st.session_state.user_role}")
    st.markdown("---")
    if st.button("🚪 تسجيل خروج"): st.stop()

# التبويبات الرئيسية
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 لوحة التحكم", "➕ تسجيل معاينة", "📋 سجل المعاينات", 
    "👨‍🔧 الفنيين", "📦 المخزون", "👤 العملاء"
])

# 1. لوحة التحكم
with tab0: show_dashboard()

# 2. تسجيل معاينة جديدة
with tab1:
    st.subheader("📝 إضافة بيانات عميل جديد")
    with st.form("add_repair_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("👤 اسم العميل")
            phone = st.text_input("📞 رقم التليفون الأول")
            cost = st.text_input("💰 التكلفة (EGP)")
        with c2:
            gov = st.selectbox("📍 المحافظة", ALL_GOVS)
            addr = st.text_input("🏠 العنوان بالتفصيل")
            date_v = st.date_input("📅 التاريخ", datetime.now())
        
        rep = st.text_area("📝 وصف العطل")
        tech_df = get_staff()
        tech_name = st.selectbox("👨‍🔧 اسم الفني", ["لم يتم التحديد"] + tech_df['اسم الفني'].tolist())
        
        if st.form_submit_button("💾 حفظ البيانات"):
            v1, msg = validate_phone(phone)
            if not name or not phone: st.error("⚠️ الاسم ورقم التليفون مطلوبان")
            elif not v1: st.error(msg)
            else:
                st.success(f"✅ تم حفظ معاينة العميل {name} بنجاح!")

# 3. سجل المعاينات
with tab2:
    st.subheader("📋 سجل المعاينات")
    repairs_df = get_repairs()
    if not repairs_df.empty:
        # نظام البحث (Search)
        s_col1, s_col2 = st.columns(2)
        with s_col1: search_n = st.text_input("🔍 ابحث بالاسم")
        with s_col2: search_p = st.text_input("📞 ابحث بالرقم")
        st.dataframe(repairs_df, use_container_width=True)
    else: st.info("📭 لا توجد سجلات حالياً")

# 4. إدارة الفنيين
with tab3:
    st.subheader("👥 إدارة الفنيين")
    col_add, col_list = st.columns([1, 2])
    with col_add:
        new_tech = st.text_input("اسم الفني الجديد")
        if st.button("➕ إضافة"): st.success("تمت الإضافة")
    with col_list:
        st.write("قائمة الفنيين المسجلين تظهر هنا")

# 5. إدارة المخزون
with tab4:
    st.subheader("📦 المخزون (قطع الغيار)")
    inv_df = get_inventory()
    if inv_df.empty: st.info("المخزون فارغ حالياً")
    else: st.dataframe(inv_df)

# 6. إدارة العملاء (الجزء الأخير الذي أرسلته)
with tab5:
    st.subheader("👤 إدارة العملاء")
    customers_df = get_customers()
    if not customers_df.empty:
        st.markdown("### 🔍 البحث عن عميل")
        search_phone = st.text_input("ابحث برقم التليفون للوصول للتاريخ المرضي", max_chars=11)
        
        if search_phone:
            customer = customers_df[customers_df['رقم التليفون'] == search_phone]
            if not customer.empty:
                st.markdown(f"### 👤 معلومات العميل: {customer.iloc[0]['الاسم']}")
                # عرض تفاصيل العميل والزيارات السابقة
                c_c1, c_c2 = st.columns(2)
                c_c1.write(f"**🏠 العنوان:** {customer.iloc[0]['العنوان']}")
                c_c2.write(f"**💰 إجمالي المصروف:** {customer.iloc[0]['إجمالي المصروف']} ج.م")
            else: st.warning("⚠️ لا يوجد عميل بهذا الرقم")
    else: st.info("📭 لا يوجد عملاء مسجلين حالياً")
