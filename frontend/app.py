import streamlit as st
import pandas as pd
import requests
import folium
import plotly.express as px
from streamlit_folium import st_folium
import streamlit.components.v1 as components
from pyvis.network import Network

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(
    page_title="SIH Anti-Cyber Fraud Command Console",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .stApp { background-color: #030206; color: #f3e8ff; font-family: 'Inter', system-ui, sans-serif; }
    div[data-baseweb="input"] { background-color: #0f0a1c !important; border: 1px solid #7e22ce !important; border-radius: 8px !important; color: #ffffff !important; }
    div[data-baseweb="select"] { background-color: #0f0a1c !important; border: 1px solid #7e22ce !important; border-radius: 8px !important; }
    .stWidgetLabel p, label p { color: #c084fc !important; font-size: 0.95rem !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: 800 !important; color: #c084fc !important; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #e9d5ff !important; }
    .main-header { background: #090514; border-left: 6px solid #a855f7; padding: 20px 24px; border-radius: 10px; margin-bottom: 24px; }
    .main-header h1 { margin: 0; font-size: 1.8rem; font-weight: 800; color: #ffffff; }
    .stButton>button { background: linear-gradient(135deg, #a855f7 0%, #7e22ce 100%) !important; color: #ffffff !important; font-weight: 700 !important; border-radius: 8px !important; }
    section[data-testid="stSidebar"] { background-color: #06030d; border-right: 1px solid #7e22ce; }
</style>
""", unsafe_allow_html=True)

# Initialize Session States
if "logged_in_user" not in st.session_state:
    st.session_state["logged_in_user"] = None
if "logged_in_role" not in st.session_state:
    st.session_state["logged_in_role"] = None
if "otp_sent" not in st.session_state:
    st.session_state["otp_sent"] = False
if "auth_email" not in st.session_state:
    st.session_state["auth_email"] = ""


def render_login():
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_mid, _ = st.columns([1, 2, 1])
    
    with col_mid:
        st.markdown("""
            <div style="text-align: center; margin-bottom: 24px;">
                <h1 style="font-size: 2.5rem; font-weight: 800; color: #c084fc; text-shadow: 0 0 18px rgba(168, 85, 247, 0.5);">
                    ⚡ SIH Cashout Tracker
                </h1>
                <p style="color: #a855f7; font-size: 1.05rem;">Supabase Real-Time OTP Verification</p>
            </div>
        """, unsafe_allow_html=True)

        portal = st.selectbox(
            "SELECT ACCESS PORTAL",
            ["Banker Admin", "Police Officer Admin", "Cyber Cell Admin", "Citizen User Portal"],
            key="login_portal_select"
        )

        email = st.text_input(
            "EMAIL ADDRESS",
            value=st.session_state["auth_email"],
            placeholder="officer@agency.gov.in or user@example.com",
            disabled=st.session_state["otp_sent"]
        )

        # Step 1: Send OTP
        if not st.session_state["otp_sent"]:
            if st.button("📲 SEND REAL-TIME OTP", use_container_width=True):
                if not email or "@" not in email:
                    st.warning("Please enter a valid email address.")
                else:
                    try:
                        res = requests.post(f"{API_BASE_URL}/auth/send-otp", json={"email": email})
                        if res.status_code == 200:
                            st.session_state["otp_sent"] = True
                            st.session_state["auth_email"] = email
                            st.success(f"OTP sent to {email}. Check your inbox!")
                            st.rerun()
                        else:
                            st.error(f"Error: {res.json().get('detail')}")
                    except Exception as err:
                        st.error(f"Failed to reach authentication server: {err}")

        # Step 2: Verify OTP
        else:
            otp_token = st.text_input("ENTER 6-DIGIT OTP", placeholder="123456")
            
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                if st.button("🔓 VERIFY & LOGIN", use_container_width=True):
                    if not otp_token:
                        st.warning("Please enter the OTP.")
                    else:
                        try:
                            role_mapped = portal.replace(" Portal", "")
                            res = requests.post(
                                f"{API_BASE_URL}/auth/verify-otp",
                                json={"email": email, "token": otp_token, "role": role_mapped}
                            )
                            if res.status_code == 200:
                                data = res.json()
                                st.session_state["logged_in_user"] = data["email"]
                                st.session_state["logged_in_role"] = data["role"]
                                st.success("Authentication successful!")
                                st.rerun()
                            else:
                                st.error("Invalid or expired OTP code.")
                        except Exception as err:
                            st.error(f"Verification error: {err}")

            with col_v2:
                if st.button("🔄 RESEND / CHANGE EMAIL", use_container_width=True):
                    st.session_state["otp_sent"] = False
                    st.rerun()


def render_sidebar():
    st.sidebar.markdown("<h2 style='color: #c084fc;'>⚙️ Control Console</h2>", unsafe_allow_html=True)
    st.sidebar.markdown(f"**Operator:** `{st.session_state['logged_in_user']}`")
    st.sidebar.markdown(f"**Role:** `{st.session_state['logged_in_role']}`")
    st.sidebar.divider()
    if st.sidebar.button("🚪 Terminate Session", use_container_width=True):
        st.session_state["logged_in_user"] = None
        st.session_state["logged_in_role"] = None
        st.session_state["otp_sent"] = False
        st.rerun()


def render_mule_graph():
    try:
        res = requests.get(f"{API_BASE_URL}/analytics/mule-network").json()
        net = Network(height="550px", width="100%", bgcolor="#030206", font_color="#ffffff", directed=True)
        group_colors = {"Victim": "#38bdf8", "Layer 1 Mule": "#c084fc", "Layer 2 Mule": "#a855f7", "Layer 3 Mule": "#ef4444", "Cashout ATM": "#10b981"}
        for n in res["nodes"]:
            net.add_node(n["id"], label=f"{n['id']}\n({n['group']})", color=group_colors.get(n["group"], "#9ca3af"), shape="dot", size=22)
        for e in res["edges"]:
            net.add_edge(e["source"], e["target"], title=e["label"], color="#a855f7", width=2)
        net.toggle_physics(True)
        net.save_graph("mule_graph.html")
        with open("mule_graph.html", "r", encoding="utf-8") as f:
            components.html(f.read(), height=570)
    except Exception as err:
        st.error(f"Failed to load Mule Network Graph: {err}")


def render_admin_dashboard(portal_title, portal_subtitle):
    render_sidebar()
    st.markdown(f'<div class="main-header"><h1>{portal_title}</h1><span style="color:#c084fc;">{portal_subtitle}</span></div>', unsafe_allow_html=True)
    try:
        hotspots = requests.get(f"{API_BASE_URL}/analytics/ai-hotspots").json().get("hotspots", [])
        complaints = requests.get(f"{API_BASE_URL}/complaints").json().get("complaints", [])
        df_hot = pd.DataFrame(hotspots)
        df_comp = pd.DataFrame(complaints)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Active Fraud Signals", f"{len(df_comp)}")
        m2.metric("Critical Risk Hotspots", f"{len(df_hot[df_hot['risk_level'] == 'CRITICAL'])}")
        m3.metric("Interceptable Volume", f"₹{df_comp['amount'].sum():,}")
        m4.metric("Monitored ATM Outlets", f"{df_hot['target_atm'].nunique()}")

        tab1, tab2, tab3 = st.tabs(["📍 Geospatial AI Heatmap", "🕸️ Mule Network Graph", "📋 Incident Ledger"])
        with tab1:
            m = folium.Map(location=[28.6139, 77.2090], zoom_start=11, tiles="CartoDB dark_matter")
            for _, row in df_hot.iterrows():
                color = "#a855f7" if row["risk_level"] == "CRITICAL" else "#38bdf8"
                folium.CircleMarker([row["lat"], row["lng"]], radius=11, color=color, fill=True, fill_color=color, fill_opacity=0.8).add_to(m)
            st_folium(m, width="100%", height=460)
        with tab2:
            render_mule_graph()
        with tab3:
            st.dataframe(df_comp[["complaint_id", "victim", "layer_1", "bank", "amount", "target_atm", "tx_velocity"]], use_container_width=True)
    except Exception as e:
        st.error(f"Backend API error: {e}")


def render_citizen():
    render_sidebar()
    st.markdown('<div class="main-header"><h1>📢 Citizen Cyber Crime Incident Reporting</h1></div>', unsafe_allow_html=True)
    with st.form("complaint_form", clear_on_submit=True):
        acc = st.text_input("VICTIM ACCOUNT NUMBER")
        amt = st.number_input("LOSS AMOUNT (₹)", min_value=1000, value=50000, step=5000)
        suspect = st.text_input("SUSPECT MULE ACCOUNT / UPI ID")
        bank = st.selectbox("DESTINATION BANK", ["SBI", "HDFC", "ICICI", "PNB", "Axis Bank"])
        if st.form_submit_button("🚨 SUBMIT COMPLAINT"):
            res = requests.post(f"{API_BASE_URL}/complaints", json={"victim_acc": acc, "amount": amt, "suspect_info": suspect, "bank_name": bank})
            if res.status_code == 200:
                st.success("Incident report logged successfully!")


# Router
role = st.session_state["logged_in_role"]
if role is None:
    render_login()
elif "Banker" in role:
    render_admin_dashboard("🏦 Banker Admin Fraud Control Portal", "Interbank Freeze & Real-Time OTP Access")
elif "Police" in role:
    render_admin_dashboard("🚓 Police Officer Dispatch Console", "Field Intelligence & Field Unit Interception")
elif "Cyber" in role:
    render_admin_dashboard("🛡️ Cyber Cell Command Intelligence", "Multi-Layered Mule Analysis Engine")
else:
    render_citizen()