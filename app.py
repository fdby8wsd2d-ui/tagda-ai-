import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, timedelta
import re

# ========================================
# INITIALIZATION & DATABASE
# ========================================
def init_db():
    conn = sqlite3.connect('tagda_ai.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT DEFAULT 'user',
        subscribed INTEGER DEFAULT 0,
        expiry TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_login TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        message_role TEXT,
        message TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        plan TEXT,
        amount REAL,
        payment_status TEXT,
        transaction_id TEXT,
        timestamp TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        details TEXT,
        timestamp TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

def create_default_admin():
    conn = sqlite3.connect('tagda_ai.db')
    c = conn.cursor()
    admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username, password, role, subscribed, expiry) VALUES (?, ?, ?, ?, ?)",
              ("admin", admin_pass, "admin", 1, str(datetime.now() + timedelta(days=9999))))
    conn.commit()
    conn.close()

create_default_admin()

st.set_page_config(page_title="TAGDA AI", page_icon="🔥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main { background: linear-gradient(135deg, #0a0a1f 0%, #1a1a3e 100%); color: #e0e0ff; }
    h1 { font-family: 'Arial Black'; color: #00ff9d; text-shadow: 0 0 20px #00ff9d; }
    .stButton>button { background: linear-gradient(45deg, #00ff9d, #00b36b); color: #000; font-weight: bold; border-radius: 50px; height: 3em; }
    .chat-user { background: #1e3a8a; padding: 18px; border-radius: 20px 20px 5px 20px; margin: 12px 0; }
    .chat-assist { background: #312e81; padding: 18px; border-radius: 5px 20px 20px 20px; margin: 12px 0; }
</style>
""", unsafe_allow_html=True)

if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = {}

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def get_user_info(username):
    conn = sqlite3.connect('tagda_ai.db')
    c = conn.cursor()
    c.execute("SELECT role, subscribed, expiry FROM users WHERE username=?", (username,))
    data = c.fetchone()
    conn.close()
    return data

def save_message(username, role, message):
    conn = sqlite3.connect('tagda_ai.db')
    c = conn.cursor()
    c.execute("INSERT INTO chats (username, message_role, message) VALUES (?, ?, ?)",
              (username, role, message))
    conn.commit()
    conn.close()

with st.sidebar:
    st.title("TAGDA AI")
    st.markdown("**Apna Private AI Assistant**")

    if st.session_state.current_user is None:
        tabs = st.tabs(["Login", "Register"])
        with tabs[0]:
            un = st.text_input("Username", key="l_un")
            pw = st.text_input("Password", type="password", key="l_pw")
            if st.button("Login"):
                conn = sqlite3.connect('tagda_ai.db')
                c = conn.cursor()
                c.execute("SELECT password, role FROM users WHERE username=?", (un,))
                data = c.fetchone()
                if data and data[0] == hash_password(pw):
                    st.session_state.current_user = un
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error("Invalid login")
                conn.close()

        with tabs[1]:
            reg_un = st.text_input("New Username")
            reg_pw = st.text_input("New Password", type="password")
            if st.button("Register"):
                if reg_un and reg_pw:
                    conn = sqlite3.connect('tagda_ai.db')
                    c = conn.cursor()
                    try:
                        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                                  (reg_un, hash_password(reg_pw), "user"))
                        conn.commit()
                        st.success("Account created!")
                    except Exception:
                        st.error("Username taken")
                    conn.close()
    else:
        info = get_user_info(st.session_state.current_user)
        st.success(f"{st.session_state.current_user}")
        st.caption(f"Role: {info[0]} | {'Premium' if info[1] else 'Free'}")

        if st.button("Logout"):
            st.session_state.current_user = None
            st.rerun()

        st.divider()
        page = st.radio("Main Menu", [
            "Universal Chat",
            "Image Studio",
            "Plans & Billing",
        ])

if st.session_state.current_user:
    info = get_user_info(st.session_state.current_user)
    is_admin = info[0] == "admin"

    if not is_admin and not info[1]:
        st.error("Subscribe karo full access ke liye!")
        if st.button("Activate (Demo)"):
            conn = sqlite3.connect('tagda_ai.db')
            c = conn.cursor()
            c.execute("UPDATE users SET subscribed=1, expiry=? WHERE username=?",
                      (str(datetime.now() + timedelta(days=9999)), st.session_state.current_user))
            conn.commit()
            conn.close()
            st.success("Unlocked!")
            st.rerun()
    else:
        if page == "Universal Chat":
            st.header("Universal Chat")
            for msg in st.session_state.chat_history.get(st.session_state.current_user, []):
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            prompt = st.chat_input("Type anything...")
            if prompt:
                if st.session_state.current_user not in st.session_state.chat_history:
                    st.session_state.chat_history[st.session_state.current_user] = []
                st.session_state.chat_history[st.session_state.current_user].append({"role": "user", "content": prompt})
                save_message(st.session_state.current_user, "user", prompt)
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    response = "Yahan par tum apna AI backend (Gemini/Claude API) jodo taaki real jawaab aaye."
                    st.markdown(response)
                st.session_state.chat_history[st.session_state.current_user].append({"role": "assistant", "content": response})
                save_message(st.session_state.current_user, "assistant", response)

        elif page == "Image Studio":
            st.header("Image Studio")
            st.info("Yahan real image-gen API (jaise Stability/Flux) jodni padegi.")

        elif page == "Plans & Billing":
            st.header("Plans & Billing")
            st.write("Billing details yahan dikhao.")

else:
    st.title("Welcome to TAGDA AI")
    st.markdown("Login karo aur shuru karo.")
