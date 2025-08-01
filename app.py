# app.py
import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
import matplotlib.pyplot as plt
from datetime import datetime
import os

# ------------------ Database Setup ------------------
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL
)''')
conn.commit()

# ------------------ Auth Functions ------------------
def signup_user(username, password):
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    result = c.fetchone()
    if result and bcrypt.checkpw(password.encode(), result[0].encode()):
        return True
    return False

# ------------------ Expense File Functions ------------------
def load_expense_data(username):
    os.makedirs("data", exist_ok=True)
    file = f"data/{username}_expenses.csv"
    if os.path.exists(file):
        return pd.read_csv(file, parse_dates=["Date"])
    return pd.DataFrame(columns=["Date", "Category", "Description", "Amount"])

def save_expense_data(username, df):
    os.makedirs("data", exist_ok=True)
    file = f"data/{username}_expenses.csv"
    df.to_csv(file, index=False)

# ------------------ Streamlit App UI ------------------
st.set_page_config(page_title="Expense Tracker", layout="wide")
st.title("💸 Personal Expense Tracker")

menu = ["Login", "Signup"]
choice = st.sidebar.selectbox("Menu", menu)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if choice == "Signup":
    st.subheader("Create New Account")
    new_user = st.text_input("Username", key="signup_user")
    new_password = st.text_input("Password", type='password', key="signup_pass")
    if st.button("Signup"):
        if new_user and new_password:
            if signup_user(new_user.strip(), new_password):
                st.success("Account created. Please login.")
            else:
                st.error("Username already exists.")
        else:
            st.warning("Please enter both username and password.")

elif choice == "Login":
    st.subheader("Login to Your Account")
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type='password', key="login_pass")
    if st.button("Login"):
        if login_user(username.strip(), password):
            st.session_state.logged_in = True
            st.session_state.username = username.strip()
            st.success(f"Welcome, {username}!")
        else:
            st.error("Incorrect username or password.")

# ------------------ Main Tracker ------------------
if st.session_state.logged_in:
    username = st.session_state.username
    st.sidebar.success(f"Logged in as {username}")

    df = load_expense_data(username)

    # Form to Add Expense
    st.sidebar.header("Add Expense")
    with st.sidebar.form("expense_form"):
        date = st.date_input("Date", value=datetime.today())
        category = st.selectbox("Category", ["Food", "Transport", "Bills", "Shopping", "Other"])
        description = st.text_input("Description")
        amount = st.number_input("Amount", min_value=0.0, format="%.2f")
        submitted = st.form_submit_button("Add")
        if submitted:
            new_data = pd.DataFrame([[date, category, description, amount]],
                                    columns=["Date", "Category", "Description", "Amount"])
            df = pd.concat([df, new_data], ignore_index=True)
            save_expense_data(username, df)
            st.success("Expense added successfully.")

    # Show Table
    st.subheader("📄 Expense Table")
    if not df.empty:
        st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True)

        # Visuals
        st.subheader("📊 Visualizations")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Category-wise Expenses")
            category_sum = df.groupby("Category")["Amount"].sum()
            fig1, ax1 = plt.subplots()
            ax1.pie(category_sum, labels=category_sum.index, autopct="%1.1f%%")
            ax1.axis('equal')
            st.pyplot(fig1)

        with col2:
            st.markdown("### Monthly Expense Trend")
            df['Month'] = pd.to_datetime(df['Date']).dt.to_period('M').astype(str)
            monthly_sum = df.groupby("Month")["Amount"].sum()
            st.line_chart(monthly_sum)

        st.download_button(
            label="⬇ Download My Expenses (CSV)",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=f"{username}_expenses.csv",
            mime="text/csv"
        )
    else:
        st.info("No expenses yet. Add some from the sidebar.")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.experimental_rerun()
