# CSV Cleaning Bot 🚀

## V0.5 – Automatic Multi-File Data Cleaner

A fast, local-first web tool that lets you upload one or more CSV or Excel files, automatically clean them with smart rules, and download a ZIP containing:

- cleaned file(s) with proper names
- a clear CLEANING_REPORT.txt showing before/after dirty scores, every change made, and remaining issues (if any)

All processing happens in your browser memory + local backend — zero data leaves your machine.

## ✨ Key Features in V0.5

- Multi-file upload – drag & drop or select several CSVs/Excels at once 🗂️
- Fully automatic cleaning (no config needed in v0.5)
- Fills missing values (median for numbers, mode for categories)
- Normalizes text (strip whitespace + lowercase)
- Removes exact duplicate rows
- Removes statistical outliers (z-score > 3 on numeric columns)
- Normalized dirty score (0–100%) shown for each file
- Counts both real NaN and empty/whitespace strings
- Severity badges: CLEAN 🟢 / GOOD 🟢 / WARNING 🟡 / CRITICAL 🔴
- Detailed per-file report in the ZIP
- Dirty BEFORE vs AFTER
- Every single change listed
- Remaining issues (or “(none)” ✅)
- Modern glassy UI with dark/light mode toggle 🌙☀️
- Safe & private – no cloud, no tracking, no data upload

## 📁 Folder Structure

```bash
.
├── backend
│   ├── main.py             # FastAPI app + cleaning logic + ZIP streaming
│   └── requirements.txt    # Python dependencies
├── frontend
│   ├── index.html          # Main UI (upload, preview, config, FAQ)
│   ├── app.js              # API calls, state, theme logic
│   └── style.css           # Glassmorphism + extra styling
└── README.md
```

## Quick Start – 60 seconds ⏱️

1. Backend

```bash
Bashcd backend
python -m venv venv
```

# Windows

```bash
venv\Scripts\activate
```

# macOS / Linux

```bash
source venv/bin/activate
pip install fastapi uvicorn pandas numpy python-multipart
uvicorn main:app --reload --host 0.0.0.0 --port 8000
Backend will be running at http://localhost:8000
```

2. Frontend

```bash
Bashcd frontend
python -m http.server 5173
```
**Open →** http://localhost:5173

3. Use it

- Drag & drop or select CSV/Excel file(s)
- Watch per-file dirty scores & severity appear
- Click Run Cleaning & Download ZIP 🗜️
- Get cleaned files + full report inside the ZIP

## Example output in CLEANING_REPORT.txt

```bash
textMulti-File Cleaning Report
============================================================

File: sales_data
  Dirty BEFORE: 12.45%
  Dirty AFTER : 0.00%
  Severity: CLEAN 🟢
  Changes applied:
    • Filled 'price' missing with median (49.99)
    • Filled 'category' missing with mode (Electronics)
    • Cleaned text in 'product_name' (strip + lowercase)
    • Removed 3 duplicate rows
    • Removed 7 outlier rows (|z| > 3)
  Remaining issues:
    • (none)
------------------------------------------------------------
```

## Planned for V0.6 (coming soon)

- Simple chat-style rule editor (“fill price with 0”, “drop column notes”)
- Optional JSON config view & edit
- First 10 rows preview table after upload
- File size / row count summary
- Progress bar for large files
- Export cleaned data directly to clipboard / new tab

## Tech Stack

**Backend:** FastAPI + Pandas + Uvicorn

**Frontend:** Tailwind CSS + vanilla JavaScript + Font Awesome

Zero external services – fully offline/local


Enjoy cleaning! 🧼✨
Made with ❤️ in 2025
Feel free to open issues / PRs — contributions welcome!