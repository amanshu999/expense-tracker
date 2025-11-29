import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from fpdf import FPDF

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

# --- PDF GENERATION FUNCTION ---
def create_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Personal Finance Report", ln=True, align='C')
    pdf.ln(10)
    col_widths = [30, 40, 80, 30] 
    pdf.set_font("Arial", 'B', 10)
    headers = dataframe.columns
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, str(header), border=1)
    pdf.ln()
    pdf.set_font("Arial", size=10)
    for index, row in dataframe.iterrows():
        datum = [str(row['Date']), str(row['Type']), str(row['Description']), f"Rs {row['Amount']:.2f}"]
        for i, data in enumerate(datum):
            text = str(data)[:30] 
            pdf.cell(col_widths[i], 10, text, border=1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1')

# Load data
data = load_data()

# --- SIDEBAR: ADD TRANSACTIONS ---
with st.sidebar:
    st.header("➕ Add New Entry")
    type_option = st.radio("Select Type:", ["Expense 💸", "Someone owes ME 🟢", "I owe Someone 🟠"])
    
    with st.form("entry_form", clear_on_submit=True):
        amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0, format="%.2f")
        desc = st.text_input("Description / Person Name")
        submitted = st.form_submit_button("Add Entry")
        
        if submitted and amount > 0 and desc:
            new_entry = {"date": datetime.now().strftime("%Y-%m-%d"), "amount": amount}
            if "Expense" in type_option:
                new_entry["description"] = desc
                data["wallet_balance"] -= amount
                data["expenses"].append(new_entry)
                st.success(f"Spent ₹{amount}")
            elif "owes ME" in type_option:
                new_entry["person"] = desc
                new_entry["type"] = "receivable"
                data["debts"].append(new_entry)
                st.success(f"Added receivable from {desc}")
            else: 
                new_entry["person"] = desc
                new_entry["type"] = "payable"
                data["debts"].append(new_entry)
                st.success(f"Added payable to {desc}")
            save_data(data)

    st.markdown("---")
    st.subheader("💼 Wallet Settings")
    current_wallet = data.get("wallet_balance", 0.0)
    new_wallet = st.number_input("Update Actual Cash Balance (₹)", value=current_wallet)
    if st.button("Update Wallet Balance"):
        data["wallet_balance"] = new_wallet
        save_data(data)
        st.success("Wallet updated!")

# --- MAIN DASHBOARD ---
st.title("💰 Personal Finance Dashboard")
expenses = data["expenses"]
debts = data["debts"]
wallet = data["wallet_balance"]

total_spent = sum(item['amount'] for item in expenses)
to_receive = sum(item['amount'] for item in debts if item['type'] == 'receivable')
to_pay = sum(item['amount'] for item in debts if item['type'] == 'payable')
net_position = (wallet + to_receive) - to_pay

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Spent", f"₹{total_spent:,.2f}", "- Money Gone", delta_color="inverse")
col2.metric("To Receive", f"₹{to_receive:,.2f}", "Assets", delta_color="normal")
col3.metric("To Pay", f"₹{to_pay:,.2f}", "- Liabilities", delta_color="inverse")
col4.metric("Net Position", f"₹{net_position:,.2f}", "True Worth")
st.markdown("---")

# --- DATA TABLE ---
st.subheader("📝 Recent Activity Log")
table_data = []
# We use a unique ID approach here to make finding records easier for edit/delete
for i, x in enumerate(expenses):
    table_data.append({"ID": f"exp_{i}", "Date": x['date'], "Type": "Expense", "Description": x['description'], "Amount": -x['amount'], "RawAmount": x['amount']})
for i, x in enumerate(debts):
    t_label = "Incoming (Owed to You)" if x['type'] == 'receivable' else "Outgoing (You Owe)"
    amt_display = x['amount'] if x['type'] == 'receivable' else -x['amount']
    table_data.append({"ID": f"debt_{i}", "Date": x['date'], "Type": t_label, "Description": x['person'], "Amount": amt_display, "RawAmount": x['amount']})

