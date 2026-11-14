
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date

st.set_page_config(page_title="Spájz", page_icon="🥫", layout="centered")

# Mobilbarát megjelenés finomhangolása (alsó sáv és gombok)
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 5rem; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# Google Sheets csatlakozás
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Ha Streamlit Cloud Secrets-ben tárolod a kulcsot:
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Lokális futtatáshoz, ha mellette van a kulcs.json
        creds = ServiceAccountCredentials.from_json_keyfile_name("kulcs.json", scope)
    client = gspread.authorize(creds)
    return client.open("Spajz_Adatbazis").worksheet("Keszlet")

sheet = init_connection()

def load_data():
    records = sheet.get_all_records()
    return pd.DataFrame(records)

st.title("🥫 Spájz")

# Navigáció felül (mobilbarát fülek)
tab_keszlet, tab_uj = st.tabs(["📦 Aktuális készlet", "➕ Új tétel felvétele"])

with tab_uj:
    with st.form("uj_termek_form", clear_on_submit=True):
        termek = st.text_input("Termék neve", placeholder="pl. Tartós tej 2,8%, Lencse konzerv")
        col1, col2 = st.columns(2)
        with col1:
            kategoria = st.selectbox("Kategória", [
                "Tejtermék",
                "Hús / Felvágott",
                "Szárazáru / Konzerv",
                "Zöldség / Gyümölcs",
                "Fagyasztott",
                "Háztartás / Egyéb"
            ])
        with col2:
            mennyiseg = st.text_input("Mennyiség", value="1 db", placeholder="pl. 2 db, 500 g")
        
        col3, col4 = st.columns(2)
        with col3:
            van_lejarat = st.checkbox("Van lejárati dátuma", value=True)
            lejarat = st.date_input("Lejárati dátum", value=date.today())
        with col4:
            rogzitette = st.selectbox("Ki vette?", ["Zsolt", "Vivien"])
            
        submitted = st.form_submit_button("Mentés a spájzba")
        
        if submitted:
            if not termek.strip():
                st.error("Add meg a termék nevét!")
            else:
                lejarat_str = lejarat.strftime("%Y-%m-%d") if van_lejarat else "-"
                ma_str = datetime.now().strftime("%Y-%m-%d")
                sheet.append_row([termek.strip(), kategoria, mennyiseg.strip(), lejarat_str, rogzitette, ma_str])
                st.success(f"Hozzáadva: {termek} ({mennyiseg})")
                st.rerun()

with tab_keszlet:
    df = load_data()
    
    if df.empty:
        st.info("Még üres a spájz. Adj hozzá tételeket a másik fülön!")
    else:
        # Kereső és kategória szűrő
        col_search, col_filter = st.columns([2, 1])
        with col_search:
            kereses = st.text_input("Keresés...", placeholder="Termék neve")
        with col_filter:
            kat_szuro = st.selectbox("Szűrés", ["Összes"] + sorted(df["Kategoria"].unique().tolist()))

        # Sorindex megőrzése a törléshez (Google Sheets-ben a 2. sortól indul az adat)
        df["SheetRow"] = df.index + 2

        if kereses:
            df = df[df["Termek"].str.contains(kereses, case=False, na=False)]
        if kat_szuro != "Összes":
            df = df[df["Kategoria"] == kat_szuro]

        st.caption(f"Megjelenítve: {len(df)} tétel")

        # Kártyás megjelenítés (mobilon sokkal olvashatóbb, mint a táblázat)
        for _, row in df.iloc[::-1].iterrows():
            lej = str(row["Lejarat"])
            badge = ""
            if lej and lej != "-":
                try:
                    exp_date = datetime.strptime(lej[:10], "%Y-%m-%d").date()
                    days_left = (exp_date - date.today()).days
                    if days_left < 0:
                        badge = f"🔴 LEJÁRT ({lej})"
                    elif days_left <= 5:
                        badge = f"🟠 Hamarosan lejár: {lej} ({days_left} nap)"
                    else:
                        badge = f"🟢 Lejárat: {lej}"
                except ValueError:
                    badge = f"Lejárat: {lej}"
            else:
                badge = "⚪ Nincs lejárati dátum"

            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{row['Termek']}** — `{row['Mennyiseg']}`")
                    st.caption(f"{row['Kategoria']} • Rögzítette: {row['Rogzitette']} • {badge}")
                with c2:
                    if st.button("🗑️", key=f"del_{row['SheetRow']}", help="Elfogyott / Törlés"):
                        sheet.delete_rows(int(row["SheetRow"]))
                        st.toast(f"{row['Termek']} törölve!")
                        st.rerun()
