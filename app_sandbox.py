import streamlit as st
import json
import os
import random
import time
import pandas as pd
import altair as alt
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 🎨 1. KONFIGURACE (VŠE ZACHOVÁNO)
# ==========================================
st.set_page_config(page_title="Cihlářské Sázky", page_icon="🧱", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; color: #333; }
    h1, h2, h3 { color: #ff6600 !important; font-family: 'Arial Black', sans-serif; text-transform: uppercase; }
    
    /* Tlačítka */
    .stButton>button { background-color: #ff6600; color: white; border: none; font-weight: bold; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #cc5200; transform: scale(1.02); }
    
    /* Karty - styl se aplikuje přímo v HTML níže pro jistotu */
    
    /* Statistiky */
    .stat-box { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 10px; border-left: 5px solid #ccc; }
    .stat-label { font-size: 0.85em; color: #666; text-transform: uppercase; letter-spacing: 1px; }
    .stat-val { font-size: 1.4em; font-weight: bold; color: #333; }
    
    /* Indikátory */
    .market-open { background-color: #d1e7dd; color: #0f5132; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; border: 2px solid #badbcc; }
    .market-closed { background-color: #f8d7da; color: #842029; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; border: 2px solid #f5c2c7; }
    
    /* Chat & Historie */
    .ticket-pending { border-left: 5px solid #ffc107; background: #fff3cd; padding: 10px; margin-bottom: 5px; border-radius: 4px; }
    .ticket-won { border-left: 5px solid #198754; background: #d1e7dd; padding: 5px; margin-bottom: 5px; border-radius: 4px; }
    .ticket-lost { border-left: 5px solid #dc3545; background: #f8d7da; padding: 5px; margin-bottom: 5px; border-radius: 4px; }
    .trans-in { border-left: 5px solid #198754; background: #d1e7dd; padding: 8px; margin-bottom: 4px; border-radius: 4px; }
    .trans-out { border-left: 5px solid #dc3545; background: #f8d7da; padding: 8px; margin-bottom: 4px; border-radius: 4px; }
    .hist-item { font-size: 0.9em; padding: 5px; border-bottom: 1px solid #eee; color: #555; }
    
    .msg-sys { background: #fff3cd; border-left: 5px solid #ffc107; padding: 8px; margin-bottom: 5px; font-size: 0.9em; }
    .msg-event { background: #cff4fc; border-left: 5px solid #0dcaf0; padding: 8px; margin-bottom: 5px; font-weight: bold; }
    .msg-user { background: white; border-left: 5px solid #ddd; padding: 8px; margin-bottom: 5px; }
    
    /* Odznaky */
    .badge { padding: 2px 6px; border-radius: 4px; color: white; font-size: 0.75em; font-weight: bold; margin-left: 5px; vertical-align: middle; }
    .bg-0 { background: #6c757d; }
    .bg-1 { background: #795548; }
    .bg-2 { background: #fd7e14; }
    .bg-3 { background: #0d6efd; }
    .bg-4 { background: #dc3545; }
    .bg-5 { background: linear-gradient(45deg, #FFD700, #DAA520); color: black; }
    .bg-admin { background: #000; border: 1px solid #ff6600; }
    .streak { color: #ff4500; font-weight: bold; margin-left: 5px; text-shadow: 0 0 5px orange; }
</style>
""", unsafe_allow_html=True)

# Pevná definice barev
COLORS = {
    "Červená": "#dc3545", "Modrá": "#0d6efd", "Žlutá": "#ffc107", "Zelená": "#198754",
    "Oranžová": "#fd7e14", "Fialová": "#6f42c1", "Bílá": "#ffffff", "Černá": "#212529",
    "Šedá": "#6c757d", "Hnědá": "#795548", "Růžová": "#d63384", "Béžová": "#f5f5dc",
    "Tyrkysová": "#20c997", "Azurová": "#0dcaf0"
}

RANKS = [
    {"name": "Pomocná síla", "inc": 50, "css": "bg-0"}, 
    {"name": "Kopáč", "inc": 150, "css": "bg-1"},
    {"name": "Zedník", "inc": 400, "css": "bg-2"}, 
    {"name": "Zásobovač", "inc": 1000, "css": "bg-3"},
    {"name": "Stavbyvedoucí", "inc": 3000, "css": "bg-4"}, 
    {"name": "Cihlobaron", "inc": 10000, "css": "bg-5"}
]

DEFAULT_SHOP = [
    {"name": "🧃 Svačina", "base_p": 50, "curr_p": 50, "type": "use", "desc": "Doplní 50 CC."},
    {"name": "👷 BOZP Helma", "base_p": 300, "curr_p": 300, "type": "use", "desc": "Aktivuj PŘED sázkou. Vrátí 50% při prohře."},
    {"name": "🧱 Zlatá Cihla", "base_p": 1000, "curr_p": 1000, "type": "use", "desc": "Aktivuj PŘED sázkou. Výhra x2."},
    {"name": "🛡️ Titanová Přilba", "base_p": 3000, "curr_p": 3000, "type": "passive", "desc": "Pasivní: 80% šance odrazit útok. (Max 1 ks)"},
    {"name": "🦶 Podkopnutí", "base_p": 8000, "curr_p": 8000, "type": "atk", "desc": "Útok v Žebříčku: Zraní soupeře."},
    {"name": "👻 Fantom", "base_p": 20000, "curr_p": 20000, "type": "atk", "desc": "Tajný útok v Žebříčku."},
    {"name": "🪣 Větší Kbelík", "base_p": 2500, "curr_p": 2500, "type": "upgrade", "desc": "+2 Sloty do batohu."}
]

# ==========================================
# ☁️ 2. GOOGLE CLOUD NAPOJENÍ (VŠE V JEDNOM LISTU)
# ==========================================
@st.cache_resource
def init_connection():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=2, show_spinner=False)  # <--- TADY PŘIDÁŠ TENTO ŘÁDEK
def load_data():
    """Načte vše z jednoho listu 'Data' (Uživatelé + Systém)"""
  # Změněno: Přidána odds_history a neaktivita_count pro nový výpočet
    base = {
        "users": {}, 
        "market": {
            "status": "CLOSED", 
            "colors": {c: 2.0 for c in COLORS},
            "odds_history": {c: [2.0] for c in COLORS},
            "neaktivita_count": {c: 0 for c in COLORS}
        }, 
        "chat": [], 
        "shop": DEFAULT_SHOP
    }
    try:
        client = init_connection()
        # POZOR: Jméno tabulky musí přesně sedět s tím, co máš v Google Drive
        sh = client.open("CihlyData_SANDBOX")
        sheet = sh.worksheet("Data")
        
        all_rows = sheet.get_all_values()
        if len(all_rows) <= 1: # Pokud je tam jen záhlaví nebo nic
            return base

        for row in all_rows[1:]: # Přeskočíme záhlaví
            if len(row) < 2 or not row[0]: continue
            name, content = row[0], row[1]
            
            try:
                decoded_content = json.loads(content)
                if name == "_SYSTEM_":
                    base["market"] = decoded_content.get("market", base["market"])
                    base["chat"] = decoded_content.get("chat", base["chat"])
                    base["shop"] = decoded_content.get("shop", base["shop"])
                else:
                    base["users"][name] = decoded_content
            except:
                continue # Přeskočit poškozené řádky
                
        return base
    except Exception as e:
        st.error(f"⚠️ Chyba načítání: {e}")
        return base

def save_data(data):
    """Uloží kompletně vše do listu 'Data' - metoda přepsáním listu"""
    try:
        client = init_connection()
        sh = client.open("CihlyData_SANDBOX")
        sheet = sh.worksheet("Data")
        
        # Příprava dat k zápisu
        rows = [["Username", "Data"]] # Záhlaví
        
        # 1. Přidáme systém pod speciální jméno
        sys_block = {
            "market": data["market"], 
            "chat": data["chat"][-50:], 
            "shop": data["shop"]
        }
        rows.append(["_SYSTEM_", json.dumps(sys_block)])
        
        # 2. Přidáme všechny uživatele
        for uname, udata in data["users"].items():
            # Čistič historie pro plynulý chod (Anti-Lag)
            if "bets" in udata: udata["bets"] = udata["bets"][-30:]
            if "trans" in udata: udata["trans"] = udata["trans"][-30:]
            rows.append([uname, json.dumps(udata)])
            
        # Provedeme vymazání a jeden velký update (šetří API kvótu)
        sheet.clear()
        sheet.update('A1', rows)
        # 👇 SEM VLOŽÍŠ TENTO ŘÁDEK 👇
        load_data.clear()
        # 👆 ---------------------- 👆
    except Exception as e:
        st.error(f"⚠️ Chyba ukládání: {e}")

# ==========================================
# 💾 LOGIKA
# ==========================================
def get_time(): return datetime.now().strftime("%H:%M")

def log_item_usage(user_dict, item_name, detail):
    if "item_history" not in user_dict: user_dict["item_history"] = []
    user_dict["item_history"].append({"item": item_name, "detail": detail, "tm": get_time()})

def update_user_stats(user_dict, amount_won, amount_lost, bet_amount, color, shop_spent=0, other_income=0):
    s = user_dict["stats"]
    if bet_amount > 0:
        s["total_bets"] += 1
        s["color_counts"][color] = s["color_counts"].get(color, 0) + 1
    if amount_won > 0:
        s["total_wins"] += 1
        s["total_bet_winnings"] += amount_won
        s["total_income_all"] += amount_won
        if amount_won > s["max_win"]: s["max_win"] = amount_won
    if amount_lost > 0: s["total_losses"] += 1
    if shop_spent > 0: s["total_spent"] += shop_spent
    if other_income > 0: s["total_income_all"] += other_income

# --- EVENTY ---
def trigger_shop_fluctuation(data):
    for item in data["shop"]: item["curr_p"] = item["base_p"]
    eligible = [i for i, item in enumerate(data["shop"]) if "Svačina" not in item["name"] and "Kbelík" not in item["name"]]
    random.shuffle(eligible)
    
    discounted, hiked = [], []
    if eligible: discounted.append(eligible.pop(0))
    if eligible and random.random() < 0.5: discounted.append(eligible.pop(0))
    if eligible and random.random() < 0.2: discounted.append(eligible.pop(0))
    if eligible: hiked.append(eligible.pop(0))
    if eligible and random.random() < 0.5: hiked.append(eligible.pop(0))
    if eligible and random.random() < 0.2: hiked.append(eligible.pop(0))
    
    msg_parts = []
    for i in discounted:
        item = data["shop"][i]; perc = random.randint(5, 95)
        item["curr_p"] = max(1, int(item["base_p"] * (1 - perc/100.0)))
        msg_parts.append(f"<span style='color:#198754'>⬇️ {item['name']} -{perc}%</span>")
    for i in hiked:
        item = data["shop"][i]; perc = random.randint(5, 95)
        item["curr_p"] = int(item["base_p"] * (1 + perc/100.0))
        msg_parts.append(f"<span style='color:#dc3545'>⬆️ {item['name']} +{perc}%</span>")
        
    if msg_parts:
        final_msg = "🏷️ CENOVÝ ŠOK: " + " | ".join(msg_parts)
        data["chat"].append({"u":"SHOP", "t":final_msg, "tm":get_time(), "r":"BOT"})
        return final_msg
    return "Ceny stabilní."

def trigger_game_event(data, event_type):
    msg = ""
    if event_type == "MEGA":
        if "original_odds" not in data["market"]:
            data["market"]["original_odds"] = data["market"]["colors"].copy()
            
        boosted = random.sample(list(COLORS.keys()), 3)
        for bc in boosted: 
            base_val = data["market"]["original_odds"][bc]
            data["market"]["colors"][bc] = round(base_val * 5.0, 1)
        msg = f"🚀 MEGA EVENT: Barvy {', '.join(boosted)} mají 5x kurz!"
        
    elif event_type == "COPPER":
        for u in data["users"].values(): 
            u["bal"] += 150
            update_user_stats(u, 0, 0, 0, "", 0, 150)
        msg = "🎁 EVENT: Nález mědi! +150 CC všem."
    elif event_type == "SCAFFOLD":
        for u in data["users"].values(): u["bal"] = int(u["bal"] * 0.9)
        msg = "🔥 EVENT: Pád lešení! -10% všem."
    elif event_type == "PROVERKA":
        victims = []
        for uname, u in data["users"].items():
            if random.random() < 0.50: 
                u["hp"] = "ZRANEN"; victims.append(uname)
        msg = f"👮 EVENT: PROVĚRKA! Zraněni: {', '.join(victims)}" if victims else "👮 EVENT: Prověrka proběhla. Vše v pořádku."

    if msg: data["chat"].append({"u":"EVENT", "t":msg, "tm":get_time(), "r":"BOT"}); return msg
    return None

data = load_data()

# ==========================================
# 🔐 3. LOGIN
# ==========================================
if "user" not in st.session_state: st.session_state.user = None

st.sidebar.title("🧱 MENU")

if not st.session_state.user:
    tab1, tab2 = st.sidebar.tabs(["Login", "Registrace"])
    with tab1:
        u = st.text_input("Jméno", key="lu")
        p = st.text_input("Heslo", type="password", key="lp")
        if st.button("Vstoupit"):
            if u in data["users"] and data["users"][u]["pass"] == p:
                st.session_state.user = u; st.rerun()
            else: st.sidebar.error("Chyba")
    with tab2:
        nu = st.text_input("Nové jméno", key="ru")
        np = st.text_input("Nové heslo", type="password", key="rp")
        if st.button("Vytvořit"):
            if nu and nu not in data["users"]:
                data["users"][nu] = {
                    "pass": np, "bal": 0, "rank": 0, "inv": [], "slots": 0, 
                    "hp": "OK", "bets": [], "pay": False, "bonus": None, 
                    "trans": [], "item_history": [], "streak": 0,
                    "stats": {"total_bets":0,"total_wins":0,"total_losses":0,"max_win":0,"total_income_all":0,"total_bet_winnings":0,"total_spent":0,"color_counts":{}, "max_streak": 0}
                }
                save_data(data); st.session_state.user = nu; st.rerun()
            else: st.sidebar.error("Obsazeno")

# ==========================================
# 🏗️ 4. APLIKACE
# ==========================================
else:
    me = st.session_state.user
    if me not in data["users"]: st.session_state.user = None; st.rerun()
    user = data["users"][me]
    
    if "streak" not in user: user["streak"] = 0
    if "stats" not in user: user["stats"] = {"total_bets":0,"total_wins":0,"total_losses":0,"max_win":0,"total_income_all":0,"total_bet_winnings":0,"total_spent":0,"color_counts":{}, "max_streak": 0}

    if st.sidebar.button("Odhlásit"): 
        st.session_state.user = None
        st.session_state.admin_ok = False
        st.rerun()
    
    rid = min(user["rank"], len(RANKS)-1)
    max_slots = 3 + (user["slots"] * 2)
    current_items = len(user["inv"])
    
    st.sidebar.divider()
    streak_display = f"🔥 {user['streak']}" if user['streak'] > 0 else ""
    st.sidebar.write(f"👷 **{me}** {streak_display}")
    st.sidebar.info(f"{RANKS[rid]['name']}")
    
    st.sidebar.metric("Zůstatek", f"{int(user['bal'])} CC")
    if user["hp"] != "OK": st.sidebar.error("🤕 JSI ZRANĚN!")
    
    page = st.sidebar.radio("Navigace", ["DOMŮ", "ŽEBŘÍČEK", "STATISTIKY", "GRAFY", "OBCHOD", "BATOH", "BANKA", "CHAT", "📚 NÁPOVĚDA", "ADMIN"])

    # --- DOMŮ ---
    if page == "DOMŮ":
        st.title("🏠 Centrála")
        st.markdown(f'<div class="market-{"open" if data["market"]["status"]=="OPEN" else "closed"}">TRH JE {"OTEVŘENÝ 🟢" if data["market"]["status"]=="OPEN" else "ZAVŘENÝ 🔴"}</div>', unsafe_allow_html=True)
        st.write("")

        if data["market"]["status"] == "OPEN":
            if not user["pay"]:
                inc = RANKS[rid]["inc"]
                if st.button(f"💸 Vybrat výplatu (+{inc} CC)"):
                    user["bal"] += inc; user["pay"] = True
                    user["trans"].append({"type": "in", "amt": inc, "src": "Výplata", "tm": get_time()})
                    update_user_stats(user, 0, 0, 0, "", 0, inc)
                    save_data(data); st.balloons(); st.rerun()

            if user["hp"] != "OK":
                st.error("🤕 Jsi zraněn! Nemůžeš sázet.")
            else:
                st.write("### 🎲 Vsaď na barvu")
                if user.get("bonus"): st.info(f"✨ Aktivní bonus: {user['bonus']}")

                cols = st.columns(4)
                idx = 0
                
                # ZDE JE OPRAVA PROBLÉMU S ROZSYPANÝM HTML
                for c_name, hex_c in COLORS.items():
                    with cols[idx % 4]:
                        odd = data["market"]["colors"].get(c_name, 2.0)
                        
                        # Styl karty
                        border_style = "2px solid #eee"
                        box_shadow = "0 4px 6px rgba(0,0,0,0.05)"
                        extra_info_html = ""
                        
                        # Porovnání s předchozím kolem
                        prev_odd = data["market"].get("prev_colors", {}).get(c_name, 2.0)
                        diff = round(odd - prev_odd, 1)
                        if diff > 0: extra_info_html = f"<div style='color:#198754;font-weight:bold;font-size:0.8em;margin-top:2px'>▲ +{diff}</div>"
                        elif diff < 0: extra_info_html = f"<div style='color:#dc3545;font-weight:bold;font-size:0.8em;margin-top:2px'>▼ {diff}</div>"
                        
                        if "original_odds" in data["market"] and c_name in data["market"]["original_odds"]:
                            orig = data["market"]["original_odds"][c_name]
                            if odd > orig:
                                border_style = "2px solid #ffd700"
                                box_shadow = "0 0 15px #ffd700"
                                diff_evt = round(odd - orig, 1)
                                extra_info_html = f"<div style='color:#ffd700;font-weight:bold;font-size:0.9em;margin-top:2px'>⚡ MEGA +{diff_evt}</div>"

                        # TOTO JE OPRAVENÉ HTML, KTERÉ SE UŽ NEROZSYPE
                        card_html = f"""
                        <div style='background: white; border-radius: 12px; padding: 10px; text-align: center; border: {border_style}; box-shadow: {box_shadow}; height: 160px; display: flex; flex-direction: column; justify-content: center; align-items: center;'>
                            <div style='width: 30px; height: 30px; border-radius: 50%; background-color: {hex_c}; display: block; margin: 0 auto 5px auto; border: 1px solid #ccc; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'></div>
                            <div style='font-weight:bold; margin-bottom:5px; color:#333;'>{c_name}</div>
                            <div style='color:#ff6600; font-weight:bold; font-size:1.4em;'>{odd}x</div>
                            {extra_info_html}
                        </div>
                        """
                        
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                        if st.button("Vsadit", key=f"b_{c_name}"):
                            st.session_state["target"] = (c_name, odd)
                    idx += 1
                
                # --- TADY BYLA CHYBA: TENTO BLOK MUSÍ BÝT ZCELA MIMO 'FOR' CYKLUS ---
                if "target" in st.session_state:
                    tc, to = st.session_state["target"]
                    st.info(f"Tiket: **{tc}** (Kurz {to})")
                    
                    bal = int(user["bal"])
                    def_v = 50 if bal >= 50 else bal
                    vklad = st.number_input("Vklad", 1, max(1, bal), max(1, def_v))
                    
                    # --- NOVÝ VÝBĚR ITEMŮ ---
                    dostupne_predmety = list(set(user.get("inv", [])))
                    if dostupne_predmety:
                        vybrane_predmety = st.multiselect("🎒 Použít předměty z batohu (max 1 od druhu):", options=dostupne_predmety)
                    else:
                        vybrane_predmety = []
                    
                    if st.button("✅ Odeslat"):
                        if user["bal"] >= vklad:
                            user["bal"] -= vklad
                            used_bonus = user.get("bonus", None)
                            user["bonus"] = None 
                            
                            # Odečtení použitých itemů
                            if vybrane_predmety:
                                for predmet in vybrane_predmety:
                                    if predmet in user["inv"]:
                                        user["inv"].remove(predmet)
                                        
                            # Přidáno "items" do sázky
                            user["bets"].append({"c": tc, "a": vklad, "o": to, "st": "PENDING", "bonus": used_bonus, "items": vybrane_predmety})
                            update_user_stats(user, 0, 0, vklad, tc)
                            save_data(data)
                            st.success("Hotovo")
                            del st.session_state["target"]
                            st.rerun()
                        else: 
                            st.error("Chybí CC")
        
        st.divider()
        st.subheader("🎫 Moje Tikety")
        pending = [b for b in user["bets"] if b["st"] == "PENDING"]
        history = [b for b in reversed(user["bets"]) if b["st"] != "PENDING"]
        
        if pending:
            for b in pending:
                bonus_txt = f" (+ {b['bonus']})" if b.get('bonus') else ""
                
                # NOVÉ: Vypsání itemů na aktivním tiketu
                items_txt = ""
                if b.get('items'):
                    items_txt = f"<br><span style='font-size: 0.8em; color: #555;'>🎒 Použito: {', '.join(b['items'])}</span>"
                    
                st.markdown(f"<div class='ticket-pending'><b>{b['c']}</b> | {b['a']} CC{bonus_txt}{items_txt}</div>", unsafe_allow_html=True)
        else: st.caption("Žádné aktivní sázky.")
            
        with st.expander("📜 Historie sázek"):
            for b in history:
                res = "✅" if b["st"] == "WON" else "❌"
                cls = "ticket-won" if b["st"] == "WON" else "ticket-lost"
                profit_info = ""
                if b["st"] == "WON":
                    profit = int(b["a"] * b["o"]) - b["a"]
                    profit_info = f"(+{profit} profit)"
                elif b["st"] == "LOST" and b.get("insurance"):
                    profit_info = "(Pojištěno 50%)"
                    
                # NOVÉ: Vypsání itemů i v historii
                items_txt = f" <span style='font-size: 0.85em;'>[🎒 {', '.join(b['items'])}]</span>" if b.get('items') else ""
                
                st.markdown(f"<div class='{cls}'>{res} <b>{b['c']}</b> ({b['a']} CC) {profit_info}{items_txt}</div>", unsafe_allow_html=True)

    # --- ŽEBŘÍČEK ---
    elif page == "ŽEBŘÍČEK":
        st.title("🏆 Žebříček")
        for i, (target_name, target_data) in enumerate(sorted(data["users"].items(), key=lambda x: x[1]['bal'], reverse=True)):
            hp_icon = "🤕" if target_data["hp"] != "OK" else ""
            streak_icon = f"🔥 {target_data['streak']}" if target_data.get('streak', 0) > 0 else ""
            trid = min(target_data["rank"], 5)
            r_style = RANKS[trid]["css"]; r_name = RANKS[trid]["name"]
            
            st.markdown(f"""
            <div style="background:white;padding:10px;border-radius:5px;margin-bottom:5px;border-left:3px solid #ccc">
                <b>#{i+1} {target_name}</b> {hp_icon} <span class='badge {r_style}'>{r_name}</span> <span class='streak'>{streak_icon}</span>
                <div style="float:right;font-weight:bold">{int(target_data['bal'])} CC</div>
            </div>
            """, unsafe_allow_html=True)
            
            if target_name != me and target_data["hp"] == "OK":
                col1, col2 = st.columns([1, 4])
                with col1:
                    if "🦶 Podkopnutí" in user["inv"]:
                        if st.button("👊 Podkopnout", key=f"kick_{target_name}"):
                            user["inv"].remove("🦶 Podkopnutí")
                            log_item_usage(user, "Podkopnutí", f"Cíl: {target_name}")
                            blocked = False
                            if "🛡️ Titanová Přilba" in target_data["inv"]:
                                if random.random() < 0.8:
                                    blocked = True; target_data["inv"].remove("🛡️ Titanová Přilba")
                                    log_item_usage(data["users"][target_name], "Titanová Přilba", "Zničena při obraně")
                            if blocked:
                                data["chat"].append({"u":"SYS", "t":f"🛡️ {target_name} vykryl útok od {me}! Helma zničena.", "tm":get_time(), "r": "BOT"})
                                st.warning("Soupeř se ubránil.")
                            else:
                                target_data["hp"] = "ZRANEN"
                                data["chat"].append({"u":"SYS", "t":f"🚨 {me} podkopl {target_name}!", "tm":get_time(), "r": "BOT"})
                                st.success("Zásah!")
                            save_data(data); st.rerun()

                    elif "👻 Fantom" in user["inv"]:
                         if st.button("👻 Fantom", key=f"fan_{target_name}"):
                            user["inv"].remove("👻 Fantom")
                            log_item_usage(user, "Fantom", f"Cíl: {target_name}")
                            blocked = False
                            if "🛡️ Titanová Přilba" in target_data["inv"]:
                                if random.random() < 0.8:
                                    blocked = True; target_data["inv"].remove("🛡️ Titanová Přilba")
                                    log_item_usage(data["users"][target_name], "Titanová Přilba", "Zničena při obraně")
                            if blocked:
                                data["chat"].append({"u":"SYS", "t":f"🛡️ {target_name} odrazil tajný útok!", "tm":get_time(), "r": "BOT"})
                            else:
                                target_data["hp"] = "ZRANEN"
                                data["chat"].append({"u":"SYS", "t":f"👻 {target_name} byl záhadně zraněn!", "tm":get_time(), "r": "BOT"})
                                st.success("Tichá práce.")
                            save_data(data); st.rerun()

    # --- STATISTIKY ---
    elif page == "STATISTIKY":
        st.title("📊 Osobní Karta")
        s = user["stats"]
        
        st.subheader("💰 Finance")
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='stat-box' style='border-left:5px solid #28a745'><div class='stat-label'>Celkový příjem (vše)</div><div class='stat-val'>+{s['total_income_all']} CC</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='stat-box' style='border-left:5px solid #17a2b8'><div class='stat-label'>Zisk jen ze sázek</div><div class='stat-val'>+{s['total_bet_winnings']} CC</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='stat-box' style='border-left:5px solid #dc3545'><div class='stat-label'>Utraceno v shopu</div><div class='stat-val'>-{s['total_spent']} CC</div></div>", unsafe_allow_html=True)
        
        st.subheader("🎲 Herní výkon")
        c4, c5, c6 = st.columns(3)
        fav_color = max(s['color_counts'], key=s['color_counts'].get) if s['color_counts'] else "Žádná"
        
        c4.markdown(f"<div class='stat-box'><div class='stat-label'>Nejoblíbenější barva</div><div class='stat-val' style='color:{COLORS.get(fav_color, '#333')};'>{fav_color}</div></div>", unsafe_allow_html=True)
        
        c5.markdown(f"<div class='stat-box'><div class='stat-label'>Výhry / Prohry</div><div class='stat-val'><span style='color:green'>{s['total_wins']}</span> / <span style='color:red'>{s['total_losses']}</span></div></div>", unsafe_allow_html=True)
        
        win_rate = 0
        if s['total_bets'] > 0: win_rate = int((s['total_wins'] / s['total_bets']) * 100)
        c6.markdown(f"<div class='stat-box'><div class='stat-label'>Úspěšnost sázek</div><div class='stat-val'>{win_rate} %</div></div>", unsafe_allow_html=True)
        
        c7, c8, c9 = st.columns(3)
        c7.markdown(f"<div class='stat-box'><div class='stat-label'>Největší trefa</div><div class='stat-val'>+{s['max_win']} CC</div></div>", unsafe_allow_html=True)
        c8.markdown(f"<div class='stat-box'><div class='stat-label'>Aktuální Streak</div><div class='stat-val' style='color:#ff4500'>🔥 {user['streak']}</div></div>", unsafe_allow_html=True)
        c9.markdown(f"<div class='stat-box'><div class='stat-label'>Nejvyšší Streak</div><div class='stat-val' style='color:#fd7e14'>🏆 {s.get('max_streak', 0)}</div></div>", unsafe_allow_html=True)

   # --- GRAFY ---
    elif page == "GRAFY":
        st.title("📈 Tržní data")
        
        st.subheader("Aktuálně vsazeno (Live)")
        current_bets = {}
        for u in data["users"].values():
            for b in u["bets"]:
                if b["st"] == "PENDING":
                    current_bets[b["c"]] = current_bets.get(b["c"], 0) + b["a"]
        
        if current_bets:
            df = pd.DataFrame(list(current_bets.items()), columns=['Barva', 'Částka'])
            df['Hex'] = df['Barva'].map(COLORS)
            c = alt.Chart(df).mark_bar(stroke='black', strokeWidth=2).encode(
                x=alt.X('Barva', sort='-y'), y='Částka',
                color=alt.Color('Barva', scale=alt.Scale(domain=list(df['Barva']), range=list(df['Hex'])), legend=None),
                tooltip=['Barva', 'Částka']
            ).properties(height=400)
            st.altair_chart(c, use_container_width=True)
        else:
            st.info("Zatím žádné sázky.")
            
        st.divider()
        st.subheader("Sázky z minulého kola")
        last_stats = data["market"].get("last_round_stats", {})
        if last_stats:
            df_last = pd.DataFrame(list(last_stats.items()), columns=['Barva', 'Částka'])
            df_last['Hex'] = df_last['Barva'].map(COLORS)
            c_last = alt.Chart(df_last).mark_bar(stroke='black', strokeWidth=2).encode(
                x=alt.X('Barva', sort='-y'), y='Částka',
                color=alt.Color('Barva', scale=alt.Scale(domain=list(df_last['Barva']), range=list(df_last['Hex'])), legend=None),
                tooltip=['Barva', 'Částka']
            ).properties(height=300)
            st.altair_chart(c_last, use_container_width=True)
        else:
            st.caption("Data nejsou k dispozici.")
        
        # --- NOVÝ GRAF VÝVOJE KURZŮ ---
        st.divider()
        st.subheader("📈 Vývoj kurzů v čase")
        
        odds_hist = data["market"].get("odds_history", {})
        
        # Zkontrolujeme, jestli už máme nějaká data (alespoň 1 kolo za námi)
        if odds_hist and any(len(h) > 0 for h in odds_hist.values()):
            # Interaktivní posuvník pro hráče (ukáže 5 až 50 kol)
            limit_kol = st.slider("Zobrazit posledních X kol:", min_value=5, max_value=50, value=15, step=5)
            
            hist_records = []
            for c_name, history in odds_hist.items():
                # Vezmeme jen vybraný počet posledních kol
                zobrazeno = history[-limit_kol:]
                for i, val in enumerate(zobrazeno):
                    hist_records.append({
                        "Kolo": i + 1,  # Relativní číslování (1 je nejstarší zobrazené)
                        "Barva": c_name,
                        "Kurz": val
                    })
            
            df_hist = pd.DataFrame(hist_records)
            
            # 1. FIX BÍLÉ BARVY: Pro graf změníme čistě bílou na světle šedou, aby byla vidět na pozadí
            graf_barvy = list(COLORS.values())
            bila_index = list(COLORS.keys()).index("Bílá")
            graf_barvy[bila_index] = "#d1d1d1" # Ztmavená bílá (světle šedá)
            
            # 2. INTERAKTIVITA: Vytvoříme výběr kliknutím na legendu
            highlight = alt.selection_point(fields=['Barva'], bind='legend')
            
            # 3. VYKRESLENÍ GRAFU S EFEKTEM VYBLEDNUTÍ
            c_line = alt.Chart(df_hist).mark_line(strokeWidth=4, point=alt.OverlayMarkDef(size=70)).encode(
                x=alt.X('Kolo:O', title='Časová osa (Kola)'),
                y=alt.Y('Kurz:Q', title='Kurz (CC)', scale=alt.Scale(zero=False)),
                color=alt.Color('Barva:N', 
                                scale=alt.Scale(domain=list(COLORS.keys()), range=graf_barvy), 
                                legend=alt.Legend(title="👆 Klikni na barvu", symbolStrokeWidth=3, symbolSize=200)),
                opacity=alt.condition(highlight, alt.value(1.0), alt.value(0.1)), # Vybraná svítí, ostatní jsou na 10 %
                tooltip=['Barva', 'Kolo', 'Kurz']
            ).add_params(
                highlight
            ).properties(height=450)
            
            st.altair_chart(c_line, use_container_width=True)
            
            # 👇 TOTO SEM VLOŽÍŠ 👇
            # --- EXPORT DAT PRO VÝZKUM ---
            csv_data = df_hist.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button(
                label="📥 Stáhnout historii kurzů", 
                data=csv_data, 
                file_name='historie_kurzu.csv', 
                mime='text/csv'
            )
            # 👆 KONEC VLOŽENÉHO KÓDU 👆
        else:
            st.info("Zatím není dostatek dat pro vývoj kurzů (musí proběhnout alespoň 1 kolo).")
        # --- NOVÝ GRAF VÝVOJE BOHATSTVÍ HRÁČŮ ---
        st.divider()
        st.subheader("💰 Vývoj bohatství hráčů")
        
        bal_hist = data["market"].get("bal_history", {})
        
        # TADY JE TA OPRAVA Z > 1 NA > 0
        if bal_hist and any(len(h) > 0 for h in bal_hist.values()):
            # DŮLEŽITÉ: key="slider_bal" zabraňuje konfliktu s prvním posuvníkem
            limit_kol_bal = st.slider("Zobrazit posledních X kol (Hráči):", min_value=5, max_value=50, value=15, step=5, key="slider_bal")
            
            bal_records = []
            for uname, history in bal_hist.items():
                zobrazeno = history[-limit_kol_bal:]
                for i, val in enumerate(zobrazeno):
                    bal_records.append({
                        "Kolo": i + 1,
                        "Hráč": uname,
                        "Zůstatek": val
                    })
            
            df_bal = pd.DataFrame(bal_records)
            
            # INTERAKTIVITA: Výběr hráče kliknutím
            highlight_bal = alt.selection_point(fields=['Hráč'], bind='legend')
            
            # VYKRESLENÍ GRAFU
            c_bal = alt.Chart(df_bal).mark_line(strokeWidth=4, point=alt.OverlayMarkDef(size=70)).encode(
                x=alt.X('Kolo:O', title='Časová osa (Kola)'),
                y=alt.Y('Zůstatek:Q', title='Zůstatek (CC)', scale=alt.Scale(zero=False)),
                # Barvy hráčů se přidělí automaticky (Altair má zabudovanou pěknou paletu)
                color=alt.Color('Hráč:N', legend=alt.Legend(title="👆 Klikni na hráče", symbolStrokeWidth=3, symbolSize=200)),
                opacity=alt.condition(highlight_bal, alt.value(1.0), alt.value(0.1)), # Průhlednost
                tooltip=['Hráč', 'Kolo', 'Zůstatek']
            ).add_params(
                highlight_bal
            ).properties(height=450)
            
            st.altair_chart(c_bal, use_container_width=True)
        else:
            st.info("Zatím není dostatek dat pro vývoj bohatství hráčů (musí proběhnout alespoň 1 kolo).")

      # --- AI PREDIKCE VÍTĚZE (Hledání skrytých vzorců a Backtesting) ---
        st.divider()
        st.subheader("Predikce výhry")
        st.caption("Model analyzuje posledních 15 kol a vyhodnocuje jejich šance na výhru")
        
        predikce_vyhry = []
        celkova_vaha = 0
        
        # --- 1. HLEDÁNÍ SKRYTÝCH VZORCŮ (Až 15 kol dozadu) ---
        for c_name, current_odd in data["market"]["colors"].items():
            history = data["market"]["odds_history"].get(c_name, [current_odd])
            
            # Bereme posledních max 15 kol pro hlubokou analýzu
            analyzovana_historie = history[-15:] if len(history) >= 15 else history
            
            # A) Základní šance (převrácená hodnota kurzu)
            zakladni_sance = 1.0 / current_odd
            
            # B) Skryté vzorce: Dlouhodobé Momentum
            trend_bonus = 0
            if len(analyzovana_historie) >= 3:
                # Rozdíl mezi začátkem sledovaného období a současností
                dlouhodoba_zmena = analyzovana_historie[0] - current_odd
                trend_bonus = dlouhodoba_zmena * 0.05
            
            # C) Skryté vzorce: Detekce tlakového hrnce (Mean Reversion)
            # Zjišťuje, jestli barva už dlouho neprohrávala (kurz jen roste)
            rust_v_rade = 0
            for i in range(1, len(analyzovana_historie)):
                if analyzovana_historie[i] > analyzovana_historie[i-1]:
                    rust_v_rade += 1
                else:
                    rust_v_rade = 0
            
            # Pokud prohrává (roste) 4 a více kol v řadě, AI tuší, že "už to musí prasknout"
            tlakovy_bonus = 0
            if rust_v_rade >= 4:
                tlakovy_bonus = rust_v_rade * 0.08
                
            # Celkové skóre = Základ + Momentum + Tlakový hrnec
            skore = max(0.01, zakladni_sance + trend_bonus + tlakovy_bonus)
            celkova_vaha += skore
            
            predikce_vyhry.append({
                "Barva": c_name,
                "Surove_Skore": skore
            })
            
        # --- 2. PŘEPOČET NA PROCENTA ---
        graf_data = []
        for p in predikce_vyhry:
            procenta = (p["Surove_Skore"] / celkova_vaha) * 100
            graf_data.append({
                "Barva": p["Barva"],
                "Šance na výhru (%)": round(procenta, 1)
            })
            
        df_ai = pd.DataFrame(graf_data)
        
        # --- 3. VÝPOČET HISTORICKÉ ÚSPĚŠNOSTI AI (BACKTESTING) ---
        spravne_tipy = 0
        celkem_testovano = 0
        
        # Ochrana proti chybám: vezmeme jakoukoliv barvu pro zjištění délky historie
        if data["market"]["colors"]:
            referencni_barva = list(data["market"]["colors"].keys())[0]
            delka_historie = len(data["market"]["odds_history"].get(referencni_barva, []))
            
            # Můžeme testovat až když máme víc jak 3 kola dat
            if delka_historie > 3:
                for i in range(3, delka_historie):
                    # Zjištění, kdo reálně vyhrál v minulém kole 'i' (ten, komu nejvíc klesl kurz)
                    skutecny_vitez = None
                    nejvetsi_pokles = 0
                    for c_name in data["market"]["colors"]:
                        hist = data["market"]["odds_history"].get(c_name, [])
                        if len(hist) > i:
                            pokles = hist[i-1] - hist[i]
                            if pokles > nejvetsi_pokles:
                                nejvetsi_pokles = pokles
                                skutecny_vitez = c_name
                                
                    # Co by na to tipovalo AI, kdyby stálo v kole 'i-1'?
                    tip_ai = None
                    nej_skore = -1
                    for c_name in data["market"]["colors"]:
                        hist = data["market"]["odds_history"].get(c_name, [])
                        if len(hist) >= i:
                            k_minuly = hist[i-1]
                            # Jednoduchá AI simulace pro minulost
                            skore_minule = (1.0 / k_minuly) + ((hist[i-3] - k_minuly) * 0.05) if i>=3 else (1.0 / k_minuly)
                            if skore_minule > nej_skore:
                                nej_skore = skore_minule
                                tip_ai = c_name
                                
                    if skutecny_vitez and tip_ai == skutecny_vitez:
                        spravne_tipy += 1
                    celkem_testovano += 1
                    
                uspesnost_procenta = (spravne_tipy / celkem_testovano) * 100 if celkem_testovano > 0 else 0
            else:
                uspesnost_procenta = 0.0
                
            # Zobrazení krásné "Metriky" nad grafem
            nahodna_sance = (1 / len(data["market"]["colors"])) * 100 if len(data["market"]["colors"]) > 0 else 7.1
            st.metric(
                label="📊 Historická přesnost modelu", 
                value=f"{uspesnost_procenta:.1f} %", 
                delta=f"{uspesnost_procenta - nahodna_sance:.1f} % oproti náhodnému hádání",
            )

        # --- 4. VYKRESLENÍ GRAFU ---
        # Fix pro bílou barvu
        graf_barvy_ai = list(COLORS.values()) if 'COLORS' in globals() else []
        if 'COLORS' in globals() and "Bílá" in COLORS:
            bila_index_ai = list(COLORS.keys()).index("Bílá")
            graf_barvy_ai[bila_index_ai] = "#d1d1d1"
            
        bars = alt.Chart(df_ai).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
            x=alt.X('Barva:N', sort='-y', title='Barvy'),
            y=alt.Y('Šance na výhru (%):Q', title='Pravděpodobnost výhry (%)'),
            color=alt.Color('Barva:N', scale=alt.Scale(domain=list(COLORS.keys()), range=graf_barvy_ai) if 'COLORS' in globals() else alt.value('blue'), legend=None),
            tooltip=['Barva', 'Šance na výhru (%)']
        )
        
        text = bars.mark_text(
            align='center',
            baseline='bottom',
            dy=-5,
            fontSize=15,
            fontWeight='bold'
        ).encode(
            text=alt.Text('Šance na výhru (%):Q', format='.1f')
        )
        
        c_ai = (bars + text).properties(height=400)
        st.altair_chart(c_ai, use_container_width=True)
        
        # Vyhlášení favorita
        if graf_data:
            nejlepsi = max(graf_data, key=lambda x: x["Šance na výhru (%)"])
            st.success(f"🏆 **Největší favorit:**  **{nejlepsi['Barva']}** ({nejlepsi['Šance na výhru (%)']} %).")
        # --- MAKROEKONOMICKÝ DASHBOARD (Zbraň B) ---
        st.divider()
        st.subheader("🌍 Makroekonomika a rozložení bohatství")
        st.caption("Analýza celkové ekonomiky trhu.")

        # 1. Výpočet celkového bohatství (Money Supply) a příprava dat
        vsechny_zustatky = sorted([int(u["bal"]) for u in data["users"].values() if u["bal"] >= 0])
        pocet_hracu = len(vsechny_zustatky)
        celkove_bohatstvi = sum(vsechny_zustatky)

        if pocet_hracu > 1 and celkove_bohatstvi > 0:
            # 2. Výpočet Giniho koeficientu (0 = absolutní rovnost, 1 = jeden vlastní vše)
            kumulativni_bohatstvi = sum((i + 1) * b for i, b in enumerate(vsechny_zustatky))
            gini = (2.0 * kumulativni_bohatstvi) / (pocet_hracu * celkove_bohatstvi) - (pocet_hracu + 1.0) / pocet_hracu
            
            # Metriky (Výsledky bez složitého grafu)
            c1, c2, c3 = st.columns(3)
            c1.metric("Celkové CC v oběhu", f"{celkove_bohatstvi} CC", help="kolik peněz je celkem ve hře.")
            c2.metric("Průměr na hráče", f"{int(celkove_bohatstvi / pocet_hracu)} CC")
            
            # Gini s barvičkou
            gini_color = "normal" if gini < 0.4 else "inverse"
            c3.metric("Giniho koeficient", f"{gini:.2f}", delta="Ideál je 0.0" if gini < 0.4 else "Vysoká nerovnost!", delta_color=gini_color, help="0 = všichni mají stejně, 1 = jeden uživatel vlastní všechno.")

            # Textové zhodnocení pro SOČ
            if gini > 0.5:
                st.warning("⚠️ **Ekonomické varování:** Bohatství je silně koncentrováno. Malé procento hráčů ovládá většinu trhu.")
            elif gini < 0.2:
                st.success("⚖️ **Ekonomická stabilita:** Bohatství je mezi hráče rozděleno velmi rovnoměrně.")
            else:
                st.info("📊 **Tržní standard:** Hra vykazuje běžnou majetkovou nerovnost, podobnou reálným ekonomikám.")

        else:
            st.info("Zatím není dostatek dat pro makroekonomickou analýzu.")

    # --- OBCHOD ---
    elif page == "OBCHOD":
        st.title("🛒 Obchod")
        t1, t2 = st.tabs(["Povýšení", "Věci"])
        with t1:
            if user["rank"] < 5:
                nr = RANKS[user["rank"]+1]
                p = [500, 2000, 5000, 15000, 50000][user["rank"]]
                
                st.info(f"Další: **{nr['name']}** (Cena: {p} CC)\n\n💰 **Zvyšuje denní příjem na {nr['inc']} CC**")
                
                if st.button("Koupit hodnost"):
                    if user["bal"] >= p:
                        user["bal"] -= p; user["rank"] += 1; update_user_stats(user,0,0,0,"",p); save_data(data); st.balloons(); st.rerun()
                    else: st.error("Chybí peníze")
        with t2:
            st.write(f"**Batoh:** {current_items} / {max_slots}")
            for item in data["shop"]:
                p = item["curr_p"]; base = item["base_p"]
                if "Kbelík" in item["name"]: p = base + (user["slots"] * 2000)
                
                price_display = f"**{p} CC**"
                if p < base: price_display = f"<span style='color:gray;text-decoration:line-through'>{base}</span> <span style='color:#198754;font-weight:bold'>{p} CC (-{int((1-p/base)*100)}%)</span>"
                elif p > base: price_display = f"<span style='color:gray;text-decoration:line-through'>{base}</span> <span style='color:#dc3545;font-weight:bold'>{p} CC (+{int((p/base-1)*100)}%)</span>"

                c1, c2 = st.columns([3,1])
                c1.markdown(f"**{item['name']}** {price_display}", unsafe_allow_html=True)
                c1.caption(f"ℹ️ {item['desc']}")
                
                if c2.button("Koupit", key=f"b_{item['name']}"):
                    if user["bal"] >= p:
                        if "Titanová" in item["name"] and "🛡️ Titanová Přilba" in user["inv"]:
                            st.error("Limit: 1 ks.")
                        elif item["type"] == "upgrade":
                            user["bal"] -= p; user["slots"] += 1; update_user_stats(user,0,0,0,"",p); save_data(data); st.success("Batoh zvětšen!"); st.rerun()
                        elif current_items < max_slots:
                            user["bal"] -= p; user["inv"].append(item["name"]); update_user_stats(user,0,0,0,"",p); save_data(data); st.success("Koupeno!"); st.rerun()
                        else: st.error("Batoh je plný!")
                    else: st.error("Chybí peníze")
                st.divider()
        

    # --- BATOH ---
    elif page == "BATOH":
        st.title("🎒 Batoh")
        if not user["inv"]: st.info("Prázdno.")
        
        for i, item_name in enumerate(user["inv"]):
            c1, c2 = st.columns([3,1])
            c1.write(f"📦 {item_name}")
            
            item_def = next((x for x in data["shop"] if x["name"] == item_name), None)
            item_type = item_def["type"] if item_def else "unknown"
            
            # --- CHYTRÉ ROZTŘÍDĚNÍ TLAČÍTEK ---
            if "Svačina" in item_name:
                # Svačinu můžeme dál normálně jíst přímo z batohu
                if c2.button("Sníst (+50 CC)", key=f"use_{i}"):
                    user["bal"] += 50
                    st.success("+50 CC")
                    log_item_usage(user, "Svačina", "Doplněno")
                    user["inv"].pop(i)
                    save_data(data)
                    st.rerun()
            elif item_type == "use": 
                # Ostatní "use" itemy (Cihla, BOZP...) se už naklikávají na úvodní stránce
                c2.caption("🎒 Používá se při sázce")
            elif item_type == "passive": 
                c2.caption("🛡️ Automatické")
            elif item_type == "atk": 
                c2.caption("👊 Použij v Žebříčku")

        st.divider()
        with st.expander("📜 Historie použití itemů"):
            for h in reversed(user["item_history"]):
                st.markdown(f"<div class='hist-item'>🔹 <b>{h['item']}</b> - {h['detail']} <span style='float:right;font-size:0.8em'>{h['tm']}</span></div>", unsafe_allow_html=True)

    # --- BANKA ---
    elif page == "BANKA":
        st.title("🏦 Banka")
        st.subheader("💸 Poslat peníze")
        col1, col2 = st.columns(2)
        prijemce = col1.selectbox("Komu:", [u for u in data["users"].keys() if u != me])
        castka = col2.number_input("Kolik:", min_value=1, max_value=max(1, int(user["bal"])))
        if st.button("Odeslat platbu"):
            if user["bal"] >= castka:
                user["bal"] -= castka; user["trans"].append({"type": "out", "amt": castka, "src": prijemce, "tm": get_time()})
                rec_user = data["users"][prijemce]; rec_user["bal"] += castka
                if "trans" not in rec_user: rec_user["trans"] = []
                rec_user["trans"].append({"type": "in", "amt": castka, "src": me, "tm": get_time()})
                update_user_stats(rec_user, 0, 0, 0, "", 0, castka)
                data["chat"].append({"u": "BANKA", "t": f"{me} poslal {castka} CC hráči {prijemce}.", "tm": get_time(), "r": "BOT"})
                save_data(data); st.success("Odesláno!"); st.rerun()
            else: st.error("Nemáš dost peněz.")
        st.divider(); st.subheader("📜 Historie transakcí")
        if not user["trans"]: st.info("Žádné transakce.")
        else:
            for t in reversed(user["trans"]):
                if t["type"] == "in": st.markdown(f"<div class='trans-in'>⬇️ Přišlo: <b>+{t['amt']} CC</b> ({t['src']}) <small>{t['tm']}</small></div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='trans-out'>⬆️ Odešlo: <b>-{t['amt']} CC</b> ({t['src']}) <small>{t['tm']}</small></div>", unsafe_allow_html=True)

    # --- CHAT ---
    elif page == "CHAT":
        st.title("📢 Chat")
        with st.container():
            for m in data["chat"][-50:]:
                u_role = m.get('r', 'Dělník'); role_class = "bg-0"
                for r in RANKS: 
                    if r["name"] == u_role: role_class = r["css"]
                if u_role == "ADMIN": role_class = "bg-admin"
                
                streak_html = ""
                sender_data = data["users"].get(m['u'])
                if sender_data and sender_data.get('streak', 0) > 0:
                    streak_html = f"<span class='streak'>🔥 {sender_data['streak']}</span>"

                cls = "msg-sys" if m['u'] in ["SYS","EVENT","BANKA","SHOP"] else "msg-user"
                if m['u'] == "EVENT": cls = "msg-event"
                
                if m['u'] in ["SYS", "EVENT", "BANKA", "SHOP"]:
                    st.markdown(f"<div class='{cls}'><small>{m['tm']}</small> <b>{m['u']}</b>: {m['t']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='{cls}'><small>{m['tm']}</small> <b>{m['u']}</b> <span class='badge {role_class}'>{u_role}</span>{streak_html}: {m['t']}</div>", unsafe_allow_html=True)

        with st.form("cf"):
            t = st.text_input("Zpráva")
            if st.form_submit_button("Odeslat") and t:
                my_rank_name = RANKS[rid]['name']
                if st.session_state.get("admin_ok"): my_rank_name = "ADMIN"
                data["chat"].append({"u":me, "t":t, "tm":get_time(), "r": my_rank_name})
                save_data(data); st.rerun()

    # --- NÁPOVĚDA (KOMPLETNÍ) ---
    elif page == "📚 NÁPOVĚDA":
        st.title("📚 Herní Manuál")
        
        with st.expander("❓ ZÁKLADNÍ PRINCIP", expanded=True):
            st.write("""
            **Cíl hry:** Získat co nejvíce Cihlakoinů (CC) a stát se Cihlobaronem.
            1.  **Výplata:** Každý herní den si vyzvedni mzdu v sekci DOMŮ.
            2.  **Sázky:** Vsaď na barvu. Pokud vyhraje, získáš násobek vkladu. Předměty můžeš přidat přímo k sázce!
            3.  **Streak:** Pokud vyhraješ všechny své sázky v kole, roste ti 🔥 Streak. Jediná chyba a padáš na nulu.
            """)
        
        st.write("---")
        st.subheader("🎒 KATALOG PŘEDMĚTŮ")
        
        st.markdown("""
        ### 🔵 Aktivní předměty (Použití u sázky)
        *Většinu těchto předmětů si vybíráš z batohu **přímo na úvodní stránce při zadávání sázky**.*

        **🧃 Svačina (Cena: 50 CC)**
        * **Co dělá:** Okamžitě ti přidá 50 CC do peněženky.
        * **Jak použít:** *Výjimka!* Jdi do **Batohu** a klikni na "Sníst".
        * **Kdy koupit:** Když jsi úplně na dně a nemáš ani na vklad. Je to záchranná brzda.

        **🧱 Zlatá Cihla (Cena: 1000 CC)**
        * **Co dělá:** Zdvojnásobí tvou výhru.
        * **Jak použít:** Kup ji -> Jdi vsadit na úvodní stránku -> Vyber ji z nabídky předmětů pod sázkou.
        * **Riziko:** Pokud sázku prohraješ, o cihlu přijdeš a nedostaneš nic. Pokud vyhraješ, získáš balík.

        **👷 BOZP Helma (Cena: 300 CC)**
        * **Co dělá:** Funguje jako pojištění sázky.
        * **Jak použít:** Kup ji -> Jdi vsadit na úvodní stránku -> Vyber ji z nabídky předmětů pod sázkou.
        * **Efekt:** Pokud tvá sázka **prohraje**, vrátí se ti **50 % vkladu**. Pokud vyhraješ, helma se spotřebuje bez efektu.

        ---
        ### 🟡 Pasivní předměty (Fungují automaticky)
        *Stačí je mít v batohu.*

        **🛡️ Titanová Přilba (Cena: 3000 CC)**
        * **Co dělá:** Chrání tě před útoky ostatních hráčů.
        * **Efekt:** Když na tebe někdo použije *Podkopnutí* nebo *Fantoma*, máš **80% šanci**, že útok odrazíš a nic se ti nestane.
        * **Pozor:** Pokud helma úspěšně odrazí útok, **zničí se** (zmizí z batohu). Musíš koupit novou. Můžeš mít u sebe jen jednu.

        ---
        ### 🔴 Útočné předměty (Použij v Žebříčku)
        *Slouží k sabotáži soupeřů.*

        **🦶 Podkopnutí (Cena: 8000 CC)**
        * **Co dělá:** Zraní vybraného hráče.
        * **Jak použít:** Jdi do Žebříčku -> Najdi oběť -> Klikni na tlačítko 👊.
        * **Efekt:** Pokud oběť nemá Titanovou helmu (nebo selže její obrana), hráč je **ZRANĚN**. Zraněný hráč nemůže sázet, dokud ho Admin nevyléčí nebo nezačne nový den.
        * **Info:** V chatu všichni uvidí, že jsi útočil ty.

        **👻 Fantom (Cena: 20000 CC)**
        * **Co dělá:** To samé co Podkopnutí, ale **anonymně**.
        * **Efekt:** V chatu se napíše "Někdo zaútočil...", ale tvé jméno zůstane skryté. Ideální pro tichou pomstu.

        ---
        ### 🟣 Vylepšení
        **🪣 Větší Kbelík (Cena: roste)**
        * **Co dělá:** Trvale zvětší kapacitu batohu o +2 místa.
        * **Cena:** S každým nákupem je dražší.
        """)

        st.write("---")
        st.subheader("⚡ EVENTY (UDÁLOSTI)")
        st.write("Každý den při otevření trhu může náhodně nastat jedna z těchto situací:")
        
        st.info("""
        **🏷️ CENOVÝ ŠOK**
        Ceny v obchodě se zblázní! Některé předměty (kromě Svačiny a Kbelíku) mohou zlevnit až o 95 %, jiné zase brutálně zdražit. Sleduj obchod každé ráno!
        """)
        
        st.success("""
        **🎁 NÁLEZ MĚDI**
        Šťastný den na stavbě! Všichni hráči automaticky dostanou bonus **150 CC**.
        """)
        
        st.error("""
        **🔥 PÁD LEŠENÍ**
        Smůla. Všem hráčům se strhne **10 %** z jejich aktuálního zůstatku.
        """)
        
        st.warning("""
        **🚀 MEGA BOOST**
        Tři náhodné barvy dostanou obrovský kurz **5.0x**! Tyto barvy budou na hlavní stránce zářit zlatě. Ideální čas zariskovat.
        """)
        
        st.error("""
        **👮 PROVĚRKA BOZP**
        Nejhorší event. Přijde kontrola. U každého hráče je **50% šance**, že dostane pokutu ve formě úrazu.
        * Pokud máš smůlu, jsi **ZRANĚN** a nemůžeš ten den sázet.
        * **Helmy proti tomuto eventu nefungují!** Je to úřední moc.
        """)

    # --- ADMIN ---
    elif page == "ADMIN":
        st.title("⚙️ Admin")
        if "admin_ok" not in st.session_state: st.session_state.admin_ok = False
        if not st.session_state.admin_ok:
            if st.text_input("Heslo", type="password") == "admin123": st.session_state.admin_ok = True; st.rerun()
        else:
            if st.button("🔒 Odhlásit"): st.session_state.admin_ok = False; st.rerun()
            
            t1, t2, t3, t4 = st.tabs(["Trh", "Hráči (Hesla)", "Obchod (Ceny)", "Eventy"])
            with t1:
                status = data["market"]["status"]
                btn_txt = "🟢 OTEVŘÍT TRH (Start)" if status == "CLOSED" else "🔴 ZAVŘÍT TRH"
                if st.button(btn_txt):
                    ns = "OPEN" if status=="CLOSED" else "CLOSED"
                    data["market"]["status"] = ns
                    if ns == "OPEN":
                        for u in data["users"].values(): 
                            u["pay"] = False; u["hp"] = "OK" 
                        if "original_odds" in data["market"]: del data["market"]["original_odds"]
                        
                        msg_shop = trigger_shop_fluctuation(data)
                        
                        roll = random.randint(1, 100)
                        msg = None
                        if roll <= 10: msg = trigger_game_event(data, "MEGA")
                        elif roll <= 30: msg = trigger_game_event(data, "COPPER")
                        elif roll <= 40: msg = trigger_game_event(data, "SCAFFOLD")
                        elif roll >= 96: msg = trigger_game_event(data, "PROVERKA")
                        
                        st.markdown(f"🛍️ **Shop:** {msg_shop}", unsafe_allow_html=True)
                        if msg:
                            if "PROVĚRKA" in msg or "Pád" in msg:
                                st.warning(msg)
                            else:
                                st.success(msg)

                    if ns == "CLOSED":
                        for item in data["shop"]: item["curr_p"] = item["base_p"]
                        if "original_odds" in data["market"]:
                            data["market"]["colors"] = data["market"]["original_odds"]
                            del data["market"]["original_odds"]
                        data["chat"].append({"u":"SYS", "t":"Trh zavřen. Ceny v obchodě resetovány.", "tm":get_time(), "r":"BOT"})

                    save_data(data); st.rerun()
                
                with st.expander("🔧 Kurzy"):
                    c_edit = st.selectbox("Barva", list(COLORS.keys()))
                    val_edit = st.number_input("Nový kurz", 1.1, 100.0, data["market"]["colors"][c_edit], 0.1)
                    if st.button("Uložit kurz"):
                        data["market"]["colors"][c_edit] = val_edit
                        data["chat"].append({"u":"SYS", "t":f"Admin změnil kurz na {c_edit} na {val_edit}x.", "tm":get_time(), "r":"BOT"})
                        save_data(data); st.success("Změněno.")
                
                # --- TLAČÍTKO PRO OPRAVU ZASEKLÝCH KURZŮ ---
                if st.button("♻️ RESETOVAT KURZY NA 2.0 (Fix)"):
                    for c in COLORS: data["market"]["colors"][c] = 2.0
                    if "original_odds" in data["market"]: del data["market"]["original_odds"]
                    save_data(data); st.success("Kurzy resetovány.")
                # -------------------------------------------

                st.divider()
                winners = st.multiselect("Vítězné barvy:", list(COLORS.keys()))
                if st.button("✅ VYPLATIT VÝHRY (Uzdravit)"):
                    if not winners: st.error("Vyber barvu!")
                    else:
                        data["market"]["prev_colors"] = data["market"]["colors"].copy()
                        round_bets = {}
                        round_profits = {}
                        count = 0
                        
                        for uname, u in data["users"].items():
                            u["hp"] = "OK"
                            net_profit = 0
                            has_win = False
                            has_loss = False
                            
                            for b in u["bets"]:
                                if b["st"] == "PENDING":
                                    round_bets[b["c"]] = round_bets.get(b["c"], 0) + b["a"]
                                    
                                    # Získání použitých itemů a starého bonusu (pro zpětnou kompatibilitu)
                                    pouzite_itemy = b.get("items", [])
                                    stary_bonus = str(b.get("bonus", ""))
                                    
                                    if b["c"] in winners:
                                        # --- VÝHRA ---
                                        vklad = b["a"]
                                        kurz = b["o"]
                                        cisty_zisk = (vklad * kurz) - vklad
                                        
                                        if "🧱 Zlatá Cihla" in pouzite_itemy or "Zlatá" in stary_bonus:
                                            cisty_zisk = cisty_zisk * 2
                                            
                                        w = int(vklad + cisty_zisk)
                                        
                                        u["bal"] += w
                                        b["st"] = "WON"
                                        net_profit += cisty_zisk
                                        update_user_stats(u, cisty_zisk, 0, 0, "")
                                        count += 1
                                        has_win = True
                                    else:
                                        # --- PROHRA ---
                                        loss = b["a"]
                                        if "👷 BOZP Helma" in pouzite_itemy or "BOZP" in stary_bonus or b.get("insurance") == True:
                                            vraceno = int(b["a"] * 0.5)
                                            u["bal"] += vraceno
                                            b["insurance"] = True
                                            net_profit -= (loss - vraceno)
                                            update_user_stats(u, 0, (loss - vraceno), 0, "")
                                        else:
                                            net_profit -= loss
                                            update_user_stats(u, 0, loss, 0, "")
                                            
                                        b["st"] = "LOST"
                                        has_loss = True
                            
                            if has_win and not has_loss:
                                u["streak"] += 1
                                if u["streak"] > u["stats"]["max_streak"]: u["stats"]["max_streak"] = u["streak"]
                            elif has_loss: u["streak"] = 0
                            
                            if net_profit != 0: round_profits[uname] = net_profit
                        
                        data["market"]["last_round_stats"] = round_bets
                        win_msg = f"🏆 Vítězové: {', '.join(winners)} | Vyplaceno {count} tiketů."
                        if round_profits:
                            best_p = max(round_profits, key=round_profits.get)
                            worst_p = min(round_profits, key=round_profits.get)
                            win_msg += f" 👑 Boháč: {best_p} (+{round_profits[best_p]}) | 💀 Smolař: {worst_p} ({round_profits[worst_p]})"
                        
                        data["chat"].append({"u":"SYS", "t":win_msg, "tm":get_time(), "r":"BOT"})
                        
                        # --- VÝPOČET KURZŮ MARKET BALANCE 2.0 ---
                        
                        # Zajištění existence nových slovníků (zpětná kompatibilita)
                        if "odds_history" not in data["market"]:
                            data["market"]["odds_history"] = {c: [data["market"]["colors"].get(c, 2.0)] for c in COLORS}
                        if "neaktivita_count" not in data["market"]:
                            data["market"]["neaktivita_count"] = {c: 0 for c in COLORS}

                        # 1. Zjištění počtu unikátních hráčů, kteří vsadili
                        celkem_sazejicich = 0
                        hraci_na_barve = {c: 0 for c in COLORS}
                        
                        for uname, u in data["users"].items():
                            vsadil = False
                            for b in u["bets"]:
                                if b["st"] in ["WON", "LOST"] and b["c"] in COLORS: # Pouze právě vyhodnocené sázky
                                    hraci_na_barve[b["c"]] += 1
                                    vsadil = True
                            if vsadil:
                                celkem_sazejicich += 1

                        celkovy_objem = sum(round_bets.values())

                        for c in data["market"]["colors"]:
                            k_n = data["market"]["colors"][c]
                            
                            # 2. Výpočet vážené popularity (P_final)
                            w_money = round_bets.get(c, 0) / celkovy_objem if celkovy_objem > 0 else 0
                            w_social = hraci_na_barve.get(c, 0) / celkem_sazejicich if celkem_sazejicich > 0 else 0
                            p_final = (0.7 * w_money) + (0.3 * w_social)

                            # 3. Asymetrická tržní změna
                            if c in winners:
                                # Vítěz spadne
                                zmena = -(0.6 + p_final * 0.4)
                                data["market"]["neaktivita_count"][c] = 0
                            else:
                                # Poražený roste
                                zmena = 0.1 + (0.1 * (1 - p_final))
                                data["market"]["neaktivita_count"][c] += 1
                                
                            # 4. Podmíněná gravitace (pouze pro neaktivní)
                            tah_gravitace = (2.0 - k_n) * 0.3 if data["market"]["neaktivita_count"][c] > 1 else 0
                            
                            # 5. Šum
                            sum_trhu = random.uniform(-0.1, 0.1)
                            
                            # 6. Výpočet a zápis nového kurzu
                            novy_kurz = k_n + zmena + tah_gravitace + sum_trhu
                            novy_kurz = round(max(1.1, novy_kurz), 1)
                            
                            data["market"]["colors"][c] = novy_kurz
                            data["market"]["odds_history"][c].append(novy_kurz)
                            
                            # Omezovač historie proti přetečení databáze (držíme jen posledních 50 kol)
                            if len(data["market"]["odds_history"][c]) > 50:
                                data["market"]["odds_history"][c].pop(0)

                        # ----------------------------------------------------
                        # (tady nahoře ti končí ten tvůj výpočet kurzů)
                        # ----------------------------------------------------

                        # 👇 TENTO BLOK SEM VLOŽ (dej pozor, aby to odsazení zleva bylo přesně jako u save_data) 👇
                        if "bal_history" not in data["market"]:
                            data["market"]["bal_history"] = {}
                        
                        for uname_history, u_data in data["users"].items():
                            if uname_history not in data["market"]["bal_history"]:
                                data["market"]["bal_history"][uname_history] = []
                            data["market"]["bal_history"][uname_history].append(u_data["bal"])
                            
                            if len(data["market"]["bal_history"][uname_history]) > 50:
                                data["market"]["bal_history"][uname_history].pop(0)
                        # 👆 KONEC VLOŽENÉHO BLOKU 👆

                        save_data(data); st.success("Hotovo!")
                        
            
            with t2:
                sel = st.selectbox("Hráč", list(data["users"].keys()))
                st.write(f"🔑 Heslo: **{data['users'][sel]['pass']}**")
                new_pass = st.text_input("Změnit heslo:", key="new_p")
                if st.button("Uložit heslo"):
                    if new_pass: data['users'][sel]['pass'] = new_pass; save_data(data); st.success("OK")
                
                st.divider()
                col_a, col_b = st.columns(2)
                if col_a.button("🏥 UZDRAVIT"): data["users"][sel]["hp"] = "OK"; save_data(data); st.success("OK")
                if col_b.button("🤕 ZRANIT"): data["users"][sel]["hp"] = "ZRANEN"; save_data(data); st.warning("OK")
                
                st.divider()
                amt = st.number_input("Částka", 1, 10000, 100)
                c1, c2 = st.columns(2)
                if c1.button("💰 Přidat"): 
                    data["users"][sel]["bal"] += amt; update_user_stats(data["users"][sel], 0, 0, 0, "", 0, amt)
                    save_data(data); st.success("OK")
                if c2.button("👮 Strhnout"): data["users"][sel]["bal"] -= amt; save_data(data); st.success("OK")
                st.divider(); st.write("⚠️ **Nebezpečná zóna**")
                if st.button("❌ SMAZAT HRÁČE"): del data["users"][sel]; save_data(data); st.rerun()

            with t3:
                st.subheader("Správa Obchodu")
                item_edit = st.selectbox("Vyber předmět:", [i["name"] for i in data["shop"]])
                selected_item = next(i for i in data["shop"] if i["name"] == item_edit)
                new_base_p = st.number_input("Nová ZÁKLADNÍ cena:", 1, 100000, selected_item["base_p"])
                if st.button("Uložit základní cenu"):
                    selected_item["base_p"] = new_base_p; selected_item["curr_p"] = new_base_p
                    save_data(data); st.success("Cena uložena.")
                st.divider()
                if st.button("🎲 Spustit CENOVÝ ŠOK"):
                    msg = trigger_shop_fluctuation(data); save_data(data); st.success(msg)

            with t4:
                st.subheader("Eventy")
                c1, c2, c3, c4 = st.columns(4)
                if c1.button("🎁 Měď"): msg = trigger_game_event(data, "COPPER"); save_data(data); st.success(msg)
                if c2.button("🔥 Lešení"): msg = trigger_game_event(data, "SCAFFOLD"); save_data(data); st.success(msg)
                if c3.button("🚀 Mega"): msg = trigger_game_event(data, "MEGA"); save_data(data); st.success(msg)
                if c4.button("👮 PROVĚRKA"): msg = trigger_game_event(data, "PROVERKA"); save_data(data); st.success(msg)
                if st.button("⚠️ RESET DATABÁZE"):
                    st.error("Pro smazání databáze jdi do Google Tabulky, smaž buňku A1 a napiš '{}'.")
