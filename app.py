import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# ZMĚNA NÁZVU - ABYCHOM POZNALI, ŽE SE TO AKTUALIZOVALO
st.title("🕵️‍♂️ DETEKTIV 3.0 (S POVOLENÍM DISKU)")

st.write("1. Načítám klíče...")
try:
    secrets = st.secrets["gcp_service_account"]
    st.success("✅ Klíče OK.")
except Exception as e:
    st.error(f"❌ Chyba klíčů: {e}")
    st.stop()

st.write("2. Přihlašuji se (včetně Google Drive)...")
try:
    # TOTO JE TA ČÁST, KTERÁ TI CHYBĚLA NEBO SE NENAČETLA:
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = Credentials.from_service_account_info(secrets, scopes=scope)
    client = gspread.authorize(creds)
    st.success("✅ Přihlášení OK.")
except Exception as e:
    st.error(f"❌ Chyba přihlášení: {e}")
    st.stop()

st.write("3. Hledám tabulku 'CihlyData'...")
try:
    sheet = client.open("CihlyData")
    st.success(f"✅ Tabulka '{sheet.title}' nalezena! JSI TAM!")
    st.balloons()
except Exception as e:
    st.error(f"❌ CHYBA TABULKY: Stále ji nevidím.")
    st.info("Pokud toto vidíš, znamená to, že kód je správný, ale musíš jít na Google Drive a nasdílet tabulku 'CihlyData' robotovi jako EDITOR.")
    st.text(f"Detail chyby: {e}")
