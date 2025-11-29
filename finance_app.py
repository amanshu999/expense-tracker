import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
DATA_FILE = "finance_data.json"
st.set_page_config(page_title="Personal Finance Tracker", page_icon="💰", layout="wide")

# --- DATA HANDLING ---
def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {"wallet_balance": 0.0, "expenses": [], "debts": []}
        with open(DATA_FILE, 'w') as f:
            json.dump(default_data, f)
        return default_data
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"wallet_balance": 0.0, "expenses": [], "debts": []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Load data at start
data = load_data()

# --- SIDEBAR: ADD TRANSACTIONS ---
with st.sidebar:
    st.header("➕ Add New Entry")
    
    # Transaction Type Selector
    type_option = st.radio("Select Type:", ["Expense 💸", "Someone owes ME 🟢", "I owe Someone 🟠"])
    
    with st.form("entry_form", clear_on_submit=True):
        amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0, format="%.2f")
        desc = st.text_input("Description / Person Name")
        submitted = st.form_submit_button("Add Entry")
        
        if submitted and amount > 0 and desc:
            new_entry = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "amount": amount
            }
            
            if "Expense" in type_option:
                new_entry["description"] = desc
                data["wallet_balance"] -= amount
                data["expenses"].append(new_entry)
                st.success(f"Spent ₹{amount} on {desc}")
                
            elif "owes ME" in type_option:
                new_entry["person"] = desc
                new_entry["type"] = "receivable"
                data["debts"].append(new_entry)
                st.success(f"Added receivable from {desc}")
                
            else: # I owe Someone
                new_entry["person"] = desc
                new_entry["type"] = "payable"
                data["debts"].append(new_entry)
                st.success(f"Added payable to {desc}")
            
            save_data(data)

    st.markdown("---")
    
    # Wallet Management
    st.subheader("💼 Wallet Settings")
    current_wallet = data.get("wallet_balance", 0.0)
    new_wallet = st.number_input("Update Actual Cash Balance (₹)", value=current_wallet)
    if st.button("Update Wallet Balance"):
        data["wallet_balance"] = new_wallet
        save_data(data)
        st.success("Wallet updated!")


# --- MAIN DASHBOARD ---
st.title("💰 Personal Finance Dashboard")
st.markdown("Track your expenses, debts, and net worth in one place.")

# CALCULATIONS
expenses = data["expenses"]
debts = data["debts"]
wallet = data["wallet_balance"]

total_spent = sum(item['amount'] for item in expenses)
to_receive = sum(item['amount'] for item in debts if item['type'] == 'receivable')
to_pay = sum(item['amount'] for item in debts if item['type'] == 'payable')
net_position = (wallet + to_receive) - to_pay

# --- TOP METRICS ROW ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Total Spent (All Time)", value=f"₹{total_spent:,.2f}", delta="- Money Gone", delta_color="inverse")

with col2:
    st.metric(label="To Receive (Assets)", value=f"₹{to_receive:,.2f}", delta="People owe you", delta_color="normal")

with col3:
    st.metric(label="To Pay (Liabilities)", value=f"₹{to_pay:,.2f}", delta="- You owe", delta_color="inverse")

with col4:
    st.metric(label="Net Position (Total)", value=f"₹{net_position:,.2f}", delta="True Worth")

# Divider
st.markdown("---")

# --- DATA TABLE & HISTORY ---
st.subheader("📝 Recent Activity Log")

# Prepare Data for Table
table_data = []
for x in expenses:
    table_data.append({"Date": x['date'], "Type": "Expense", "Description": x['description'], "Amount": -x['amount']})
for x in debts:
    t_label = "Incoming (Owed to You)" if x['type'] == 'receivable' else "Outgoing (You Owe)"
    # For display logic: Receivables are positive assets, Payables are negative liabilities
    amt_display = x['amount'] if x['type'] == 'receivable' else -x['amount']
    table_data.append({"Date": x['date'], "Type": t_label, "Description": x['person'], "Amount": amt_display})

# Convert to Pandas DataFrame
if table_data:
    df = pd.DataFrame(table_data)
    # Sort by Date (newest first) but since date is string, we rely on list order mostly. 
    # Let's just reverse the list order for display
    df = df.iloc[::-1] 

    # Style the dataframe (Highlight negatives in red, positives in green)
    def color_negative_red(val):
        color = 'red' if val < 0 else 'green'
        return f'color: {color}'

    # --- FIX APPLIED HERE: Replaced use_container_width=True with width='stretch' ---
    st.dataframe(df.style.map(color_negative_red, subset=['Amount']), width='stretch')
    
    # --- EXPORT BUTTON ---
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv,
        file_name='finance_data.csv',
        mime='text/csv',
    )
    
    # --- DELETE SECTION ---
    with st.expander("🗑️ Manage / Delete Records"):
        st.warning("Select a record to delete. This action cannot be undone.")
        
        # Create a list of strings to identify records
        # Format: "Index | Date | Desc | Amount"
        delete_options = [f"{i} | {row['Date']} | {row['Description']} | ₹{abs(row['Amount'])}" for i, row in df.iterrows()]
        
        selected_to_delete = st.selectbox("Select Record:", ["None"] + delete_options)
        
        if st.button("Delete Selected Record"):
            if selected_to_delete != "None":
                # Extract the index from the string
                idx_to_remove = int(selected_to_delete.split(" | ")[0])
                
                # Logic to remove from original JSON structure
                row = df.loc[idx_to_remove]
                target_date = row['Date']
                target_desc = row['Description']
                target_amt = abs(row['Amount'])
                target_type = row['Type']
                
                deleted = False
                
                if target_type == "Expense":
                    for i, item in enumerate(data["expenses"]):
                        if item['date'] == target_date and item['description'] == target_desc and item['amount'] == target_amt:
                            data["wallet_balance"] += target_amt # Refund wallet
                            del data["expenses"][i]
                            deleted = True
                            break
                else:
                    # Debts
                    internal_type = "receivable" if "Incoming" in target_type else "payable"
                    for i, item in enumerate(data["debts"]):
                        if item['date'] == target_date and item['person'] == target_desc and item['amount'] == target_amt and item['type'] == internal_type:
                            del data["debts"][i]
                            deleted = True
                            break
                
                if deleted:
                    save_data(data)
                    st.success("Record deleted successfully! Refreshing...")
                    st.rerun()
                else:
                    st.error("Could not find record in database.")
else:
    st.info("No transactions yet. Add one from the sidebar!")

# --- FOOTER ---
st.markdown("---")
st.caption(f"Current Cash in Hand: **₹{wallet:,.2f}**")