import io
import re
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="WFP Jijiga AO – Process Monitoring Cleaner & Tableau Prep",
    layout="wide"
)

# ---------- Helper functions ----------

SYSTEM_PREFIXES = ["_", "meta:", "instance", "start", "end"]
SYSTEM_NAMES = {
    "_id","_uuid","_submission_time","_xform_id","_version","_status",
    "starttime","endtime","deviceid","today"
}

META_PATTERNS = [
    "region","sub office","sub_office","zone","woreda","wereda","kebele",
    "village","camp","fdp","distribution point","health facility","tsfp",
    "market","partner","implementing partner","cooperating partner",
    "date","monitoring month","monitoring year","collected by",
    "enumerator","latitude","longitude","altitude","gps"
]

def is_system_column(col: str) -> bool:
    low = col.lower().strip()
    if low in SYSTEM_NAMES:
        return True
    for p in SYSTEM_PREFIXES:
        if low.startswith(p):
            return True
    return False

def standardize_column_name(col: str) -> str:
    low = col.lower().strip()
    # location/admin
    if "region" in low and "sub office" not in low:
        return "region"
    if "sub office" in low:
        return "sub_office"
    if "zone" in low:
        return "zone"
    if "wereda" in low or "woreda" in low:
        return "woreda"
    if "kebele" in low and "specify" not in low:
        return "kebele"
    if "village" in low or ("camp" in low and "name" in low):
        return "village"
    if "fdp" in low and "name" in low:
        return "fdp_name"
    if "market" in low and "name" in low:
        return "market_name"
    if "health facility" in low or "tsfp centre" in low or "tsfp center" in low:
        return "tsfp_center"
    if "implementing partner" in low or "cooperating partner" in low or ("partner" in low and "name" in low):
        return "partner_name"
    # date / time
    if "date" in low and ("visit" in low or "monitor" in low or "interview" in low or low == "date"):
        return "visit_date"
    if "monitoring year" in low:
        return "monitoring_year"
    if "monitoring month" in low:
        return "monitoring_month"
    # enumerator
    if "information collected by" in low or "name of wfp staff" in low or "name of enumerator" in low or "interviewer" in low:
        return "enumerator"
    # gps
    if "latitude" in low:
        return "gps_lat"
    if "longitude" in low:
        return "gps_lon"
    if "altitude" in low:
        return "gps_alt"
    # default: cleaned snake_case
    cleaned = re.sub(r"[^0-9a-zA-Z]+","_", low).strip("_")
    return cleaned

def classify_meta_columns(columns):
    meta = []
    indicator = []
    for c in columns:
        low = c.lower()
        if any(p in low for p in ["region","zone","wereda","woreda","kebele","village","camp","fdp","market","tsfp","partner","date","month","year","enumerator","latitude","longitude","altitude"]):
            meta.append(c)
        else:
            indicator.append(c)
    return meta, indicator

def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Cleaned")
    buf.seek(0)
    return buf.getvalue()

# ---------- Sidebar / Help ----------

with st.sidebar:
    st.title("ℹ️ Help / Information")
    st.markdown("**WFP Jijiga Area Office – M&E Unit**")
    st.markdown(
        "- Upload raw MoDA / Excel / CSV process monitoring exports.\n"
        "- The app will remove Kobo/system fields, standardize key columns, and optionally create a Tableau-ready long-format file.\n"
        "- You can download both the cleaned wide file and the long-format file."
    )
    with st.expander("How does the cleaning work?", expanded=False):
        st.markdown(
            "- Drops Kobo/system columns (e.g. `_id`, `_uuid`, `_submission_time`, `starttime`, `endtime`).\n"
            "- Tries to standardize location fields to: `region`, `sub_office`, `zone`, `woreda`, `kebele`, `village`, `fdp_name`, `tsfp_center`, `market_name`.\n"
            "- Tries to standardize partner and date fields to: `partner_name`, `visit_date`, `monitoring_year`, `monitoring_month`.\n"
            "- Long format uses all non-metadata fields as indicators and melts them into `indicator_name` / `indicator_value`."
        )

st.markdown("<h1 style='color:#0072BC;'>WFP Jijiga – Process Monitoring Cleaner & Tableau Prep v2</h1>", unsafe_allow_html=True)
st.caption("Standalone app for MoDA/Excel process monitoring data – cleaning, renaming, and Tableau-ready reshaping.")

uploaded = st.file_uploader(
    "📁 Upload MoDA / Excel / CSV Process Monitoring File",
    type=["xlsx","xls","csv"]
)

