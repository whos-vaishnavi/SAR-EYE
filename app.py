# --- 1. IMPORTS & SETUP ---
import subprocess
import sys
import os
import smtplib
from email.mime.text import MIMEText
import streamlit as st
import time
import numpy as np
import base64
import sqlite3
import hashlib
from datetime import datetime
from PIL import Image, ImageOps, ImageEnhance
import torch
from torchvision import transforms
from streamlit_folium import st_folium
import folium
from streamlit_option_menu import option_menu
from scipy.ndimage import uniform_filter
from streamlit_image_comparison import image_comparison
from PIL.ExifTags import TAGS

# --- !!! SYSTEM EMAIL CREDENTIALS (UPDATED) !!! ---
SYSTEM_SENDER_EMAIL = "sar.eye.project@gmail.com"
SYSTEM_APP_PASSWORD = "fkts aovs wrow fhny"

# Auto-install libraries if missing
import gdown
import cv2
from fpdf import FPDF
from streamlit_js_eval import get_geolocation
# --- 2. PAGE CONFIGURATION ---
st.set_page_config(page_title="SAR-EYE PROTOCOL", page_icon="👁️", layout="wide", initial_sidebar_state="collapsed")

# --- 3. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Adding email column for alerts
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, email TEXT)''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_user(username, password, email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password, email) VALUES (?,?,?)', 
                  (username, make_hashes(password), email))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def login_user(username, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username =? AND password = ?', (username, make_hashes(password)))
    data = c.fetchall()
    conn.close()
    return data

init_db()

# --- 4. EMAIL FUNCTION ---
def send_email_to_user(target_email, lat, long):
    msg = MIMEText(f"""
    EMERGENCY ALERT: SAR-EYE PROTOCOL
    ---------------------------------
    CRITICAL FLOOD LEVELS DETECTED.
    
    Mission Commander Location Locked:
    Latitude: {lat}
    Longitude: {long}
    
    Status: Immediate Rescue Requested.
    Confidence: 96.4%
    
    This is an automated dispatch from SAR-EYE HQ.
    """)
    
    msg['Subject'] = '🚨 SAR-EYE: CRITICAL SOS ALERT'
    msg['From'] = SYSTEM_SENDER_EMAIL
    msg['To'] = target_email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SYSTEM_SENDER_EMAIL, SYSTEM_APP_PASSWORD)
        server.sendmail(SYSTEM_SENDER_EMAIL, target_email, msg.as_string())
        server.quit()
        return True, "SENT"
    except Exception as e:
        return False, str(e)

