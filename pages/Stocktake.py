import streamlit as st
import pandas as pd
import os

# --- Utility Functions (copy from your main script or utils) ---
def clean_barcode(val):
    try:
        if pd.isnull(val) or val == "":
            return ""
        s = str(val).strip().replace('\u200b','').replace('\u00A0','')
        f = float(s)
        s = str(int(f))
        return s
    except:
        return str(val).strip()

def force_all_columns_to_string(df):
    for col in df.columns:
        df[col] = df[col].astype(str)
    return df

def clean_nans(df):
    return df.replace([pd.NA, 'nan'], '', regex=True)

# --- Load inventory ---
INVENTORY_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Inventory")
inventory_files = [f for f in os.listdir(INVENTORY_FOLDER) if f.lower().endswith(('.xlsx', '.csv'))]
selected_file = inventory_files[0]
if len(inventory_files) > 1:
    selected_file = st.selectbox("Select inventory file to use:", inventory_files)
INVENTORY_FILE = os.path.join(INVENTORY_FOLDER, selected_file)

def load_inventory():
    if os.path.exists(INVENTORY_FILE):
        if INVENTORY_FILE.lower().endswith('.xlsx'):
            df = pd.read_excel(INVENTORY_FILE)
        elif INVENTORY_FILE.lower().endswith('.csv'):
            df = pd.read_csv(INVENTORY_FILE)
        else:
            st.error("Unsupported inventory file type.")
            st.stop()
        df = force_all_columns_to_string(df)
        return df
    else:
        st.error(f"Inventory file '{INVENTORY_FILE}' not found.")
        st.stop()

df = load_inventory()
barcode_col = "BARCODE"
if barcode_col not in df.columns:
    st.error(f"No {barcode_col} column found in your inventory file!")
    st.stop()

st.title("Stocktake - Scan Barcodes")

# --- Session state for scanned barcodes ---
if "scanned_barcodes" not in st.session_state:
    st.session_state["scanned_barcodes"] = []

# --- Scan input using a form (clears on submit) ---
with st.form("stocktake_scan_form", clear_on_submit=True):
    scanned_barcode = st.text_input("Scan or enter barcode", key="stocktake_scan_input")
    submit = st.form_submit_button("Add Scanned Barcode")
    if submit:
        cleaned = clean_barcode(scanned_barcode)
        if cleaned == "":
            st.warning("Please scan or enter a barcode.")
        elif cleaned in st.session_state["scanned_barcodes"]:
            st.warning("Barcode already scanned in this session.")
        elif cleaned in df[barcode_col].map(clean_barcode).values:
            st.session_state["scanned_barcodes"].append(cleaned)
            st.success(f"Added barcode: {cleaned}")
        else:
            st.error("Barcode not found in inventory.")

# --- Table of scanned products ---
scanned_df = df[df[barcode_col].map(clean_barcode).isin(st.session_state["scanned_barcodes"])]
st.markdown("### Scanned Products Table")
st.dataframe(clean_nans(scanned_df), width='stretch')

# --- Download scanned products ---
if not scanned_df.empty:
    st.download_button(
        label="Download Scanned Table (CSV)",
        data=clean_nans(scanned_df).to_csv(index=False).encode('utf-8'),
        file_name="stocktake_scanned.csv",
        mime="text/csv"
    )
    st.download_button(
        label="Download Scanned Table (Excel)",
        data=clean_nans(scanned_df).to_excel(index=False),
        file_name="stocktake_scanned.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- Optional: Show missing items ---
if st.checkbox("Show missing products (in inventory but not scanned)"):
    missing_df = df[~df[barcode_col].map(clean_barcode).isin(st.session_state["scanned_barcodes"])]
    st.markdown("### Missing Products")
    st.dataframe(clean_nans(missing_df), width='stretch')
    if not missing_df.empty:
        st.download_button(
            label="Download Missing Table (CSV)",
            data=clean_nans(missing_df).to_csv(index=False).encode('utf-8'),
            file_name="stocktake_missing.csv",
            mime="text/csv"
        )