if table_data:
    df = pd.DataFrame(table_data)
    df_display = df.drop(columns=['ID', 'RawAmount']).iloc[::-1] # Hide technical columns for display
    
    def color_negative_red(val):
        color = 'red' if val < 0 else 'green'
        return f'color: {color}'
    st.dataframe(df_display.style.map(color_negative_red, subset=['Amount']), width=1000)
    
    # --- EXPORT SECTION ---
    st.markdown("### 📤 Export Data")
    d1, d2, d3 = st.columns(3)
    d1.download_button("📄 Download CSV", df_display.to_csv(index=False).encode('utf-8'), 'finance_data.csv', 'text/csv')
    d2.download_button("💾 Download JSON", json.dumps(data, indent=4), 'finance_backup.json', 'application/json')
    try:
        d3.download_button("📑 Download PDF", create_pdf(df_display), 'finance_report.pdf', 'application/pdf')
    except:
        d3.error("PDF Error")

    # --- MANAGE RECORDS (EDIT / DELETE) ---
    st.markdown("---")
    st.subheader("🛠️ Manage Records (Edit / Delete)")
    
    with st.expander("Click to Edit or Delete a Record", expanded=True):
        # Create select options
        # We map the display string back to the ID
        record_map = {f"{row['Date']} | {row['Type']} | {row['Description']} | ₹{abs(row['Amount'])}": row['ID'] for i, row in df.iterrows()}
        selected_label = st.selectbox("Select a Transaction:", ["Select..."] + list(record_map.keys()))

        if selected_label != "Select...":
            selected_id = record_map[selected_label]
            
            # Find the specific row data
            row_data = df[df['ID'] == selected_id].iloc[0]
            
            st.info(f"Selected: **{row_data['Description']}** ({row_data['Type']})")
            
            tab_edit, tab_delete = st.tabs(["✏️ Edit Record", "🗑️ Delete Record"])
            
            # --- EDIT FUNCTIONALITY ---
            with tab_edit:
                with st.form("edit_form"):
                    new_desc = st.text_input("Description / Name", value=row_data['Description'])
                    new_amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0, value=float(row_data['RawAmount']))
                    # We don't allow changing Type (Expense -> Debt) as it complicates logic too much. Better to delete and re-add.
                    
                    update_btn = st.form_submit_button("Update Record")
                    
                    if update_btn:
                        # 1. Reverse the old transaction
                        if "exp" in selected_id:
                            idx = int(selected_id.split("_")[1])
                            old_amt = data["expenses"][idx]["amount"]
                            data["wallet_balance"] += old_amt # Refund wallet
                            
                            # 2. Apply new transaction
                            data["expenses"][idx]["description"] = new_desc
                            data["expenses"][idx]["amount"] = new_amount
                            data["wallet_balance"] -= new_amount # Deduct new amount
                            
                        elif "debt" in selected_id:
                            idx = int(selected_id.split("_")[1])
                            data["debts"][idx]["person"] = new_desc
                            data["debts"][idx]["amount"] = new_amount
                        
                        save_data(data)
                        st.success("Record updated successfully!")
                        st.rerun()

            # --- DELETE FUNCTIONALITY ---
            with tab_delete:
                st.warning("Are you sure? This will remove the record permanently.")
                if st.button("Confirm Delete", type="primary"):
                    if "exp" in selected_id:
                        idx = int(selected_id.split("_")[1])
                        # Refund wallet before deleting
                        data["wallet_balance"] += data["expenses"][idx]["amount"]
                        del data["expenses"][idx]
                    elif "debt" in selected_id:
                        idx = int(selected_id.split("_")[1])
                        del data["debts"][idx]
                    
                    save_data(data)
                    st.success("Record deleted!")
                    st.rerun()

else:
    st.info("No transactions to manage.")

st.caption(f"Current Cash in Hand: **₹{wallet:,.2f}**")
