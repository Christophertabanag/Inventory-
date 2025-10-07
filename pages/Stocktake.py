import streamlit as st
import pandas as pd
import os
import io

# --- Custom CSS for button colors ---
st.markdown("""
    <style>
    /* Main scan button green */
    div.stButton > button[kind="primary"] {
        background-color: #27ae60 !important;
        color: white !important;
        font-weight: bold;
        border-radius: 6px;
        border: none;
        height: 38px;
        min-width: 170px;
    }
    /* Empty table button red */
    div[data-testid="column"] button#empty_scanned_btn {
        background-color: #e74c3c !important;
        color: white !important;
        font-weight: bold;
    }
    /* Yes, Empty Table button blue */
    button#confirm_empty_scanned_btn {
        background-color: #3498db !important;
        color: white !important;
        font-weight: bold;
    }
    /* Cancel button yellow */
    button#cancel_empty_scanned_btn {
        background-color: #f1c40f !important;
        color: black !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

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

def format_rrp(val):
    try:
        f = float(str(val).replace("$", "").strip())
        return f"${f:.2f}"
    except Exception:
        return "$0.00"

# --- Use the same VISIBLE_FIELDS as your main script ---
VISIBLE_FIELDS = [
    "BARCODE", "LOCATION", "FRAMENUM", "MANUFACT", "MODEL", "SIZE",
    "FCOLOUR", "FRAMETYPE", "F GROUP", "SUPPLIER", "QUANTITY", "F TYPE", "TEMPLE",
    "DEPTH", "DIAG", "BASECURVE", "RRP", "EXCOSTPR", "COST PRICE", "TAXPC",
    "FRSTATUS", "AVAILFROM", "NOTE"
]

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

# --- Session state for scanned barcodes and delete prompt ---
if "scanned_barcodes" not in st.session_state:
    st.session_state["scanned_barcodes"] = []
if "confirm_clear_scanned_barcodes" not in st.session_state:
    st.session_state["confirm_clear_scanned_barcodes"] = False

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

# --- Empty Table Functionality with Confirmation Prompt ---
st.markdown("#### Manage Scanned Products Table")
clear_col, prompt_col = st.columns([1, 6], gap="small")
with clear_col:
    if st.button("🗑️ Empty Table", key="empty_scanned_btn"):
        st.session_state["confirm_clear_scanned_barcodes"] = True

if st.session_state.get("confirm_clear_scanned_barcodes", False):
    with prompt_col:
        st.warning("Are you sure you want to **empty the scanned products table**? This cannot be undone.")
        yes_col, no_col = st.columns([1, 1])
        with yes_col:
            if st.button("Yes, Empty Table", key="confirm_empty_scanned_btn"):
                st.session_state["scanned_barcodes"].clear()
                st.session_state["confirm_clear_scanned_barcodes"] = False
                st.success("Scanned products table emptied.")
        with no_col:
            if st.button("Cancel", key="cancel_empty_scanned_btn"):
                st.session_state["confirm_clear_scanned_barcodes"] = False

# --- Table formatting helper ---
def format_inventory_table(input_df):
    df_disp = input_df.copy()
    # Only keep columns that exist & match the order in VISIBLE_FIELDS
    cols = [col for col in VISIBLE_FIELDS if col in df_disp.columns]
    df_disp = df_disp[cols]
    # Format columns as in Inventory Manager
    if "BARCODE" in df_disp.columns:
        df_disp["BARCODE"] = df_disp["BARCODE"].map(clean_barcode)
    if "RRP" in df_disp.columns:
        df_disp["RRP"] = df_disp["RRP"].apply(format_rrp).astype(str)
    return clean_nans(df_disp)

# --- Table of scanned products ---
scanned_df = df[df[barcode_col].map(clean_barcode).isin(st.session_state["scanned_barcodes"])]
st.markdown("### Scanned Products Table")
st.dataframe(format_inventory_table(scanned_df), width='stretch')

# --- Download scanned products ---
if not scanned_df.empty:
    st.download_button(
        label="Download Scanned Table (CSV)",
        data=format_inventory_table(scanned_df).to_csv(index=False).encode('utf-8'),
        file_name="stocktake_scanned.csv",
        mime="text/csv"
    )
    # Excel download with BytesIO buffer
    excel_buffer = io.BytesIO()
    format_inventory_table(scanned_df).to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    st.download_button(
        label="Download Scanned Table (Excel)",
        data=excel_buffer,
        file_name="stocktake_scanned.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- Optional: Show missing items ---
if st.checkbox("Show missing products (in inventory but not scanned)"):
    missing_df = df[~df[barcode_col].map(clean_barcode).isin(st.session_state["scanned_barcodes"])]
    st.markdown("### Missing Products")
    st.dataframe(format_inventory_table(missing_df), width='stretch')
    if not missing_df.empty:
        st.download_button(
            label="Download Missing Table (CSV)",
            data=format_inventory_table(missing_df).to_csv(index=False).encode('utf-8'),
            file_name="stocktake_missing.csv",
            mime="text/csv"
        )
        excel_buffer_missing = io.BytesIO()
        format_inventory_table(missing_df).to_excel(excel_buffer_missing, index=False)
        excel_buffer_missing.seek(0)
        st.download_button(
            label="Download Missing Table (Excel)",
            data=excel_buffer_missing,
            file_name="stocktake_missing.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
