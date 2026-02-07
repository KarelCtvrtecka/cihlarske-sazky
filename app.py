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
    
    /* Karty */
    .bet-card { 
        background: white; border-radius: 12px; padding: 10px; text-align: center; 
        border: 2px solid #eee; box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
        position: relative; height: 150px; 
        display: flex; flex-direction: column; justify-content: center; align-items: center;
    }
    
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

COLORS = {
    "Červená": "#dc3545", "Modrá": "#0d6efd", "Žlutá": "#ffc107", "Zelená": "#198754",
    "Oranžová": "#fd7e14", "Fialová": "#6f42c1", "Bílá": "#ffffff", "Černá": "#212529",
    "Šedá": "#6c757d", "Hnědá": "#795548", "Růžová": "#d63384", "Béžová": "#f5f5dc",
    "Tyrkysová": "#20c997", "Azurová": "#0dcaf0"
}

RANKS = [
    {"name": "Pomocná síla", "inc": 50, "css": "bg-0"}, 
    {"name": "Kopáč", "inc": 60, "css": "bg-1"},
    {"name": "Zedník", "inc": 75, "css": "bg-2"}, 
    {"name": "Zásobovač", "inc": 120, "css": "bg-3"},
    {"name": "Stavbyvedoucí", "inc": 250, "css": "bg-4"}, 
    {"name": "Cihlobaron", "inc": 550, "css": "bg-5"}
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
# 💾 2. DATA A LOGIKA (Google Sheets - NUTNÉ PRO ONLINE)
# ==========================================
def get_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client.open("CihlyData").sheet1

def load_data():
    base = {
        "users": {},
        "market": {
            "status": "CLOSED", 
            "colors": {c: 2.0 for c in COLORS},
            "prev_colors": {c: 2.0 for c in COLORS},
            "last_round_stats": {}
        },
        "chat": [],
        "shop": DEFAULT_SHOP
    }
    try:
        sheet = get_sheet()
        raw = sheet.acell('A1').value
        if not raw or raw == "{}": return base
        d = json.loads(raw)
        
        # --- SAFEGUARDY ZE TVÉHO KÓDU ---
        if "shop" not in d: d["shop"] = DEFAULT_SHOP
        if "market" in d and "colors" in d["market"]:
            for c in COLORS:
                if c not in d["market"]["colors"]: d["market"]["colors"][c] = 2.0
        
        # Pojistka proti nesmyslným kurzům
        if d["market"].get("status") == "CLOSED":
            for c in d["market"]["colors"]:
                if d["market"]["colors"][c] > 9.0: 
                        d["market"]["colors"] = {k: 2.0 for k in COLORS}
                        if "original_odds" in d["market"]: del d["market"]["original_odds"]
                        break
        
        # Migrace statistik
        for u in d["users"].values():
            if "streak" not in u: u["streak"] = 0
            if "stats" not in u: 
                u["stats"] = {
                    "total_bets": 0, "total_wins": 0, "total_losses": 0,
                    "max_win": 0, "total_income_all": 0, "total_bet_winnings": 0,
                    "total_spent": 0, "color_counts": {}, "max_streak": 0
                }
            if "total_income_all" not in u["stats"]: u["stats"]["total_income_all"] = u["stats"].get("total_earned", 0)
            if "total_bet_winnings" not in u["stats"]: u["stats"]["total_bet_winnings"] = 0
            if "max_streak" not in u["stats"]: u["stats"]["max_streak"] = u["streak"]
            
        return d
    except Exception as e:
        return base

def save_data(data):
    try:
        sheet = get_sheet()
        sheet.update_acell('A1', json.dumps(data))
    except Exception as e:
        st.error(f"Chyba ukládání: {e}")

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
                # --- ZMĚNA 1: VÝPLATA S ČÁSTKOU ---
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
                if user["bonus"]: st.info(f"✨ Aktivní bonus: {user['bonus']}")

                cols = st.columns(4)
                idx = 0
                for c_name, odd in data["market"]["colors"].items():
                    with cols[idx % 4]:
                        hex_c = COLORS.get(c_name, "#ccc")
                        
                        card_style = ""
                        extra_info = ""
                        prev_odd = data["market"].get("prev_colors", {}).get(c_name, 2.0)
                        diff = round(odd - prev_odd, 1)
                        if diff > 0: extra_info += f"<br><span style='color:#198754;font-weight:bold;font-size:0.8em'>▲ +{diff}</span>"
                        elif diff < 0: extra_info += f"<br><span style='color:#dc3545;font-weight:bold;font-size:0.8em'>▼ {diff}</span>"
                        
                        if "original_odds" in data["market"] and c_name in data["market"]["original_odds"]:
                            orig = data["market"]["original_odds"][c_name]
                            if odd > orig:
                                card_style = "border: 2px solid #ffd700; box-shadow: 0 0 15px #ffd700;"
                                diff_evt = round(odd - orig, 1)
                                extra_info = f"<br><span style='color:#ffd700;font-weight:bold;font-size:0.9em'>⚡ MEGA +{diff_evt}</span>"

                        st.markdown(f"<div class='bet-card' style='{card_style}'><div style='height:25px;width:25px;border-radius:50%;background:{hex_c};display:inline-block;border:1px solid #999'></div><br><b>{c_name}</b><br><span style='color:#f60;font-weight:bold'>{odd}x</span>{extra_info}</div>", unsafe_allow_html=True)
                        if st.button("Vsadit", key=f"b_{c_name}"):
                            st.session_state["target"] = (c_name, odd)
                    idx += 1
                
                if "target" in st.session_state:
                    tc, to = st.session_state["target"]
                    st.info(f"Tiket: **{tc}** (Kurz {to})")
                    bal = int(user["bal"])
                    def_v = 50 if bal >= 50 else bal
                    vklad = st.number_input("Vklad", 1, max(1, bal), max(1, def_v))
                    if st.button("✅ Odeslat"):
                        if user["bal"] >= vklad:
                            user["bal"] -= vklad
                            used_bonus = user["bonus"]; user["bonus"] = None 
                            user["bets"].append({"c": tc, "a": vklad, "o": to, "st": "PENDING", "bonus": used_bonus})
                            update_user_stats(user, 0, 0, vklad, tc)
                            save_data(data); st.success("Hotovo"); del st.session_state["target"]; st.rerun()
                        else: st.error("Chybí CC")
        
        st.divider()
        st.subheader("🎫 Moje Tikety")
        pending = [b for b in user["bets"] if b["st"] == "PENDING"]
        history = [b for b in reversed(user["bets"]) if b["st"] != "PENDING"]
        
        if pending:
            for b in pending:
                bonus_txt = f" (+ {b['bonus']})" if b.get('bonus') else ""
                st.markdown(f"<div class='ticket-pending'><b>{b['c']}</b> | {b['a']} CC{bonus_txt}</div>", unsafe_allow_html=True)
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
                st.markdown(f"<div class='{cls}'>{res} <b>{b['c']}</b> ({b['a']} CC) {profit_info}</div>", unsafe_allow_html=True)

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

    # --- OBCHOD ---
    elif page == "OBCHOD":
        st.title("🛒 Obchod")
        t1, t2 = st.tabs(["Povýšení", "Věci"])
        with t1:
            if user["rank"] < 5:
                nr = RANKS[user["rank"]+1]
                p = [500, 2000, 5000, 15000, 50000][user["rank"]]
                
                # --- ZMĚNA 2: VYSVĚTLENÍ HODNOSTI ---
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
            
            if item_type == "use":
                if c2.button("Použít", key=f"use_{i}"):
                    if "Svačina" in item_name:
                        user["bal"] += 50; st.success("+50 CC"); log_item_usage(user, "Svačina", "Doplněno")
                    elif "Cihla" in item_name or "BOZP" in item_name:
                        user["bonus"] = item_name; st.success(f"Aktivováno: {item_name}"); log_item_usage(user, item_name, "Aktivován bonus")
                    user["inv"].pop(i); save_data(data); st.rerun()
            elif item_type == "passive": c2.caption("🛡️ Automatické")
            elif item_type == "atk": c2.caption("👊 Použij v Žebříčku")

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
            2.  **Sázky:** Vsaď na barvu. Pokud vyhraje, získáš násobek vkladu.
            3.  **Streak:** Pokud vyhraješ všechny své sázky v kole, roste ti 🔥 Streak. Jediná chyba a padáš na nulu.
            """)
        
        st.write("---")
        st.subheader("🎒 KATALOG PŘEDMĚTŮ")
        
        st.markdown("""
        ### 🔵 Aktivní předměty (Použij v Batohu)
        *Předměty typu 'Use' musíš ručně aktivovat v Batohu před tím, než jdou do akce.*

        **🧃 Svačina (Cena: 50 CC)**
        * **Co dělá:** Okamžitě ti přidá 50 CC do peněženky.
        * **Kdy koupit:** Když jsi úplně na dně a nemáš ani na vklad. Je to záchranná brzda.

        **🧱 Zlatá Cihla (Cena: 1000 CC)**
        * **Co dělá:** Zdvojnásobí tvou výhru.
        * **Jak použít:** Kup ji -> Jdi do Batohu -> Klikni "Použít" (aktivuje se bonus) -> Jdi vsadit.
        * **Riziko:** Pokud sázku prohraješ, o cihlu přijdeš a nedostaneš nic. Pokud vyhraješ, získáš balík.

        **👷 BOZP Helma (Cena: 300 CC)**
        * **Co dělá:** Funguje jako pojištění sázky.
        * **Jak použít:** Kup ji -> Jdi do Batohu -> Klikni "Použít" -> Jdi vsadit.
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
                                    if b["c"] in winners:
                                        mul = 2 if "Zlatá" in str(b.get("bonus","")) else 1
                                        w = int(b["a"] * b["o"] * mul)
                                        u["bal"] += w
                                        b["st"] = "WON"
                                        net_profit += (w - b["a"])
                                        update_user_stats(u, w-b["a"], 0, 0, "")
                                        count += 1
                                        has_win = True
                                    else:
                                        loss = b["a"]
                                        if "BOZP" in str(b.get("bonus","")): 
                                            u["bal"] += int(b["a"]*0.5); b["insurance"] = True
                                        b["st"] = "LOST"
                                        net_profit -= loss
                                        update_user_stats(u, 0, loss, 0, "")
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
                        
                        # --- NOVÁ LOGIKA ZMĚNY KURZŮ (RANDOM 0.0 - 0.3) ---
                        for c in data["market"]["colors"]:
                            # Generujeme změnu mezi 0.0 a 0.3
                            change = round(random.uniform(0.0, 0.3), 1)
                            
                            if c in winners:
                                # Výhra: pokles o 0.0 až 0.3, minimum 1.1
                                data["market"]["colors"][c] = max(1.1, round(data["market"]["colors"][c] - change, 1))
                            else:
                                # Prohra: nárůst o 0.0 až 0.3
                                data["market"]["colors"][c] = round(data["market"]["colors"][c] + change, 1)
                        # ----------------------------------------------------
                        
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
