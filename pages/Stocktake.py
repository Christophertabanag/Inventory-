import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime
import shutil

# --- Custom CSS for button colors ---
st.markdown("""
    <style>
    div.stButton > button[kind="primary"] {
        background-color: #27ae60 !important;
        color: white !important;
        font-weight: bold;
        border-radius: 6px;
        border: none;
        height: 38px;
        min-width: 170px;
    }
    div[data-testid="column"] button#empty_scanned_btn {
        background-color: #e74c3c !important;
        color: white !important;
        font-weight: bold;
    }
    button#confirm_empty_scanned_btn {
        background-color: #3498db !important;
        color: white !important;
        font-weight: bold;
    }
    button#cancel_empty_scanned_btn {
        background-color: #f1c40f !important;
        color: black !important;
        font-weight: bold;
    }
    .stAlert {
        font-size: 1.1em;
    }
    </style>
""", unsafe_allow_html=True)

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

def clean_for_display(df):
    df = df.copy()
    if "BARCODE" in df.columns:
        df["BARCODE"] = df["BARCODE"].apply(lambda x: str(int(float(x))) if pd.notnull(x) and str(x).replace('.','',1).isdigit() and float(x).is_integer() else x)
    if "QUANTITY" in df.columns:
        df["QUANTITY"] = df["QUANTITY"].apply(lambda x: str(int(float(x))) if pd.notnull(x) and str(x).replace('.','',1).isdigit() and float(x).is_integer() else x)
    df = df.replace("nan", "").replace(pd.NA, "").replace(float("nan"), "")
    return df

VISIBLE_FIELDS = [
    "BARCODE", "LOCATION", "FRAMENUM", "MANUFACT", "MODEL", "SIZE",
    "FCOLOUR", "FRAMETYPE", "F GROUP", "SUPPLIER", "QUANTITY", "F TYPE", "TEMPLE",
    "DEPTH", "DIAG", "BASECURVE", "RRP", "EXCOSTPR", "COST PRICE", "TAXPC",
    "FRSTATUS", "AVAILFROM", "NOTE"
]

# --- Shared scanned barcodes CSV ---
SCANNED_FILE = os.path.join(os.path.dirname(__file__), "..", "scanned_barcodes.csv")
BACKUP_FOLDER = os.path.join(os.path.dirname(__file__), "..", "scanned_backups")
os.makedirs(BACKUP_FOLDER, exist_ok=True)

def backup_scanned_file():
    if os.path.exists(SCANNED_FILE):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2(SCANNED_FILE, os.path.join(BACKUP_FOLDER, f"scanned_barcodes_{timestamp}.csv"))

def load_scanned_barcodes():
    if os.path.exists(SCANNED_FILE):
        df = pd.read_csv(SCANNED_FILE, dtype={"barcode": str})
        # If no timestamp col, add it as empty
        if "timestamp" not in df.columns:
            df["timestamp"] = ""
        return df
    return pd.DataFrame(columns=["barcode", "timestamp"])

def save_scanned_barcodes(df):
    df.to_csv(SCANNED_FILE, index=False)

def add_scan(barcode):
    df = load_scanned_barcodes()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_row = {"barcode": barcode, "timestamp": now}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    backup_scanned_file()
    save_scanned_barcodes(df)

def remove_scan(barcode, timestamp=None):
    df = load_scanned_barcodes()
    if timestamp:
        df = df[~((df["barcode"] == barcode) & (df["timestamp"] == timestamp))]
    else:
        df = df[df["barcode"] != barcode]
    backup_scanned_file()
    save_scanned_barcodes(df)

def clear_scans():
    backup_scanned_file()
    save_scanned_barcodes(pd.DataFrame(columns=["barcode", "timestamp"]))

def undo_last_scan():
    df = load_scanned_barcodes()
    if not df.empty:
        df = df.iloc[:-1]
        backup_scanned_file()
        save_scanned_barcodes(df)
        return True
    return False

def get_duplicates(df):
    return df["barcode"][df.duplicated("barcode", keep=False)]

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

# Clean the DataFrame barcodes as strings
df[barcode_col] = df[barcode_col].map(clean_barcode).astype(str)

st.title("Stocktake - Scan Barcodes (Shared, Robust)")

# --- Load and display scanned barcodes (with timestamp) ---
scanned_df = load_scanned_barcodes()

# --- Scan input using a form (clears on submit) ---
with st.form("stocktake_scan_form", clear_on_submit=True):
    scanned_barcode = st.text_input("Scan or enter barcode", key="stocktake_scan_input")
    submit = st.form_submit_button("Add Scanned Barcode")
    if submit:
        cleaned = clean_barcode(scanned_barcode)
        if cleaned == "":
            st.error("❌ Please scan or enter a barcode.")
        elif cleaned not in df[barcode_col].values:
            st.error("❌ Barcode not found in inventory.")
        else:
            # Allow duplicate scans, but highlight them in table
            add_scan(cleaned)
            st.success(f"✅ Added barcode: {cleaned}")
            if hasattr(st, "rerun"):
                st.rerun()
            elif hasattr(st, "experimental_rerun"):
                st.experimental_rerun()

