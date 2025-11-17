# WFP Somali Region – Process Monitoring Cleaner & Tableau Prep (Streamlit v2)

This Streamlit app is designed for **WFP Jijiga Area Office II – M&E / RAM Unit** to:
- Upload raw **MoDA / Excel / CSV** process monitoring exports (Relief, TSFP, Warehouse, Market, etc.).
- Remove Kobo/system fields (e.g. `_id`, `_uuid`, `_submission_time`, `starttime`, `endtime`).
- Standardize key metadata fields:
  - `region`, `sub_office`, `zone`, `woreda`, `kebele`, `village`
  - `fdp_name`, `tsfp_center`, `market_name`
  - `partner_name`, `visit_date`, `monitoring_year`, `monitoring_month`, `enumerator`
- Generate a **cleaned wide-format file** (for QA and archival).
- Generate a **Tableau-ready long-format dataset** with:
  - `indicator_name`
  - `indicator_value`
  - All metadata columns preserved.

## How to run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL shown in your terminal (usually http://localhost:8501).

## Usage notes

1. Upload a MoDA/Excel/CSV file.
2. If Excel, choose the sheet you want to process.
3. Keep the default options:
   - ✅ Drop Kobo/system fields  
   - ✅ Standardize key metadata fields  
   - ✅ Generate long-format dataset
4. Preview the **raw**, **cleaned**, and **long-format** data.
5. Download:
   - Cleaned wide Excel file.
   - Long-format CSV for Tableau / Power BI.
