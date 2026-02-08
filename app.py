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
# 🎨 1. KONFIGURACE
# ==========================================
st.set_page_config(page_title="Cihlářské Sázky", page_icon="🧱", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; color: #333; }
    h1, h2, h3 { color: #ff6600 !important; font-family: 'Arial Black', sans-serif; text-transform: uppercase; }
    .stButton>button { background-color: #ff6600; color: white; border: none; font-weight: bold; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #cc5200; transform: scale(1.02); }
    .bet-card { background: white; border-radius: 12px; padding: 15px; text-align: center; border: 2px solid #eee; box-shadow: 0 4px 6px rgba(0,0,0,0.05); position: relative; height: 180px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    .stat-box { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 10px; border-left: 5px solid #ccc; }
    .stat-label { font-size: 0.85em; color: #666; text-transform: uppercase; letter-spacing: 1px; }
    .stat-val { font-size: 1.4em; font-weight: bold; color: #333; }
    .market-open { background-color: #d1e7dd; color: #0f5132; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; border: 2px solid #badbcc; }
    .market-closed { background-color: #f8d7da; color: #842029; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; border: 2px solid #f5c2c7; }
    .ticket-pending { border-left: 5px solid #ffc107; background: #fff3cd; padding: 10px; margin-bottom: 5px; border-radius: 4px; }
    .ticket-won { border-left: 5px solid #198754; background: #d1e7dd; padding: 5px; margin-bottom: 5px; border-radius: 4px; }
    .ticket-lost { border-left: 5px solid #dc3545; background: #f8d7da; padding: 5px; margin-bottom: 5px; border-radius: 4px; }
    .trans-in { border-left: 5px solid #198754; background: #d1e7dd; padding: 8px; margin-bottom: 4px; border-radius: 4px; }
    .trans-out { border-left: 5px solid #dc3545; background: #f8d7da; padding: 8px; margin-bottom: 4px; border-radius: 4px; }
    .hist-item { font-size: 0.9em; padding: 5px; border-bottom: 1px solid #eee; color: #555; }
    .msg-sys { background: #fff3cd; border-left: 5px solid #ffc107; padding: 8px; margin-bottom: 5px; font-size: 0.9em; }
    .msg-event { background: #cff4fc; border-left: 5px solid #0dcaf0; padding: 8px; margin-bottom: 5px; font-weight: bold; }
    .msg-user { background: white; border-left: 5px solid #ddd; padding: 8px; margin-bottom: 5px; }
    .badge { padding: 2px 6px; border-radius: 4px; color: white; font-size: 0.75em; font-weight: bold; margin-left: 5px; vertical-align: middle; }
    .bg-0 { background: #6c757d; } .bg-1 { background: #795548; } .bg-2 { background: #fd7e14; } .bg-3 { background: #0d6efd; } .bg-4 { background: #dc3545; } .bg-5 { background: linear-gradient(45deg, #FFD700, #DAA520); color: black; } .bg-admin { background: #000; border: 1px solid #ff6600; }
    .streak { color: #ff4500; font-weight: bold; margin-left: 5px; text-shadow: 0 0 5px orange; }
</style>
""", unsafe_allow_html=True)

COLORS = { "Červená": "#dc3545", "Modrá": "#0d6efd", "Žlutá": "#ffc107", "Zelená": "#198754", "Oranžová": "#fd7e14", "Fialová": "#6f42c1", "Bílá": "#ffffff", "Černá": "#212529", "Šedá": "#6c757d", "Hnědá": "#795548", "Růžová": "#d63384", "Béžová": "#f5f5dc", "Tyrkysová": "#20c997", "Azurová": "#0dcaf0" }
RANKS = [ {"name": "Pomocná síla", "inc": 50, "css": "bg-0"}, {"name": "Kopáč", "inc": 60, "css": "bg-1"}, {"name": "Zedník", "inc": 75, "css": "bg-2"}, {"name": "Zásobovač", "inc": 120, "css": "bg-3"}, {"name": "Stavbyvedoucí", "inc": 250, "css": "bg-4"}, {"name": "Cihlobaron", "inc": 550, "css": "bg-5"} ]
DEFAULT_SHOP = [ {"name": "🧃 Svačina", "base_p": 50, "curr_p": 50, "type": "use", "desc": "Doplní 50 CC."}, {"name": "👷 BOZP Helma", "base_p": 300, "curr_p": 300, "type": "use", "desc": "Aktivuj PŘED sázkou. Vrátí 50% při prohře."}, {"name": "🧱 Zlatá Cihla", "base_p": 1000, "curr_p": 1000, "type": "use", "desc": "Aktivuj PŘED sázkou. Výhra x2."}, {"name": "🛡️ Titanová Přilba", "base_p": 3000, "curr_p": 3000, "type": "passive", "desc": "Pasivní: 80% šance odrazit útok. (Max 1 ks)"}, {"name": "🦶 Podkopnutí", "base_p": 8000, "curr_p": 8000, "type": "atk", "desc": "Útok v Žebříčku: Zraní soupeře."}, {"name": "👻 Fantom", "base_p": 20000, "curr_p": 20000, "type": "atk", "desc": "Tajný útok v Žebříčku."}, {"name": "🪣 Větší Kbelík", "base_p": 2500, "curr_p": 2500, "type": "upgrade", "desc": "+2 Sloty do batohu."} ]

# ==========================================
# ☁️ 2. GOOGLE CLOUD (OPTIMALIZOVANÉ)
# ==========================================
@st.cache_resource
def init_connection():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def get_sheet():
    client = init_connection()
    return client.open("CihlyData").sheet1

def load_data():
    base = { "users": {}, "market": { "status": "CLOSED", "colors": {c: 2.0 for c in COLORS}, "prev_colors": {c: 2.0 for c in COLORS}, "last_round_stats": {} }, "chat": [], "shop": DEFAULT_SHOP }
    try:
        sheet = get_sheet()
        raw = sheet.acell('A1').value
        if not raw or raw == "{}": return base
        d = json.loads(raw)
        if "shop" not in d: d["shop"] = DEFAULT_SHOP
        if "market" in d and "colors" in d["market"]:
            for c in COLORS:
                if c not in d["market"]["colors"]: d["market"]["colors"][c] = 2.0
        if d["market"].get("status") == "CLOSED":
            for c in d["market"]["colors"]:
                if d["market"]["colors"][c] > 9.0: 
                        d["market"]["colors"] = {k: 2.0 for k in COLORS}; del d["market"]["original_odds"]; break
        for u in d["users"].values():
            if "streak" not in u: u["streak"] = 0
            if "stats" not in u: u["stats"] = {"total_bets":0,"total_wins":0,"total_losses":0,"max_win":0,"total_income_all":0,"total_bet_winnings":0,"total_spent":0,"color_counts":{}, "max_streak": 0}
            if "total_income_all" not in u["stats"]: u["stats"]["total_income_all"] = u["stats"].get("total_earned", 0)
            if "total_bet_winnings" not in u["stats"]: u["stats"]["total_bet_winnings"] = 0
            if "max_streak" not in u["stats"]: u["stats"]["max_streak"] = u["streak"]
        return d
    except: return base

def save_data(data):
    try:
        # --- OPTIMALIZACE: Ořezávání historie (aby nepadala paměť) ---
        if len(data["chat"]) > 60: data["chat"] = data["chat"][-60:] # Nechá jen posledních 60 zpráv
        for u in data["users"].values():
            if "trans" in u and len(u["trans"]) > 50: u["trans"] = u["trans"][-50:] # Max 50 transakcí
            if "item_history" in u and len(u["item_history"]) > 30: u["item_history"] = u["item_history"][-30:] # Max 30 použití
        # -----------------------------------------------------------
        sheet = get_sheet()
        sheet.update_acell('A1', json.dumps(data))
    except Exception as e:
        st.toast(f"⚠️ Chyba spojení s Googlem: {e}")

# ==========================================
# 💾 LOGIKA
# ==========================================
def get_time(): return datetime.now().strftime("%H:%M")
def log_item_usage(u, i, d): 
    if "item_history" not in u: u["item_history"]=[] 
    u["item_history"].append({"item":i,"detail":d,"tm":get_time()})
def update_user_stats(u, w, l, b, c, s=0, o=0):
    stt = u["stats"]
    if b>0: stt["total_bets"]+=1; stt["color_counts"][c]=stt["color_counts"].get(c,0)+1
    if w>0: stt["total_wins"]+=1; stt["total_bet_winnings"]+=w; stt["total_income_all"]+=w; 
    if w>stt["max_win"]: stt["max_win"]=w
    if l>0: stt["total_losses"]+=1
    if s>0: stt["total_spent"]+=s
    if o>0: stt["total_income_all"]+=o

def trigger_shop_fluctuation(data):
    for item in data["shop"]: item["curr_p"] = item["base_p"]
    eligible = [i for i, item in enumerate(data["shop"]) if "Svačina" not in item["name"] and "Kbelík" not in item["name"]]
    random.shuffle(eligible)
    discounted = eligible[:3] if len(eligible)>=3 else eligible
    hiked = eligible[3:6] if len(eligible)>=6 else []
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
        if "original_odds" not in data["market"]: data["market"]["original_odds"] = data["market"]["colors"].copy()
        boosted = random.sample(list(COLORS.keys()), 3)
        for bc in boosted: 
            base_val = data["market"]["original_odds"][bc]
            data["market"]["colors"][bc] = round(base_val * 5.0, 1)
        msg = f"🚀 MEGA EVENT: Barvy {', '.join(boosted)} mají 5x kurz!"
    elif event_type == "COPPER":
        for u in data["users"].values(): u["bal"] += 150; update_user_stats(u, 0, 0, 0, "", 0, 150)
        msg = "🎁 EVENT: Nález mědi! +150 CC všem."
    elif event_type == "SCAFFOLD":
        for u in data["users"].values(): u["bal"] = int(u["bal"] * 0.9)
        msg = "🔥 EVENT: Pád lešení! -10% všem."
    elif event_type == "PROVERKA":
        victims = []
        for uname, u in data["users"].items():
            if random.random() < 0.50: u["hp"] = "ZRANEN"; victims.append(uname)
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
            if u in data["users"] and data["users"][u]["pass"] == p: st.session_state.user = u; st.rerun()
            else: st.sidebar.error("Chyba")
    with tab2:
        nu = st.text_input("Nové jméno", key="ru")
        np = st.text_input("Nové heslo", type="password", key="rp")
        if st.button("Vytvořit"):
            if nu and nu not in data["users"]:
                data["users"][nu] = {"pass": np, "bal": 0, "rank": 0, "inv": [], "slots": 0, "hp": "OK", "bets": [], "pay": False, "bonus": None, "trans": [], "item_history": [], "streak": 0, "stats": {"total_bets":0,"total_wins":0,"total_losses":0,"max_win":0,"total_income_all":0,"total_bet_winnings":0,"total_spent":0,"color_counts":{}, "max_streak": 0}}
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

    if st.sidebar.button("Odhlásit"): st.session_state.user = None; st.session_state.admin_ok = False; st.rerun()
    
    rid = min(user["rank"], len(RANKS)-1)
    max_slots = 3 + (user["slots"] * 2)
    current_items = len(user["inv"])
    
    st.sidebar.divider()
    st.sidebar.write(f"👷 **{me}** {'🔥 '+str(user['streak']) if user['streak']>0 else ''}")
    st.sidebar.info(f"{RANKS[rid]['name']}")
    st.sidebar.metric("Zůstatek", f"{int(user['bal'])} CC")
    if user["hp"] != "OK": st.sidebar.error("🤕 JSI ZRANĚN!")
    
    page = st.sidebar.radio("Navigace", ["DOMŮ", "ŽEBŘÍČEK", "STATISTIKY", "GRAFY", "OBCHOD", "BATOH", "BANKA", "CHAT", "📚 NÁPOVĚDA", "ADMIN"])

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
                    update_user_stats(user, 0, 0, 0, "", 0, inc); save_data(data); st.balloons(); st.rerun()
            if user["hp"] != "OK": st.error("🤕 Jsi zraněn! Nemůžeš sázet.")
            else:
                st.write("### 🎲 Vsaď na barvu")
                if user["bonus"]: st.info(f"✨ Aktivní bonus: {user['bonus']}")
                cols = st.columns(4); idx = 0
                for c_name, hex_c in COLORS.items():
                    with cols[idx % 4]:
                        odd = data["market"]["colors"].get(c_name, 2.0)
                        card_style = "2px solid #eee"; box_shadow = "0 4px 6px rgba(0,0,0,0.05)"; extra_info = ""
                        prev_odd = data["market"].get("prev_colors", {}).get(c_name, 2.0); diff = round(odd - prev_odd, 1)
                        if diff > 0: extra_info = f"<div style='color:#198754;font-weight:bold;font-size:0.8em;margin-top:2px'>▲ +{diff}</div>"
                        elif diff < 0: extra_info = f"<div style='color:#dc3545;font-weight:bold;font-size:0.8em;margin-top:2px'>▼ {diff}</div>"
                        if "original_odds" in data["market"] and c_name in data["market"]["original_odds"]:
                            if odd > data["market"]["original_odds"][c_name]:
                                card_style = "2px solid #ffd700"; box_shadow = "0 0 15px #ffd700"; diff_evt = round(odd - data["market"]["original_odds"][c_name], 1)
                                extra_info = f"<div style='color:#ffd700;font-weight:bold;font-size:0.9em;margin-top:2px'>⚡ MEGA +{diff_evt}</div>"
                        st.markdown(f"<div style='background:white;border-radius:12px;padding:10px;text-align:center;border:{card_style};box-shadow:{box_shadow};height:160px;display:flex;flex-direction:column;justify-content:center;align-items:center;'><div style='width:30px;height:30px;border-radius:50%;background-color:{hex_c};display:block;margin:0 auto 5px auto;border:1px solid #ccc;box-shadow:0 2px 4px rgba(0,0,0,0.1);'></div><div style='font-weight:bold;margin-bottom:5px;color:#333;'>{c_name}</div><div style='color:#ff6600;font-weight:bold;font-size:1.4em;'>{odd}x</div>{extra_info}</div>", unsafe_allow_html=True)
                        if st.button("Vsadit", key=f"b_{c_name}"): st.session_state["target"] = (c_name, odd)
                    idx += 1
                if "target" in st.session_state:
                    tc, to = st.session_state["target"]; st.info(f"Tiket: **{tc}** (Kurz {to})"); bal = int(user["bal"]); def_v = 50 if bal >= 50 else bal
                    vklad = st.number_input("Vklad", 1, max(1, bal), max(1, def_v))
                    if st.button("✅ Odeslat"):
                        if user["bal"] >= vklad:
                            user["bal"] -= vklad; used_bonus = user["bonus"]; user["bonus"] = None 
                            user["bets"].append({"c": tc, "a": vklad, "o": to, "st": "PENDING", "bonus": used_bonus})
                            update_user_stats(user, 0, 0, vklad, tc); save_data(data); st.success("Hotovo"); del st.session_state["target"]; st.rerun()
                        else: st.error("Chybí CC")
        st.divider(); st.subheader("🎫 Moje Tikety")
        pending = [b for b in user["bets"] if b["st"] == "PENDING"]
        if pending:
            for b in pending: st.markdown(f"<div class='ticket-pending'><b>{b['c']}</b> | {b['a']} CC{ ' (+ '+b['bonus']+')' if b.get('bonus') else ''}</div>", unsafe_allow_html=True)
        else: st.caption("Žádné aktivní sázky.")
        with st.expander("📜 Historie"):
            for b in reversed([x for x in user["bets"] if x["st"] != "PENDING"]):
                cls = "ticket-won" if b["st"] == "WON" else "ticket-lost"; res = "✅" if b["st"] == "WON" else "❌"; pi = f"(+{int(b['a']*b['o'])-b['a']} profit)" if b["st"]=="WON" else ("(Pojištěno 50%)" if b.get("insurance") else "")
                st.markdown(f"<div class='{cls}'>{res} <b>{b['c']}</b> ({b['a']} CC) {pi}</div>", unsafe_allow_html=True)

    elif page == "ŽEBŘÍČEK":
        st.title("🏆 Žebříček")
        for i, (tn, td) in enumerate(sorted(data["users"].items(), key=lambda x: x[1]['bal'], reverse=True)):
            hp = "🤕" if td["hp"] != "OK" else ""; strk = f"🔥 {td['streak']}" if td.get('streak',0)>0 else ""; trid = min(td["rank"], 5)
            st.markdown(f"<div style='background:white;padding:10px;border-radius:5px;margin-bottom:5px;border-left:3px solid #ccc'><b>#{i+1} {tn}</b> {hp} <span class='badge {RANKS[trid]['css']}'>{RANKS[trid]['name']}</span> <span class='streak'>{strk}</span> <div style='float:right;font-weight:bold'>{int(td['bal'])} CC</div></div>", unsafe_allow_html=True)
            if tn != me and td["hp"] == "OK":
                c1, c2 = st.columns([1,4])
                with c1:
                    if "🦶 Podkopnutí" in user["inv"] and st.button("👊 Kop", key=f"k_{tn}"):
                        user["inv"].remove("🦶 Podkopnutí"); log_item_usage(user, "Podkopnutí", tn)
                        if "🛡️ Titanová Přilba" in td["inv"] and random.random()<0.8: td["inv"].remove("🛡️ Titanová Přilba"); data["chat"].append({"u":"SYS","t":f"🛡️ {tn} vykryl útok!","tm":get_time(),"r":"BOT"})
                        else: td["hp"] = "ZRANEN"; data["chat"].append({"u":"SYS","t":f"🚨 {me} podkopl {tn}!","tm":get_time(),"r":"BOT"})
                        save_data(data); st.rerun()
                    if "👻 Fantom" in user["inv"] and st.button("👻 Fan", key=f"f_{tn}"):
                        user["inv"].remove("👻 Fantom"); log_item_usage(user, "Fantom", tn)
                        if "🛡️ Titanová Přilba" in td["inv"] and random.random()<0.8: td["inv"].remove("🛡️ Titanová Přilba"); data["chat"].append({"u":"SYS","t":f"🛡️ {tn} odrazil tajný útok!","tm":get_time(),"r":"BOT"})
                        else: td["hp"] = "ZRANEN"; data["chat"].append({"u":"SYS","t":f"👻 {tn} byl záhadně zraněn!","tm":get_time(),"r":"BOT"})
                        save_data(data); st.rerun()

    elif page == "STATISTIKY":
        st.title("📊 Osobní Karta"); s = user["stats"]
        c1, c2, c3 = st.columns(3); c1.markdown(f"<div class='stat-box' style='border-left:5px solid #28a745'><div class='stat-label'>Celkový příjem (vše)</div><div class='stat-val'>+{s['total_income_all']} CC</div></div>", unsafe_allow_html=True); c2.markdown(f"<div class='stat-box' style='border-left:5px solid #17a2b8'><div class='stat-label'>Zisk jen ze sázek</div><div class='stat-val'>+{s['total_bet_winnings']} CC</div></div>", unsafe_allow_html=True); c3.markdown(f"<div class='stat-box' style='border-left:5px solid #dc3545'><div class='stat-label'>Utraceno v shopu</div><div class='stat-val'>-{s['total_spent']} CC</div></div>", unsafe_allow_html=True)
        c4, c5, c6 = st.columns(3); fav = max(s['color_counts'], key=s['color_counts'].get) if s['color_counts'] else "Žádná"; c4.markdown(f"<div class='stat-box'><div class='stat-label'>Oblíbená</div><div class='stat-val' style='color:{COLORS.get(fav, '#333')}'>{fav}</div></div>", unsafe_allow_html=True); c5.markdown(f"<div class='stat-box'><div class='stat-label'>W/L</div><div class='stat-val'><span style='color:green'>{s['total_wins']}</span> / <span style='color:red'>{s['total_losses']}</span></div></div>", unsafe_allow_html=True); wr = int((s['total_wins']/s['total_bets'])*100) if s['total_bets']>0 else 0; c6.markdown(f"<div class='stat-box'><div class='stat-label'>Úspěšnost</div><div class='stat-val'>{wr} %</div></div>", unsafe_allow_html=True)
        c7, c8, c9 = st.columns(3); c7.markdown(f"<div class='stat-box'><div class='stat-label'>Max Win</div><div class='stat-val'>+{s['max_win']} CC</div></div>", unsafe_allow_html=True); c8.markdown(f"<div class='stat-box'><div class='stat-label'>Aktuální Streak</div><div class='stat-val' style='color:#ff4500'>🔥 {user['streak']}</div></div>", unsafe_allow_html=True); c9.markdown(f"<div class='stat-box'><div class='stat-label'>Top Streak</div><div class='stat-val' style='color:#fd7e14'>🏆 {s.get('max_streak', 0)}</div></div>", unsafe_allow_html=True)

    elif page == "GRAFY":
        st.title("📈 Tržní data"); cur = {}; last = data["market"].get("last_round_stats", {})
        for u in data["users"].values():
            for b in u["bets"]:
                if b["st"] == "PENDING": cur[b["c"]] = cur.get(b["c"], 0) + b["a"]
        if cur: 
            df = pd.DataFrame(list(cur.items()), columns=['Barva', 'Částka']); df['Hex'] = df['Barva'].map(COLORS)
            c = alt.Chart(df).mark_bar(stroke='black', strokeWidth=2).encode(x=alt.X('Barva', sort='-y'), y='Částka', color=alt.Color('Barva', scale=alt.Scale(domain=list(df['Barva']), range=list(df['Hex'])), legend=None)).properties(height=400)
            st.altair_chart(c, use_container_width=True)
        else: st.info("Zatím žádné sázky.")
        st.divider(); st.subheader("Minulé kolo")
        if last: 
            df_last = pd.DataFrame(list(last.items()), columns=['Barva', 'Částka']); df_last['Hex'] = df_last['Barva'].map(COLORS)
            c_last = alt.Chart(df_last).mark_bar(stroke='black', strokeWidth=2).encode(x=alt.X('Barva', sort='-y'), y='Částka', color=alt.Color('Barva', scale=alt.Scale(domain=list(df_last['Barva']), range=list(df_last['Hex'])), legend=None)).properties(height=300)
            st.altair_chart(c_last, use_container_width=True)

    elif page == "OBCHOD":
        st.title("🛒 Obchod"); t1, t2 = st.tabs(["Povýšení", "Věci"])
        with t1:
            if user["rank"] < 5:
                nr = RANKS[user["rank"]+1]; p = [500, 2000, 5000, 15000, 50000][user["rank"]]
                st.info(f"Další: **{nr['name']}** ({p} CC)\n\n💰 **Zvyšuje denní příjem na {nr['inc']} CC**")
                if st.button("Koupit hodnost"):
                    if user["bal"] >= p: user["bal"] -= p; user["rank"] += 1; update_user_stats(user,0,0,0,"",p); save_data(data); st.balloons(); st.rerun()
                    else: st.error("Chybí peníze")
        with t2:
            st.write(f"Batoh: {len(user['inv'])} / {3 + user['slots']*2}")
            for item in data["shop"]:
                p = item["curr_p"]; base = item["base_p"]
                if "Kbelík" in item["name"]: p = base + (user["slots"] * 2000)
                pdsp = f"**{p} CC**" if p==base else (f"<span style='color:gray;text-decoration:line-through'>{base}</span> <span style='color:#198754;font-weight:bold'>{p} CC (-{int((1-p/base)*100)}%)</span>" if p<base else f"<span style='color:gray;text-decoration:line-through'>{base}</span> <span style='color:#dc3545;font-weight:bold'>{p} CC (+{int((p/base-1)*100)}%)</span>")
                c1, c2 = st.columns([3,1]); c1.markdown(f"**{item['name']}** {pdsp}", unsafe_allow_html=True); c1.caption(item['desc'])
                if c2.button("Koupit", key=f"b_{item['name']}"):
                    if user["bal"] >= p: 
                        if "Titanová" in item["name"] and "🛡️ Titanová Přilba" in user["inv"]: st.error("Limit 1 ks.")
                        elif item["type"] == "upgrade": user["bal"]-=p; user["slots"]+=1; update_user_stats(user,0,0,0,"",p); save_data(data); st.success("OK"); st.rerun()
                        elif len(user["inv"]) < 3 + user["slots"]*2: user["bal"]-=p; user["inv"].append(item["name"]); update_user_stats(user,0,0,0,"",p); save_data(data); st.success("OK"); st.rerun()
                        else: st.error("Plno!")
                    else: st.error("Chybí CC")
                st.divider()

    elif page == "BATOH":
        st.title("🎒 Batoh"); 
        if not user["inv"]: st.info("Prázdno.")
        for i, item in enumerate(user["inv"]):
            c1, c2 = st.columns([3,1]); c1.write(f"📦 {item}"); itype = next((x["type"] for x in data["shop"] if x["name"]==item),"unknown")
            if itype=="use" and c2.button("Použít", key=f"u{i}"):
                if "Svačina" in item: user["bal"]+=50; log_item_usage(user,"Svačina","Doplněno")
                else: user["bonus"]=item; log_item_usage(user,item,"Aktivován bonus")
                user["inv"].pop(i); save_data(data); st.rerun()
            elif itype=="passive": c2.caption("🛡️ Automatické")
            elif itype=="atk": c2.caption("👊 Použij v Žebříčku")
        st.divider(); 
        with st.expander("📜 Historie"):
            for h in reversed(user["item_history"]): st.markdown(f"<div class='hist-item'>🔹 <b>{h['item']}</b> - {h['detail']} <span style='float:right;font-size:0.8em'>{h['tm']}</span></div>", unsafe_allow_html=True)

    elif page == "BANKA":
        st.title("🏦 Banka"); r = st.selectbox("Komu:", [u for u in data["users"] if u!=me]); a = st.number_input("Kolik:", 1, max(1, int(user["bal"])))
        if st.button("Poslat"): 
            if user["bal"]>=a: 
                user["bal"]-=a; user["trans"].append({"type":"out","amt":a,"src":r,"tm":get_time()}); data["users"][r]["bal"]+=a; data["users"][r]["trans"].append({"type":"in","amt":a,"src":me,"tm":get_time()}); update_user_stats(data["users"][r],0,0,0,"",0,a); data["chat"].append({"u":"BANKA","t":f"{me} poslal {a} CC hráči {r}.","tm":get_time(),"r":"BOT"}); save_data(data); st.success("Odesláno"); st.rerun()
        st.divider(); 
        for t in reversed(user["trans"]): st.markdown(f"<div class='trans-in'>⬇️ +{t['amt']} ({t['src']})</div>" if t['type']=='in' else f"<div class='trans-out'>⬆️ -{t['amt']} ({t['src']})</div>", unsafe_allow_html=True)

    elif page == "CHAT":
        st.title("📢 Chat")
        with st.container():
            for m in data["chat"][-50:]: 
                cls = "msg-sys" if m['u'] in ["SYS","EVENT","BANKA","SHOP"] else "msg-user"; role_cl="bg-0"
                for r in RANKS: 
                    if r["name"]==m.get("r"): role_cl=r["css"]
                if m.get("r")=="ADMIN": role_cl="bg-admin"
                snd = data["users"].get(m['u']); strk = f"<span class='streak'>🔥 {snd['streak']}</span>" if snd and snd.get('streak',0)>0 else ""
                st.markdown(f"<div class='{cls}'><small>{m['tm']}</small> <b>{m['u']}</b> {f'<span class=badge {role_cl}>{m.get(r,)}</span>' if m['u'] not in ['SYS','EVENT','BANKA','SHOP'] else ''} {strk}: {m['t']}</div>", unsafe_allow_html=True)
        with st.form("cf"): 
            if st.form_submit_button("Odeslat") and (t:=st.text_input("Zpráva")): data["chat"].append({"u":me, "t":t, "tm":get_time(), "r": "ADMIN" if st.session_state.get("admin_ok") else RANKS[rid]['name']}); save_data(data); st.rerun()

    elif page == "📚 NÁPOVĚDA": st.title("📚 Manuál"); st.write("Kompletní manuál viz předchozí verze.")

    elif page == "ADMIN":
        st.title("⚙️ Admin"); 
        if not st.session_state.get("admin_ok"): 
            if st.text_input("Heslo", type="password")=="admin123": st.session_state.admin_ok=True; st.rerun()
        else:
            if st.button("Odhlásit"): st.session_state.admin_ok=False; st.rerun()
            t1, t2, t3, t4 = st.tabs(["Trh", "Hráči", "Obchod", "Eventy"])
            with t1:
                if st.button("🟢 OTEVŘÍT / 🔴 ZAVŘÍT"):
                    ns = "OPEN" if data["market"]["status"]=="CLOSED" else "CLOSED"; data["market"]["status"]=ns
                    if ns=="OPEN": 
                        for u in data["users"].values(): u["pay"]=False; u["hp"]="OK"
                        if "original_odds" in data["market"]: del data["market"]["original_odds"]
                        st.markdown(f"Shop: {trigger_shop_fluctuation(data)}", unsafe_allow_html=True)
                        r = random.randint(1,100); msg=None
                        if r<=10: msg=trigger_game_event(data,"MEGA")
                        elif r<=30: msg=trigger_game_event(data,"COPPER")
                        elif r<=40: msg=trigger_game_event(data,"SCAFFOLD")
                        elif r>=96: msg=trigger_game_event(data,"PROVERKA")
                        if msg: st.success(msg)
                    else:
                        for i in data["shop"]: i["curr_p"]=i["base_p"]
                        if "original_odds" in data["market"]: data["market"]["colors"]=data["market"]["original_odds"]; del data["market"]["original_odds"]
                        data["chat"].append({"u":"SYS","t":"Trh zavřen.","tm":get_time(),"r":"BOT"})
                    save_data(data); st.rerun()
                winners = st.multiselect("Vítězové", list(COLORS.keys()))
                if st.button("VYPLATIT"):
                    data["market"]["prev_colors"] = data["market"]["colors"].copy(); round_bets = {}
                    for u in data["users"].values():
                        u["hp"]="OK"; win=False; loss=False
                        for b in u["bets"]:
                            if b["st"]=="PENDING":
                                round_bets[b["c"]] = round_bets.get(b["c"],0)+b["a"]
                                if b["c"] in winners:
                                    m=2 if "Zlatá" in str(b.get("bonus","")) else 1; w=int(b["a"]*b["o"]*m); u["bal"]+=w; b["st"]="WON"; update_user_stats(u,w-b["a"],0,0,""); win=True
                                else:
                                    if "BOZP" in str(b.get("bonus","")): u["bal"]+=int(b["a"]*0.5); b["insurance"]=True
                                    b["st"]="LOST"; update_user_stats(u,0,b["a"],0,""); loss=True
                        if win and not loss: u["streak"]+=1; u["stats"]["max_streak"]=max(u["streak"], u["stats"]["max_streak"])
                        elif loss: u["streak"]=0
                    data["market"]["last_round_stats"]=round_bets; data["chat"].append({"u":"SYS","t":f"Vítězové: {', '.join(winners)}","tm":get_time(),"r":"BOT"})
                    for c in data["market"]["colors"]:
                        ch = round(random.uniform(0.0,0.3),1)
                        if c in winners: data["market"]["colors"][c] = max(1.1, round(data["market"]["colors"][c]-ch,1))
                        else: data["market"]["colors"][c] = round(data["market"]["colors"][c]+ch,1)
                    save_data(data); st.success("OK")
            with t2:
                sel = st.selectbox("Hráč", list(data["users"].keys())); st.write(f"Heslo: {data['users'][sel]['pass']}")
                if st.button("UZDRAVIT"): data["users"][sel]["hp"]="OK"; save_data(data); st.success("OK")
                amt = st.number_input("Částka", 1, 10000); c1,c2=st.columns(2)
                if c1.button("Přidat"): data["users"][sel]["bal"]+=amt; update_user_stats(data["users"][sel],0,0,0,"",0,amt); save_data(data); st.success("OK")
                if c2.button("Strhnout"): data["users"][sel]["bal"]-=amt; save_data(data); st.success("OK")
                if st.button("SMAZAT"): del data["users"][sel]; save_data(data); st.rerun()
            with t3:
                if st.button("Cenový šok"): msg=trigger_shop_fluctuation(data); save_data(data); st.success(msg)
            with t4:
                if st.button("⚠️ RESET DATABÁZE"): st.error("Smaž A1 v Google Sheets.")