# --- Undo Last Scan Button ---
if not scanned_df.empty:
    if st.button("Undo Last Scan"):
        if undo_last_scan():
            st.info("Last scan undone.")
            if hasattr(st, "rerun"):
                st.rerun()
            elif hasattr(st, "experimental_rerun"):
                st.experimental_rerun()
        else:
            st.warning("No scan to undo.")

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
                clear_scans()
                st.session_state["confirm_clear_scanned_barcodes"] = False
                st.success("Scanned products table emptied.")
                if hasattr(st, "rerun"):
                    st.rerun()
                elif hasattr(st, "experimental_rerun"):
                    st.experimental_rerun()
        with no_col:
            if st.button("Cancel", key="cancel_empty_scanned_btn"):
                st.session_state["confirm_clear_scanned_barcodes"] = False

# --- Search & Filter ---
search_query = st.text_input("🔎 Search scanned barcodes / product details")

# --- Build scanned table (latest scan on top) ---
display_scans = scanned_df.copy()
display_scans = display_scans[::-1]  # most recent first

# Merge with inventory for product details
if not display_scans.empty:
    merged = display_scans.merge(
        df,
        left_on="barcode",
        right_on=barcode_col,
        how="left",
        suffixes=('', '_inv')
    )
    merged["Duplicate"] = merged["barcode"].isin(get_duplicates(display_scans))
    merged["Timestamp"] = merged["timestamp"]
    merged = merged.drop(columns=[barcode_col, "timestamp"], errors="ignore")
    # Place important columns first
    order = ["barcode", "Timestamp", "Duplicate"] + [col for col in VISIBLE_FIELDS if col in merged.columns]
    merged = merged[[col for col in order if col in merged.columns]]

    # --- Search & filter logic ---
    if search_query.strip():
        mask = pd.Series(False, index=merged.index)
        for col in merged.columns:
            mask = mask | merged[col].astype(str).str.contains(search_query, case=False, na=False)
        merged = merged[mask]

    # --- Highlight duplicates ---
    def highlight_dupes(val, is_dup):
        if is_dup:
            return "background-color: #ffe6e6; color: #d9534f; font-weight:bold;"
        return ""

    st.markdown("### Scanned Products Table")
    st.dataframe(
        merged.style.apply(
            lambda row: [highlight_dupes(v, row["Duplicate"]) if col == "barcode" else "" for col, v in row.items()],
            axis=1
        ),
        width='stretch',
        hide_index=True
    )

    # --- Remove a specific scan by barcode and timestamp ---
    st.markdown("Remove a specific scan:")
    remove_row = st.selectbox(
        "Choose scan to remove",
        options=merged[["barcode", "Timestamp"]].apply(lambda r: f"{r['barcode']} @ {r['Timestamp']}", axis=1) if not merged.empty else [],
        key="remove_selectbox"
    )
    if st.button("Remove Selected"):
        if remove_row:
            barcode, ts = remove_row.split(' @ ')
            remove_scan(barcode, ts)
            st.success(f"Removed scan: {barcode} @ {ts}")
            if hasattr(st, "rerun"):
                st.rerun()
            elif hasattr(st, "experimental_rerun"):
                st.experimental_rerun()
        else:
            st.warning("No scan selected for removal.")

    # --- Download scanned products ---
    st.download_button(
        label="Download Scanned Table (CSV)",
        data=merged.to_csv(index=False).encode('utf-8'),
        file_name="stocktake_scanned.csv",
        mime="text/csv"
    )
    excel_buffer = io.BytesIO()
    merged.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    st.download_button(
        label="Download Scanned Table (Excel)",
        data=excel_buffer,
        file_name="stocktake_scanned.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No scanned products to display.")

# --- Optional: Show missing items ---
if st.checkbox("Show missing products (in inventory but not scanned)"):
    missing_df = df[~df[barcode_col].isin(scanned_df["barcode"].tolist())]
    st.markdown("### Missing Products")
    st.dataframe(clean_for_display(missing_df), width='stretch')
    if not missing_df.empty:
        st.download_button(
            label="Download Missing Table (CSV)",
            data=clean_for_display(missing_df).to_csv(index=False).encode('utf-8'),
            file_name="stocktake_missing.csv",
            mime="text/csv"
        )
        excel_buffer_missing = io.BytesIO()
        clean_for_display(missing_df).to_excel(excel_buffer_missing, index=False)
        excel_buffer_missing.seek(0)
        st.download_button(
            label="Download Missing Table (Excel)",
            data=excel_buffer_missing,
            file_name="stocktake_missing.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# --- Backup management ---
if st.checkbox("Show available backups and restore"):
    backups = sorted([f for f in os.listdir(BACKUP_FOLDER) if f.endswith('.csv')])
    if backups:
        selected_backup = st.selectbox("Select a backup to restore", backups)
        if st.button("Restore Selected Backup"):
            backup_path = os.path.join(BACKUP_FOLDER, selected_backup)
            shutil.copy2(backup_path, SCANNED_FILE)
            st.success(f"Restored backup: {selected_backup}")
            if hasattr(st, "rerun"):
                st.rerun()
            elif hasattr(st, "experimental_rerun"):
                st.experimental_rerun()
        st.download_button(
            label="Download Selected Backup",
            data=open(os.path.join(BACKUP_FOLDER, selected_backup), "rb").read(),
            file_name=selected_backup,
            mime="text/csv"
        )
    else:
        st.info("No backups available yet.")