if uploaded is not None:
    st.success(f"Uploaded: {uploaded.name}")
    filetype = "csv" if uploaded.name.lower().endswith(".csv") else "excel"

    if filetype == "excel":
        xls = pd.ExcelFile(uploaded)
        sheet_name = st.selectbox("Select sheet to process", xls.sheet_names)
        df_raw = pd.read_excel(xls, sheet_name=sheet_name)
    else:
        sheet_name = None
        df_raw = pd.read_csv(uploaded)

    st.write("### 🔍 Raw Preview")
    st.dataframe(df_raw.head())

    drop_system = st.checkbox("Drop Kobo/system fields (recommended)", value=True)
    do_standardize = st.checkbox("Standardize key metadata fields (region, woreda, partner, date, etc.)", value=True)
    make_long = st.checkbox("Generate Tableau-ready long-format dataset", value=True)

    log_lines = []

    df = df_raw.copy()

    # Drop system columns
    if drop_system:
        before = df.shape[1]
        keep_cols = [c for c in df.columns if not is_system_column(c)]
        dropped = [c for c in df.columns if c not in keep_cols]
        df = df[keep_cols]
        log_lines.append(f"Dropped {before - len(keep_cols)} system columns: {', '.join(dropped) if dropped else 'None'}")

    # Standardize names
    if do_standardize:
        new_cols = {}
        for c in df.columns:
            new_cols[c] = standardize_column_name(c)
        df.rename(columns=new_cols, inplace=True)
        log_lines.append("Standardized column names to snake_case and aligned key metadata fields (region, woreda, partner_name, etc.).")

    st.write("### ✅ Cleaned (Wide) Preview")
    st.dataframe(df.head())

    # Decide meta vs indicator columns
    meta_cols, indicator_cols = classify_meta_columns(df.columns.tolist())
    # ensure meta_cols at least includes some known ones if present
    for c in ["region","sub_office","zone","woreda","kebele","village","fdp_name","tsfp_center","market_name","partner_name","visit_date","enumerator"]:
        if c in df.columns and c not in meta_cols:
            meta_cols.append(c)
            if c in indicator_cols:
                indicator_cols.remove(c)

    meta_cols = sorted(list(dict.fromkeys(meta_cols)))  # unique & stable

    st.write("#### 🧩 Detected metadata fields")
    st.code(", ".join(meta_cols) if meta_cols else "None detected – the app will treat all fields as indicators for long-format.")

    if make_long:
        if not meta_cols:
            st.warning("No metadata fields detected – long-format will use all columns as indicators.")
            meta_use = []
        else:
            meta_use = meta_cols

        indicator_use = [c for c in df.columns if c not in meta_use]
        log_lines.append(f"Identified {len(meta_use)} metadata columns and {len(indicator_use)} indicator columns for long-format reshaping.")

        if indicator_use:
            df_long = df.melt(
                id_vars=meta_use,
                value_vars=indicator_use,
                var_name="indicator_name",
                value_name="indicator_value"
            )
            st.write("### 📊 Tableau-ready Long Format Preview")
            st.dataframe(df_long.head())
        else:
            df_long = None
            st.warning("No indicator columns identified for long-format dataset.")

    # Downloads
    st.markdown("### 💾 Downloads")

    # Wide cleaned Excel
    wide_bytes = to_excel_bytes(df)
    wide_name = "PM_Cleaned_Wide.xlsx" if sheet_name is None else f"PM_Cleaned_Wide_{sheet_name}.xlsx"
    st.download_button(
        "⬇️ Download Cleaned Wide File (Excel)",
        data=wide_bytes,
        file_name=wide_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Long-format CSV
    if make_long and df_long is not None:
        long_csv = df_long.to_csv(index=False).encode("utf-8")
        long_name = "PM_LongFormat_Tableau.csv" if sheet_name is None else f"PM_LongFormat_Tableau_{sheet_name}.csv"
        st.download_button(
            "⬇️ Download Tableau-ready Long Format (CSV)",
            data=long_csv,
            file_name=long_name,
            mime="text/csv"
        )

    # Logs
    st.write("### 📝 Processing Log")
    if log_lines:
        st.write("\n".join(f"- {ln}" for ln in log_lines))
    else:
        st.write("No transformations applied.")

else:
    st.info("Upload a MoDA/Excel/CSV file to begin cleaning and reshaping.")

st.markdown("""---
<div style="font-size:0.9rem; color:#555;">
<strong>WFP Jijiga Area Office – M&E Unit (RAM)</strong><br>
Process Monitoring Data Cleaning & Tableau Preparation Utility – Streamlit App v2
</div>
""", unsafe_allow_html=True)
