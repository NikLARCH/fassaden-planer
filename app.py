import streamlit as st
import pandas as pd
import os
import io
from fpdf import FPDF
from PIL import Image

# --- SEITEN KONFIGURATION ---
st.set_page_config(page_title="Fassadenbegrünung Profi-Planer", layout="wide")

# --- 1. BENUTZER & PASSWÖRTER ---
USERS = {
    "admin": "admin123",
    "demo": "gast",
    "architekt": "planer2024",
    "praktikant": "lern123"
}

# --- 2. WER IST NUR GAST? ---
GUESTS = ["demo", "praktikant"]

# --- CSS STYLING (STEALTH MODE) ---
st.markdown("""
<style>
    /* 1. KOPFZEILE & MENÜS AUSBLENDEN */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
    [data-testid="stDecoration"] {visibility: hidden !important; display: none !important;}
    
    /* 2. FUSSZEILE & BRANDING AUSBLENDEN */
    footer {visibility: hidden !important; display: none !important;}
    [data-testid="stFooter"] {visibility: hidden !important; display: none !important;}
    
    /* 3. DAS GRÜNE ICON / VIEWER BADGE UNTEN RECHTS */
    .viewerBadge_container__1QSob {visibility: hidden !important; display: none !important;}
    div[class^="viewerBadge"] {visibility: hidden !important; display: none !important;}
    
    /* 4. SICHERHEITSHALBER: ALLE LINKS ZU STREAMLIT AUSBLENDEN */
    a[href*="streamlit.io"] {visibility: hidden !important; display: none !important;}

    /* --- DEIN NORMALES DESIGN AB HIER --- */
    
    /* Login Box Styling */
    .stTextInput > div > div > input {
        background-color: #f0f2f6;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        caret-color: #000000 !important;
    }
    
    .stExpander { border: 1px solid #e0e0e0; border-radius: 5px; }
    div[data-testid="stExpander"] details summary p {
        font-weight: bold;
        font-size: 1.1em;
    }
    button[kind="secondary"] {
        width: 100%;
        border-color: #ff4b4b;
        color: #ff4b4b;
    }
    button[kind="secondary"]:hover {
        border-color: #ff0000;
        color: #ff0000;
    }
    .guest-warning {
        padding: 10px;
        background-color: #ffeeba;
        color: #856404;
        border-radius: 5px;
        border: 1px solid #ffeeba;
        font-size: 0.9em;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNKTION: DATEN LADEN ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("pflanzen.csv", sep=";", dtype=str)
        return df
    except Exception as e:
        st.error(f"Fehler beim Laden der Datenbank: {e}")
        return pd.DataFrame()

# --- FUNKTION: EXCEL EXPORT ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Pflanzenauswahl')
    processed_data = output.getvalue()
    return processed_data

# --- HILFSFUNKTION: BILDER VORBEREITEN ---
def prepare_image_for_pdf(image_path, unique_id):
    try:
        if not os.path.exists(image_path): return None
        img = Image.open(image_path)
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == 'P': img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[3])
            img = bg
        else:
            img = img.convert("RGB")
        temp_path = f"temp_img_{unique_id}.jpg"
        img.save(temp_path, "JPEG", quality=90)
        return temp_path
    except: return None

# --- FUNKTION: PDF EXPORT ---
def export_pdf(df_filtered):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Logo
    logo_path = "logo.png"
    if not os.path.exists(logo_path): logo_path = "1200x1200_1.png"
    
    if os.path.exists(logo_path):
        clean_logo = prepare_image_for_pdf(logo_path, "header_logo")
        if clean_logo:
            try:
                pdf.image(clean_logo, x=160, y=10, w=35)
                os.remove(clean_logo)
            except: pass

    # Titel
    pdf.set_font("Arial", "B", 16)
    pdf.set_y(20)
    pdf.cell(0, 10, txt="Pflanzenauswahl Fassadenbegrünung", ln=True, align='L')
    pdf.line(10, 32, 200, 32)
    pdf.ln(15)
    
    for index, row in df_filtered.iterrows():
        if pdf.get_y() > 220: pdf.add_page()
        
        # Name
        pdf.set_font("Arial", "B", 14)
        pdf.set_fill_color(240, 240, 240)
        name = str(row.get('Name', '')).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 8, txt=name, ln=True, fill=True)
        pdf.set_font("Arial", "I", 10)
        bot = str(row.get('Botanisch', '')).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 6, txt=bot, ln=True)
        pdf.ln(2)

        # Bild
        orig_bp = str(row.get("Bild_URL", "")).strip()
        img_size = 40
        img_x = 10
        img_y = pdf.get_y()
        has_img = False
        clean_path = None
        
        if len(orig_bp) > 4:
            clean_path = prepare_image_for_pdf(orig_bp, index)
            if clean_path:
                try:
                    pdf.image(clean_path, x=img_x, y=img_y, w=img_size)
                    has_img = True
                except: pass

        if not has_img:
            pdf.set_fill_color(250, 250, 250)
            pdf.rect(img_x, img_y, img_size, img_size, 'F')
            pdf.set_xy(img_x, img_y + 18)
            pdf.set_font("Arial", size=8)
            pdf.cell(img_size, 5, "Kein Bild", align='C')

        if clean_path and os.path.exists(clean_path):
            try: os.remove(clean_path)
            except: pass

        # Infos
        text_x = 55
        pdf.set_xy(text_x, img_y)
        pdf.set_font("Arial", size=10)
        kurz_infos = ["Standort", "Klettertyp", "Wasserbedarf", "Winterhaerte"]
        for k in kurz_infos:
            val = str(row.get(k, '-')).encode('latin-1', 'replace').decode('latin-1')
            lbl = k.replace("_", " ")
            pdf.set_font("Arial", "B", 10)
            pdf.cell(35, 5, f"{lbl}:", ln=False)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 5, val, ln=True)
            pdf.set_x(text_x)

        # Details
        pdf.set_y(max(pdf.get_y(), img_y + img_size + 5))
        desc = str(row.get('Beschreibung', '')).encode('latin-1', 'replace').decode('latin-1')
        if len(desc) > 3:
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 5, "Beschreibung:", ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 5, desc)
            pdf.ln(2)

        pdf.set_font("Arial", "B", 8)
        pdf.cell(0, 5, "Vollständige Daten:", ln=True)
        pdf.set_font("Arial", "", 8)
        all_details = ""
        exclude = ["Name", "Botanisch", "Bild_URL", "Beschreibung"] + kurz_infos
        for col in df_filtered.columns:
            if col not in exclude:
                val = str(row[col])
                if val != "nan" and val != "-":
                    val_c = val.encode('latin-1', 'replace').decode('latin-1')
                    all_details += f"[{col.replace('_',' ')}: {val_c}]  "
        pdf.multi_cell(0, 4, all_details)
        pdf.ln(3)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.set_draw_color(0,0,0)
        pdf.ln(5)
    
    return pdf.output(dest='S').encode('latin-1')

# --- RESET CALLBACK ---
def reset_all_filters():
    st.session_state["f_standort"] = []
    st.session_state["f_typ"] = []
    st.session_state["f_immergruen"] = "Alle"
    st.session_state["f_insekten"] = False
    if "f_wasser" in st.session_state: st.session_state["f_wasser"] = []
    if "f_winter" in st.session_state: st.session_state["f_winter"] = []
    if "f_boden" in st.session_state: st.session_state["f_boden"] = []
    if "f_wuchs" in st.session_state: st.session_state["f_wuchs"] = []

# --- LOGIN LOGIK ---
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
                else:
                    st.error("Falscher Benutzername oder Passwort")
        return False
    return True

# --- HAUPTPROGRAMM ---
def main():
    if not check_login(): return

    current_user = st.session_state.get("current_user", "Gast")

    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        logo_files = ["logo.png", "1200x1200_1.png"]
        for f in logo_files:
            if os.path.exists(f):
                st.image(f, use_container_width=True)
                break
    with col_title:
        st.title("🌿 Profi-Datenbank")
        st.markdown("### Fassadenbegrünung")

    st.divider()
    df = load_data()

    if not df.empty:
        # --- SIDEBAR OBEN ---
        st.sidebar.caption(f"Angemeldet als: **{current_user}**")
        if st.sidebar.button("🔒 Abmelden"):
            st.session_state["logged_in"] = False
            st.session_state["current_user"] = None
            st.rerun()
        st.sidebar.markdown("---")
        
        # --- FILTER ---
        st.sidebar.header("🔍 Filter")
        st.sidebar.button("🔄 Reset", on_click=reset_all_filters)
        
        standorte = []
        if "Standort" in df.columns:
            opts = sorted(list(set(df["Standort"].dropna().astype(str))))
            standorte = st.sidebar.multiselect("Standort", opts, key="f_standort")
        klettertyp = []
        if "Klettertyp" in df.columns:
            opts = sorted(list(set(df["Klettertyp"].dropna().astype(str))))
            klettertyp = st.sidebar.multiselect("Klettertyp", opts, key="f_typ")
        c1, c2 = st.sidebar.columns(2)
        immergruen = c1.radio("Immergrün", ["Alle", "Ja", "Nein"], key="f_immergruen")
        insekten = c2.checkbox("🐝 Insekten", key="f_insekten")

        st.sidebar.markdown("---")
        with st.sidebar.expander("➕ Weitere Eigenschaften", expanded=False):
            wasser = []
            if "Wasserbedarf" in df.columns:
                opts = sorted(list(set(df["Wasserbedarf"].dropna().astype(str))))
                wasser = st.multiselect("Wasserbedarf", opts, key="f_wasser")
            winter = []
            if "Winterhaerte" in df.columns:
                opts = sorted(list(set(df["Winterhaerte"].dropna().astype(str))))
                winter = st.multiselect("Winterhärte", opts, key="f_winter")
            boden = []
            if "Boden" in df.columns:
                opts = sorted(list(set(df["Boden"].dropna().astype(str))))
                boden = st.multiselect("Bodenanspruch", opts, key="f_boden")
            wuchs = []
            if "Wuchsstaerke" in df.columns:
                opts = sorted(list(set(df["Wuchsstaerke"].dropna().astype(str))))
                wuchs = st.multiselect("Wuchsstärke", opts, key="f_wuchs")

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
        
        # --- EXPORT BEREICH (MIT DEM SCHUTZ) ---
        st.sidebar.divider()
        st.sidebar.header("📂 Export")
        
        # HIER IST DER DIEBSTAHLSCHUTZ:
        if current_user in GUESTS:
            # Das sieht der Gast
            st.sidebar.warning("🔒 Export nur in Vollversion")
            st.sidebar.markdown("<div class='guest-warning'>Bitte Vollversion erwerben für Excel & PDF Export</div>", unsafe_allow_html=True)
        else:
            # Das sehen zahlende Kunden (und Admin)
            st.sidebar.download_button("💾 Excel", to_excel(df_filtered), "pflanzen.xlsx")
            if st.sidebar.button("📄 PDF"):
                with st.spinner("PDF wird generiert..."):
                    st.sidebar.download_button("⬇️ Download", export_pdf(df_filtered), "report.pdf", "application/pdf")

        # --- ANZEIGE ---
        st.success(f"{len(df_filtered)} Pflanzen")
        cols = st.columns(3)
        for idx, (i, row) in enumerate(df_filtered.iterrows()):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(str(row.get("Name", "Unbekannt")))
                    st.caption(str(row.get("Botanisch", "-")))
                    bp = str(row.get("Bild_URL", "")).strip()
                    if len(bp) > 4 and os.path.exists(bp):
                        st.image(bp, use_container_width=True)
                    else:
                        st.info("Kein Bild verfügbar")
                    st.markdown(f"**Standort:** {row.get('Standort', '-')}\n**Typ:** {row.get('Klettertyp', '-')}")
                    with st.expander("📋 Details"):
                        desc = str(row.get("Beschreibung", ""))
                        if desc != "nan":
                            st.write(f"**Beschreibung:** {desc}")
                            st.markdown("---")
                        for col in df.columns:
                            if col not in ["Name", "Botanisch", "Bild_URL", "Beschreibung"]:
                                val = str(row[col])
                                if val == "nan": val = "-"
                                st.markdown(f"**{col.replace('_', ' ')}:** {val}")
    else:
        st.warning("Keine Daten gefunden.")

if __name__ == "__main__":
    main()