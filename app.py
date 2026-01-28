import streamlit as st
import pandas as pd
import os
import io
from fpdf import FPDF
from PIL import Image

# --- SEITEN KONFIGURATION ---
st.set_page_config(page_title="Fassadenbegrünung Profi-Planer", layout="wide")

# --- KUNDEN-DATENBANK ---
USERS = {
    "admin": "admin123",
    "demo": "gast",
    "architekt": "planer2024",
    "praktikant": "lern123"
}
GUESTS = ["demo", "praktikant"]

# --- AGGRESSIVES CSS (Tarnkappen-Modus) ---
st.markdown("""
<style>
    /* 1. OBERE LEISTE KOMPLETT WEG */
    header {visibility: hidden !important; display: none !important;}
    #MainMenu {visibility: hidden !important; display: none !important;}
    [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
    [data-testid="stDecoration"] {visibility: hidden !important; display: none !important;}
    
    /* 2. UNTERE LEISTE & LOGOS WEG */
    footer {visibility: hidden !important; display: none !important;}
    [data-testid="stFooter"] {visibility: hidden !important; display: none !important;}
    
    /* 3. KNALLHARTE METHODE GEGEN DAS GRÜNE ICON UNTEN RECHTS */
    .viewerBadge_container__1QSob {display: none !important;}
    div[class^="viewerBadge"] {display: none !important;}
    div[style*="position: fixed"][style*="bottom: 0px"] {display: none !important;}
    
    /* 4. WEISSE EINGABEFELDER ERZWINGEN */
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        caret-color: #000000 !important;
        border: 1px solid #ccc !important;
    }
    
    /* 5. GAST-BOX DESIGN */
    .guest-warning {
        padding: 10px;
        background-color: #ffeeba;
        color: #856404;
        border-radius: 5px;
        border: 1px solid #ffeeba;
        text-align: center;
    }
    
    /* 6. BUTTON DESIGN */
    button[kind="secondary"] {
        color: #ff4b4b !important;
        border-color: #ff4b4b !important;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNKTIONEN ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("pflanzen.csv", sep=";", dtype=str)
        return df
    except: return pd.DataFrame()

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Pflanzenauswahl')
    return output.getvalue()

def prepare_image_for_pdf(image_path, unique_id):
    try:
        if not os.path.exists(image_path): return None
        img = Image.open(image_path)
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == 'P': img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[3])
            img = bg
        else: img = img.convert("RGB")
        temp_path = f"temp_img_{unique_id}.jpg"
        img.save(temp_path, "JPEG", quality=90)
        return temp_path
    except: return None

def export_pdf(df_filtered):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    logo_path = "logo.png"
    if not os.path.exists(logo_path): logo_path = "1200x1200_1.png"
    if os.path.exists(logo_path):
        clean_logo = prepare_image_for_pdf(logo_path, "header_logo")
        if clean_logo:
            try:
                pdf.image(clean_logo, x=160, y=10, w=35)
                os.remove(clean_logo)
            except: pass
    pdf.set_font("Arial", "B", 16)
    pdf.set_y(20)
    pdf.cell(0, 10, txt="Pflanzenauswahl Fassadenbegrünung", ln=True, align='L')
    pdf.line(10, 32, 200, 32)
    pdf.ln(15)
    for index, row in df_filtered.iterrows():
        if pdf.get_y() > 220: pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.set_fill_color(240, 240, 240)
        name = str(row.get('Name', '')).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 8, txt=name, ln=True, fill=True)
        pdf.set_font("Arial", "I", 10)
        bot = str(row.get('Botanisch', '')).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 6, txt=bot, ln=True)
        pdf.ln(2)
        orig_bp = str(row.get("Bild_URL", "")).strip()
        img_size = 40; img_x = 10; img_y = pdf.get_y(); has_img = False; clean_path = None
        if len(orig_bp) > 4:
            clean_path = prepare_image_for_pdf(orig_bp, index)
            if clean_path:
                try:
                    pdf.image(clean_path, x=img_x, y=img_y, w=img_size); has_img = True
                except: pass
        if not has_img:
            pdf.set_fill_color(250, 250, 250); pdf.rect(img_x, img_y, img_size, img_size, 'F')
            pdf.set_xy(img_x, img_y + 18); pdf.set_font("Arial", size=8); pdf.cell(img_size, 5, "Kein Bild", align='C')
        if clean_path and os.path.exists(clean_path): os.remove(clean_path)
        text_x = 55; pdf.set_xy(text_x, img_y); pdf.set_font("Arial", size=10)
        kurz_infos = ["Standort", "Klettertyp", "Wasserbedarf", "Winterhaerte"]
        for k in kurz_infos:
            val = str(row.get(k, '-')).encode('latin-1', 'replace').decode('latin-1')
            lbl = k.replace("_", " ")
            pdf.set_font("Arial", "B", 10); pdf.cell(35, 5, f"{lbl}:", ln=False)
            pdf.set_font("Arial", "", 10); pdf.cell(0, 5, val, ln=True); pdf.set_x(text_x)
        pdf.set_y(max(pdf.get_y(), img_y + img_size + 5))
        desc = str(row.get('Beschreibung', '')).encode('latin-1', 'replace').decode('latin-1')
        if len(desc) > 3:
            pdf.set_font("Arial", "B", 10); pdf.cell(0, 5, "Beschreibung:", ln=True)
            pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 5, desc); pdf.ln(2)
        pdf.set_font("Arial", "B", 8); pdf.cell(0, 5, "Vollständige Daten:", ln=True)
        pdf.set_font("Arial", "", 8); all_details = ""
        exclude = ["Name", "Botanisch", "Bild_URL", "Beschreibung"] + kurz_infos
        for col in df_filtered.columns:
            if col not in exclude:
                val = str(row[col])
                if val != "nan" and val != "-":
                    val_c = val.encode('latin-1', 'replace').decode('latin-1')
                    all_details += f"[{col.replace('_',' ')}: {val_c}]  "
        pdf.multi_cell(0, 4, all_details); pdf.ln(3)
        pdf.set_draw_color(200, 200, 200); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.set_draw_color(0,0,0); pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

def reset_all_filters():
    st.session_state["f_standort"] = []
    st.session_state["f_typ"] = []
    st.session_state["f_immergruen"] = "Alle"
    st.session_state["f_insekten"] = False
    if "f_wasser" in st.session_state: st.session_state["f_wasser"] = []
    if "f_winter" in st.session_state: st.session_state["f_winter"] = []
    if "f_boden" in st.session_state: st.session_state["f_boden"] = []
    if "f_wuchs" in st.session_state: st.session_state["f_wuchs"] = []

# --- LOGIN ---
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["current_user"] = None 
    if not st.session_state["logged_in"]:
        st.markdown("## 🔒 Geschützter Bereich")
        st.info("Bitte melden Sie sich an.")
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            username = st.text_input("Benutzername")
            password = st.text_input("Passwort", type="password")
            if st.button("Anmelden", type="primary"):
                if username in USERS and USERS[username] == password:
                    st.session_state["logged_in"] = True
                    st.session_state["current_user"] = username 
                    st.rerun()
                else: st.error("Falsch")
        return False
    return True

# --- MAIN ---
def main():
    if not check_login(): return
    current_user = st.session_state.get("current_user", "Gast")
    
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        for f in ["logo.png", "1200x1200_1.png"]:
            if os.path.exists(f): st.image(f, use_container_width=True); break
    with col_title:
        st.title("🌿 Profi-Datenbank"); st.markdown("### Fassadenbegrünung")
    st.divider()
    
    df = load_data()
    if not df.empty:
        st.sidebar.caption(f"Angemeldet als: **{current_user}**")
        if st.sidebar.button("🔒 Abmelden"):
            st.session_state["logged_in"] = False
            st.session_state["current_user"] = None
            st.rerun()
        st.sidebar.markdown("---")
        st.sidebar.header("🔍 Filter")
        st.sidebar.button("🔄 Reset", on_click=reset_all_filters)
        
        standorte = []; klettertyp = []
        if "Standort" in df.columns: standorte = st.sidebar.multiselect("Standort", sorted(list(set(df["Standort"].dropna().astype(str)))), key="f_standort")
        if "Klettertyp" in df.columns: klettertyp = st.sidebar.multiselect("Klettertyp", sorted(list(set(df["Klettertyp"].dropna().astype(str)))), key="f_typ")
        c1, c2 = st.sidebar.columns(2)
        immergruen = c1.radio("Immergrün", ["Alle", "Ja", "Nein"], key="f_immergruen")
        insekten = c2.checkbox("🐝 Insekten", key="f_insekten")
        
        st.sidebar.markdown("---")
        with st.sidebar.expander("➕ Weitere Eigenschaften"):
            wasser = []; winter = []; boden = []; wuchs = []
            if "Wasserbedarf" in df.columns: wasser = st.multiselect("Wasserbedarf", sorted(list(set(df["Wasserbedarf"].dropna().astype(str)))), key="f_wasser")
            if "Winterhaerte" in df.columns: winter = st.multiselect("Winterhärte", sorted(list(set(df["Winterhaerte"].dropna().astype(str)))), key="f_winter")
            if "Boden" in df.columns: boden = st.multiselect("Bodenanspruch", sorted(list(set(df["Boden"].dropna().astype(str)))), key="f_boden")
            if "Wuchsstaerke" in df.columns: wuchs = st.multiselect("Wuchsstärke", sorted(list(set(df["Wuchsstaerke"].dropna().astype(str)))), key="f_wuchs")

        mask = pd.Series([True] * len(df))
        if standorte: mask &= df["Standort"].isin(standorte)
        if klettertyp: mask &= df["Klettertyp"].isin(klettertyp)
        if immergruen != "Alle": mask &= (df["Immergruen"] == immergruen)
        if insekten: mask &= (df["Insektenfreundlich"].str.contains("Ja", na=False, case=False))
        if wasser: mask &= df["Wasserbedarf"].isin(wasser)
        if winter: mask &= df["Winterhaerte"].isin(winter)
        if boden: mask &= df["Boden"].isin(boden)
        if wuchs: mask &= df["Wuchsstaerke"].isin(wuchs)
        df_filtered = df[mask]
        
        st.sidebar.divider(); st.sidebar.header("📂 Export")
        if current_user in GUESTS:
            st.sidebar.warning("🔒 Export nur in Vollversion")
            st.sidebar.markdown("<div class='guest-warning'>Bitte Vollversion erwerben für Excel & PDF Export</div>", unsafe_allow_html=True)
        else:
            st.sidebar.download_button("💾 Excel", to_excel(df_filtered), "pflanzen.xlsx")
            if st.sidebar.button("📄 PDF"):
                with st.spinner("PDF wird generiert..."):
                    st.sidebar.download_button("⬇️ Download", export_pdf(df_filtered), "report.pdf", "application/pdf")

        st.success(f"{len(df_filtered)} Pflanzen")
        cols = st.columns(3)
        for idx, (i, row) in enumerate(df_filtered.iterrows()):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(str(row.get("Name", "Unbekannt")))
                    st.caption(str(row.get("Botanisch", "-")))
                    bp = str(row.get("Bild_URL", "")).strip()
                    if len(bp) > 4 and os.path.exists(bp): st.image(bp, use_container_width=True)
                    else: st.info("Kein Bild verfügbar")
                    st.markdown(f"**Standort:** {row.get('Standort', '-')}\n**Typ:** {row.get('Klettertyp', '-')}")
                    with st.expander("📋 Details"):
                        desc = str(row.get("Beschreibung", ""))
                        if desc != "nan": st.write(f"**Beschreibung:** {desc}"); st.markdown("---")
                        for col in df.columns:
                            if col not in ["Name", "Botanisch", "Bild_URL", "Beschreibung"]:
                                val = str(row[col]); 
                                if val == "nan": val = "-"
                                st.markdown(f"**{col.replace('_', ' ')}:** {val}")
    else: st.warning("Keine Daten gefunden.")

if __name__ == "__main__":
    main()
