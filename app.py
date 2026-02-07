import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.title("🕵️‍♂️ DETEKTIV CHYB")

st.write("1. Zkouším načíst tajné klíče (Secrets)...")
try:
    secrets = st.secrets["gcp_service_account"]
    st.success("✅ Klíče nalezeny!")
except Exception as e:
    st.error(f"❌ CHYBA KLÍČŮ: {e}")
    st.stop()

st.write("2. Zkouším se přihlásit ke Googlu...")
try:
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_info(secrets, scopes=scope)
    client = gspread.authorize(creds)
    st.success("✅ Přihlášení úspěšné!")
except Exception as e:
    st.error(f"❌ CHYBA PŘIHLÁŠENÍ: {e}")
    st.stop()

st.write("3. Hledám tabulku 'CihlyData'...")
try:
    sheet = client.open("CihlyData")
    st.success(f"✅ Tabulka '{sheet.title}' nalezena!")
except Exception as e:
    st.error(f"❌ CHYBA TABULKY: Nemohu najít 'CihlyData'. Zkontroluj název a sdílení.")
    st.error(f"Detail chyby: {e}")
    st.stop()

st.write("4. Zkouším zapsat testovací data...")
try:
    sheet.sheet1.update_acell('A1', '{"test": "Uspesne spojeni!"}')
    st.balloons()
    st.success("🎉 HURÁ! VŠE FUNGUJE! Robot umí číst i zapisovat.")
    st.info("Teď můžeš vrátit zpátky herní kód.")
except Exception as e:
    st.error(f"❌ CHYBA ZÁPISU: Robot nemá právo 'Editor'.")
    st.error(f"Detail chyby: {e}")