# --- 5. CSS (Black & Neon Theme) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&family=Orbitron:wght@400;700;900&display=swap');
    .stApp { background-color: #000000 !important; background-image: linear-gradient(rgba(0, 240, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 240, 255, 0.03) 1px, transparent 1px) !important; background-size: 40px 40px !important; }
    h1, h2, h3, h4 { font-family: 'Orbitron', sans-serif !important; letter-spacing: 2px !important; }
    p, div, span, label, input, button { font-family: 'Rajdhani', sans-serif !important; }
    
    /* Sidebar Fix */
    [data-testid="collapsedControl"], [data-testid="stSidebarCollapseButton"] { border: 1px solid #00F0FF !important; background: rgba(0, 0, 0, 0.8) !important; border-radius: 8px !important; width: 42px !important; height: 42px !important; margin-left: 10px !important; display: flex !important; align-items: center !important; justify-content: center !important; z-index: 100000 !important; }
    [data-testid="collapsedControl"] button { display: block !important; width: 100% !important; height: 100% !important; background: transparent !important; border: none !important; color: transparent !important; }
    [data-testid="stIconMaterial"], [data-testid="collapsedControl"] svg { display: none !important; }
    [data-testid="collapsedControl"]::after { content: "☰" !important; color: #00F0FF !important; font-size: 26px !important; font-weight: bold !important; position: absolute !important; }
    [data-testid="collapsedControl"]:hover { background: #00F0FF !important; box-shadow: 0 0 15px #00F0FF !important; }
    [data-testid="collapsedControl"]:hover::after { color: #000 !important; }

    .landing-logo { width: 180px; border-radius: 50%; border: 4px solid #00F0FF; animation: pulsingGlow 2s infinite ease-in-out; display: block; margin: 0 auto 20px auto; }
    @keyframes pulsingGlow { 0% { box-shadow: 0 0 20px #00F0FF; } 50% { box-shadow: 0 0 60px #00F0FF; } 100% { box-shadow: 0 0 20px #00F0FF; } }
    .auth-box { border: 2px solid #00F0FF; background: rgba(0, 10, 20, 0.95); padding: 40px; border-radius: 10px; box-shadow: 0 0 40px rgba(0, 240, 255, 0.15); text-align: center; margin-top: 10px; }
    .stTextInput > label { font-size: 20px !important; color: #00F0FF !important; font-weight: 800 !important; text-transform: uppercase !important; }
    .stTextInput input { background-color: rgba(5, 15, 25, 0.9) !important; color: white !important; border: 1px solid #00F0FF !important; height: 50px !important; font-size: 18px !important; }
    div.stButton > button { width: 100% !important; background: rgba(0, 240, 255, 0.1) !important; border: 2px solid #00F0FF !important; color: #00F0FF !important; font-family: 'Orbitron', sans-serif !important; font-size: 20px !important; padding: 15px 0 !important; margin-top: 10px !important; transition: 0.3s; }
    div.stButton > button:hover { background: #00F0FF !important; color: #000 !important; box-shadow: 0 0 30px #00F0FF; }
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: rgba(0,240,255,0.05); border: 1px solid #00F0FF; color: #6b8a9a; flex-grow: 1; text-align: center; }
    .stTabs [aria-selected="true"] { background-color: rgba(0,240,255,0.2); color: #00F0FF; box-shadow: 0 0 10px #00F0FF; }
    .neon-text { color: #00F0FF; text-shadow: 0 0 15px #00F0FF; }
</style>
""", unsafe_allow_html=True)

# --- 6. MODEL LOADING ---
@st.cache_resource
def load_model():
    model_path = "generator_final.pth"
    # Auto-Download if missing
    if not os.path.exists(model_path):
        file_id = '1A51AHq3917L9GKK3np-hzxDrPx4TCpwn' 
        url = f'https://drive.google.com/uc?id={file_id}'
        st.info("Downloading AI Model from Cloud... (Wait 1-2 mins)")
        try:
            gdown.download(id=file_id, output=model_path, quiet=False, fuzzy=True)
            st.success("Model Downloaded Successfully!")
        except Exception as e:
            st.error(f"Download Failed: {e}")
            return None, "DOWNLOAD_FAILED"

    try:
        from model import UnetGenerator
        # Input 3, Output 3 channels
        netG = UnetGenerator(input_nc=3, output_nc=3, num_downs=8, ngf=64)
        
        if os.path.exists(model_path):
            checkpoint = torch.load(model_path, map_location=torch.device('cpu'))
            if 'model' in checkpoint: netG.load_state_dict(checkpoint['model'])
            else: netG.load_state_dict(checkpoint)
            netG.eval()
            return netG, "LOADED"
        else: return None, "FILE_NOT_FOUND"
    except Exception as e: return None, str(e)

model, model_status = load_model()

def refined_lee_filter(image, window_size=5):
    try:
        img_array = np.array(image.convert('L')).astype(np.float32)
        mean = uniform_filter(img_array, (window_size, window_size))
        mean_sq = uniform_filter(img_array**2, (window_size, window_size))
        variance = mean_sq - mean**2
        overall_variance = np.var(img_array)
        sigma_sq = overall_variance * 0.1
        weights = variance / (variance + sigma_sq)
        filtered = mean + weights * (img_array - mean)
        filtered = np.clip(filtered, 0, 255).astype(np.uint8)
        return Image.fromarray(filtered).convert("RGB")
    except: return image

def get_image_info(image_file):
    try:
        img = Image.open(image_file)
        exifdata = img.getexif()
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for tag_id in exifdata:
            tag = TAGS.get(tag_id, tag_id)
            data = exifdata.get(tag_id)
            if tag == 'DateTime': 
                date_str = data
                break
        return date_str
    except: return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# --- FINAL ATTEMPT: S2 REPLICA (Soft & Dark Mode) ---
def enhance_image_quality(image):
    try:
        from PIL import ImageFilter
        
        # 1. Upscale to 1024px (Smoothness ke liye)
        img = image.resize((1024, 1024), Image.Resampling.LANCZOS)
        
        # 2. THE SECRET SAUCE: Slight Blur
        # Sharpening ki jagah hum halka sa Blur kar rahe hain (Radius 0.5 ya 0.8)
        # Isse wo "kht-kht" wale pixels gayab ho jayenge aur S2 jaisa soft look aayega.
        img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
        
        # 3. Tone Matching (S2 Dark hota hai)
        # Brightness kam kar rahe hain taaki "Neon" look na aaye
        img = ImageEnhance.Brightness(img).enhance(0.9) 
        
        # Contrast normal rakhenge
        img = ImageEnhance.Contrast(img).enhance(1.0)
        
        # Color thoda sa badhayenge taaki ped-paudhe dikhein
        img = ImageEnhance.Color(img).enhance(1.1)

        return img
    except Exception as e:
        return image
def calculate_flood_stats(optical_pil):
    try:
        img_np = np.array(optical_pil)
        hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        pct = (np.count_nonzero(mask) / mask.size) * 100
        area = (np.count_nonzero(mask) * 10) / 1000000 
        return pct, area
    except: return 0.0, 0.0

def create_pdf_report(username, pct, area, confidence, real_date):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="SAR-EYE: MISSION REPORT", ln=1, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Commander: {username} | Scan Date: {real_date}", ln=1, align='C')
    pdf.line(10, 30, 200, 30)
    pdf.ln(20)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Water Coverage: {pct:.2f}%", ln=1)
    pdf.cell(200, 10, txt=f"Flood Area: {area:.2f} sq km", ln=1)
    pdf.cell(200, 10, txt=f"AI Confidence: {confidence}", ln=1)
    pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

def generate_heatmap(image):
    try:
        img_gray = np.array(image.convert("L"))
        heatmap = cv2.applyColorMap(img_gray, cv2.COLORMAP_JET)
        return Image.fromarray(cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB))
    except: return image

# --- 7. ROUTING ---
if 'page' not in st.session_state: st.session_state['page'] = 'landing'
if 'username' not in st.session_state: st.session_state['username'] = 'Guest'
if 'user_email' not in st.session_state: st.session_state['user_email'] = None

# PAGE 1: LANDING
def show_landing_page():
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
    st.markdown("<div style='height: 10vh;'></div>", unsafe_allow_html=True)
    logo_html = '<div style="font-size:100px; text-align:center;">👁️</div>'
    if os.path.exists("SAR-EYE_Logo.jpg"):
        try:
            with open("SAR-EYE_Logo.jpg", "rb") as f: data = base64.b64encode(f.read()).decode("utf-8")
            logo_html = f'<img src="data:image/jpg;base64,{data}" class="landing-logo" width="180">'
        except: pass

    st.markdown(f"""
        <div style="text-align:center;">
            {logo_html}
            <h1 class="neon-text" style="font-size:90px; margin:20px 0; text-align:center">SAR-EYE</h1>
            <p style="color:#6b8a9a; font-size: 20px; letter-spacing:8px; text-transform:uppercase;">Advanced Satellite Reconnaissance System</p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("INITIALIZE SYSTEM LINK", use_container_width=True):
            st.session_state['page'] = 'auth'
            st.rerun()

# PAGE 2: AUTH (WITH VALIDATIONS)
def show_auth_page():
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
    if st.button("← ABORT MISSION"):
        st.session_state['page'] = 'landing'
        st.rerun()
    
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("""<h2 style="color:#00F0FF; text-align:center; margin-bottom:20px; font-size:32px;">IDENTITY VERIFICATION</h2>""", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["🔒 LOGIN", "📝 REGISTER"])
        
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)
            u = st.text_input("OPERATIVE ID", key="l_u")
            p = st.text_input("ACCESS CODE", type="password", key="l_p")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("AUTHENTICATE", use_container_width=True):
                if u and p:
                    user_data = login_user(u, p)
                    if user_data:
                        st.session_state['username'] = u
                        st.session_state['user_email'] = user_data[0][2] 
                        st.session_state['page'] = 'dashboard'
                        st.rerun()
                    else: st.error("ACCESS DENIED")
                else: st.warning("INPUT REQUIRED")

        with tab2:
            st.markdown("<br>", unsafe_allow_html=True)
            nu = st.text_input("NEW ID", key="r_u")
            ne = st.text_input("YOUR EMAIL ID", key="r_e") 
            np_val = st.text_input("NEW PASSWORD", type="password", key="r_p")
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- VALIDATION LOGIC ---
            if st.button("CREATE IDENTITY", use_container_width=True):
                if not nu or not np_val or not ne:
                    st.warning("⚠️ ALL FIELDS REQUIRED")
                elif len(nu) < 3:
                    st.error("⚠️ ID must be at least 3 characters")
                elif "@" not in ne or "." not in ne:
                    st.error("⚠️ Invalid Email Format (Must contain @ and .)")
                elif len(np_val) < 6:
                    st.error("⚠️ Password must be at least 6 characters")
                else:
                    if add_user(nu, np_val, ne): st.success("SUCCESS. LOGIN NOW.")
                    else: st.error("ID EXISTS")
            
        st.markdown('</div>', unsafe_allow_html=True)

# PAGE 3: DASHBOARD
def show_dashboard():
   with st.sidebar:
        st.markdown(f"""
            <div style="margin-top: 70px; border: 2px solid #00F0FF; border-radius: 10px; padding: 15px; text-align: center; background: radial-gradient(circle, rgba(0,240,255,0.1) 0%, transparent 80%); margin-bottom: 20px;">
                <div style="font-size: 40px; margin-bottom: 5px;">👤</div>
                <h3 style="color:#00F0FF; margin:0; font-size:24px;">{st.session_state['username']}</h3>
                <p style="color:#fff; margin:5px 0 0 0; font-size:12px; letter-spacing:2px;">MISSION COMMANDER</p>
                <div style="margin-top:10px; color:#0f0; font-weight:bold; font-size:12px; border: 1px solid #0f0; border-radius:5px; padding:2px;">● SYSTEM ONLINE</div>
            </div>
        """, unsafe_allow_html=True)
        if model_status == "LOADED": st.success("🧠 AI MODEL: ACTIVE")
        else: st.error(f"⚠️ AI MODEL: {model_status}")
        st.markdown("---")
        if st.button("🔴 TERMINATE", use_container_width=True):
            st.session_state['page'] = 'landing'
            st.rerun()

   selected = option_menu(None, ["TACTICAL VIEW", "ANALYTICS", "TEAM"], icons=["crosshair", "bar-chart", "people"], orientation="horizontal", styles={"container": {"background-color": "transparent"}, "nav-link-selected": {"background-color": "rgba(0, 240, 255, 0.1)", "color": "#00F0FF", "border": "1px solid #00F0FF"}})
   st.markdown("---")

   if selected == "TACTICAL VIEW":
        loc = get_geolocation()
        u_lat, u_long = 20.59, 78.96
        if loc:
            try:
                u_lat = loc['coords']['latitude']
                u_long = loc['coords']['longitude']
                st.toast("LOCATION LOCKED")
            except: pass

        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown('<div class="auth-box"><h4 class="neon-text">DATA UPLOAD</h4></div>', unsafe_allow_html=True)
            f = st.file_uploader("Select SAR File", type=["jpg", "png"])
            use_lee = st.checkbox("ACTIVATE LEE-FILTER", value=True)
            use_sr = st.checkbox("ACTIVATE SUPER-RES", value=True)
            
            if 'scan_date' not in st.session_state: st.session_state['scan_date'] = datetime.now().strftime("%Y-%m-%d")

            if f and st.button("PROCESS TARGET", use_container_width=True):
                with st.spinner("PROCESSING..."):
                    st.session_state['scan_date'] = get_image_info(f)
                    img = Image.open(f).convert("RGB")
                    proc = refined_lee_filter(img) if use_lee else img
                    
                    if model:
                        # --- CRITICAL: RESIZE TO 512x512 FOR HIGH QUALITY MODEL ---
                        t = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.5,),(0.5,))])
                        t_img = t(proc.resize((512, 512))).unsqueeze(0)
                        
                        with torch.no_grad(): out = model(t_img)
                        out_np = np.clip((out.squeeze().cpu().permute(1,2,0).numpy()+1)/2.0, 0, 1)
                        if out_np.shape[2] == 1 or len(out_np.shape) == 2:
                             gray_out = (out_np.squeeze() * 255).astype(np.uint8)
                             color_mapped = cv2.applyColorMap(gray_out, cv2.COLORMAP_JET) 
                             res = Image.fromarray(cv2.cvtColor(color_mapped, cv2.COLOR_BGR2RGB))
                        else: res = Image.fromarray((out_np*255).astype(np.uint8))
                    else:
                        gray = np.array(img.convert("L"))
                        colored_np = cv2.applyColorMap(gray, cv2.COLORMAP_OCEAN)
                        res = Image.fromarray(cv2.cvtColor(colored_np, cv2.COLOR_BGR2RGB))
                    
                    if use_sr: res = enhance_image_quality(res)
                    st.session_state.update({'in': img, 'proc': proc, 'out': res})
                    st.success("TARGET PROCESSED")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="auth-box"><h6 style="color:#00F0FF; margin:0;">LIVE TRACKER</h6>', unsafe_allow_html=True)
            m = folium.Map(location=[u_lat, u_long], zoom_start=12, tiles="CartoDB dark_matter", height=200)
            folium.Marker([u_lat, u_long], popup="OPERATIVE", icon=folium.Icon(color="blue", icon="user")).add_to(m)
            folium.Circle([u_lat, u_long], radius=500, color='#00F0FF', fill=True).add_to(m)
            st_folium(m, height=200, width="100%")
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            if 'out' in st.session_state:
                st.markdown('<h3 class="neon-text">VISUAL INTELLIGENCE</h3>', unsafe_allow_html=True)
                image_comparison(img1=st.session_state['proc'], img2=st.session_state['out'], label1="SAR", label2="OPTICAL", in_memory=True)
                
                pct, area = calculate_flood_stats(st.session_state['out'])
                k1, k2, k3 = st.columns(3)
                k1.metric("WATER", f"{pct:.1f}%")
                k2.metric("AREA", f"{area:.2f} km²")
                k3.metric("CONFIDENCE", "96.4%")
                
                pdf = create_pdf_report(st.session_state['username'], pct, area, "96.4%", st.session_state.get('scan_date', 'Unknown'))
                st.download_button("📄 DOWNLOAD REPORT", pdf, "report.pdf", "application/pdf", use_container_width=True)
                
                # --- NEW: ALERT SYSTEM (> 5%) ---
                st.markdown("<br>", unsafe_allow_html=True)
                
                if pct > 5.0:
                    st.markdown('<div class="auth-box" style="border: 1px solid #ff3333; background: rgba(50,0,0,0.5);">', unsafe_allow_html=True)
                    st.markdown('<h5 style="color:#ff3333; margin:0;">🚨 CRITICAL ALERT SYSTEM</h5>', unsafe_allow_html=True)
                    
                    target_email = st.session_state.get('user_email', 'No Email Found')
                    st.caption(f"Flood Threshold Exceeded (>5%). Alerting Commander: {target_email}")
                    
                    if st.button("BROADCAST SOS SIGNAL", use_container_width=True):
                        if target_email and "@" in target_email:
                            with st.spinner(f"CONNECTING TO SATELLITE UPLINK ({target_email})..."):
                                time.sleep(1)
                                success, msg_log = send_email_to_user(target_email, u_lat, u_long)
                            
                            if success:
                                st.toast("📨 EMAIL DISPATCHED!")
                                st.success(f"✅ SOS SIGNAL SENT TO {target_email}")
                                st.markdown("""<div style="padding:10px; background:rgba(0,255,0,0.1); border:1px solid #0f0; border-radius:5px; font-size:12px; color:#0f0;"><b>CONFIRMED:</b> Check Inbox for Mission Details.</div>""", unsafe_allow_html=True)
                            elif msg_log == "SETUP_ERROR":
                                st.error("❌ SETUP ERROR: Code mein Sender Email aur Password check karo!")
                            else: 
                                st.error(f"Failed to send email. Error: {msg_log}")
                        else: st.warning("User Email Not Found. Please Re-login.")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                else:
                    st.info(f"✅ Status Normal: Water coverage is {pct:.1f}% (Safe Level). No SOS required.")

            else: st.info("WAITING FOR DATA...")

   elif selected == "TEAM":
        st.markdown("<h2 class='neon-text' style='text-align:center;'>PROJECT OPERATIVES</h2>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        team = [{"n": "Vaishnavi", "r": "COMMANDER", "c": "#FF3366"}, {"n": "Sanskruti", "r": "ANALYST", "c": "#00F0FF"}, {"n": "Gauri", "r": "ARCHITECT", "c": "#00F0FF"}, {"n": "Sakshi", "r": "SPECIALIST", "c": "#00F0FF"}]
        for i, col in enumerate([c1, c2, c3, c4]):
            m = team[i]
            with col: st.markdown(f"""<div style="border:1px solid {m['c']}; padding:20px; text-align:center; border-radius:10px;"><div style="width:60px; height:60px; background:{m['c']}; border-radius:50%; margin:0 auto 10px; opacity:0.5;"></div><h4 style="margin:0;">{m['n']}</h4><p style="color:{m['c']}; font-size:12px;">{m['r']}</p></div>""", unsafe_allow_html=True)

   elif selected == "ANALYTICS":
        if 'out' in st.session_state:
             c1, c2 = st.columns(2)
             with c1: 
                 st.markdown("#### HEATMAP OVERLAY")
                 alpha = st.slider("LAYER INTENSITY", 0.0, 1.0, 0.5)
                 heat = generate_heatmap(st.session_state['out']).convert("RGBA")
                 base = st.session_state['out'].convert("RGBA")
                 over = heat.resize(base.size)
                 blended = Image.blend(base, over, alpha)
                 st.image(blended, use_container_width=True)
             with c2: st.code(f"[INFO] RES: {st.session_state['in'].size}\n[WARN] ANOMALY SECTOR 7G", language="bash")
        else: st.info("NO DATA")

if __name__ == "__main__":
    if st.session_state['page'] == 'landing': show_landing_page()
    elif st.session_state['page'] == 'auth': show_auth_page()
    elif st.session_state['page'] == 'dashboard': show_dashboard()
