# 🧹 CSV / Excel Cleaning & Sorting Bot (v0.4)

An interactive, **privacy-first** data cleaning tool with a separate **FastAPI** backend and a modern static frontend.

Upload CSV or Excel files → get automatic cleaning suggestions → review/edit JSON config → download a cleaned ZIP (cleaned dataset + issues log).

The app computes a **normalized dirty score** (0–100) with severity levels to highlight data quality issues.

This version focuses on refined UI/UX, clearer backend API, and a fully **config-driven** cleaning pipeline — ready for future LLM integration.

## ✨ Features (v0.4)

- **Modern web UI** (standalone frontend)
  - Tailwind-styled, glassmorphic design
  - Light / dark theme toggle (persisted in local storage)
  - Sidebar navigation + FAQ + About sections

- **FastAPI backend API**
  - `POST /upload_csv` – upload & analyze CSV / Excel
  - `POST /run_cleaning` – execute pipeline & stream ZIP

- **File upload support**
  - CSV (`.csv`)
  - Excel (`.xls`, `.xlsx`)

- **Automatic suggestions**
  - Suggested dtypes based on column content
  - Suggested numeric columns for outlier detection
  - Empty-but-structured sections for missing values, text cleaning, sorting

- **JSON config editor**
  - Auto-filled after upload
  - Fully editable before running cleaning

- **Data preview**
  - First 10 rows rendered as HTML table

- **Cleaning & download**
  - One-click “Run Cleaning & Download ZIP”
  - ZIP contains:
    - `[filename]_cleaned.csv`
    - `[filename]_issuelog.txt`

- **In-memory sessions**
  - Each upload gets a `session_id`
  - Config + cleaning operate on session’s DataFrame

- **UI reset**
  - Automatically resets after upload or successful cleaning

## 🧩 Dirty Dataset Detection & Normalized Score

- Detects:
  - Missing values
  - Duplicate rows

- **Normalized dirty score** (0–100):
  - Based on missing cells + duplicate rows
  - Normalized against total cells

- Dirty messages shown in UI via warning card
- Also written into `[filename]_issuelog.txt`

- **Severity levels**:
  - INFO
  - LOW
  - MEDIUM
  - HIGH

## ⚙️ Config-Driven Cleaning Pipeline

The backend `CSVCleaner` runs this configurable sequence:

1. **Data types** (`dtypes`)  
   int, float, category, str, datetime, ...

2. **Missing values**
   - `drop_rows_if_missing_any_of`: critical columns
   - Fill with: mean, median, mode, constant ("0", "unknown", custom)
   - Type-aware handling + safe fallbacks

3. **Text cleaning**
   - `lower_columns`
   - `strip_spaces_columns`
   - Optional `remove_chars` (regex pattern)

4. **Duplicate removal**
   - `subset` + `keep` strategy

5. **Outlier handling** (Z-score)
   - Configurable columns + threshold

6. **Sorting**
   - `by` + `ascending`

7. **Optional split** (reserved for future use)

**Pipeline order**:

## apply_dtypes → handle_missing → text_clean → drop_duplicates → handle_outliers → sort


> 💬 **Note**: The experimental chat interface has been removed in v0.4.  
> All control is now explicit via the JSON editor (with room to re-add LLM chat later).

## 🛠 Tech Stack

- **Backend**: FastAPI, Pandas, Scikit-learn, PyYAML, Uvicorn
- **Frontend**: Plain HTML + Tailwind CSS + vanilla JavaScript
- No heavy frontend frameworks

## 📁 Folder Structure

.
├── backend
│   ├── main.py             # FastAPI app + cleaning logic + ZIP streaming
│   ├── config.yaml         # Example config (CLI/offline use)
│   └── requirements.txt    # Python dependencies
├── frontend
│   ├── index.html          # Main UI (upload, preview, config, FAQ)
│   ├── app.js              # API calls, state, theme logic
│   └── style.css           # Glassmorphism + extra styling
└── README.md


## 🚀 Setup & Run Locally

1. **Clone repository**

```bash
git clone https://github.com/HarshaAnandRaj/Data-Cleaning-and-Sorting-Bot.git
cd Data-Cleaning-and-Sorting-Bot
```

2. **Activate:**

```bash
WindowsBashvenv\Scripts\activate
macOS / LinuxBashsource venv/bin/activate
```

3. **Install dependencies**

```bash
Bashpip install -r requirements.txt
```
4. **Run backend**

```bash
Bashuvicorn main:app --reload --host 0.0.0.0 --port 8000
Backend → http://localhost:8000
```

5. **Open frontend**

```bash
Bashcd ../frontend
python -m http.server 5173
Then open: http://localhost:5173
```

## 📝 How to Use

Upload file → Click "Choose file" → "Analyze File"
Review dirty score & warning card (if any)
Check data preview (first 10 rows)
Edit JSON config (or click "Accept All Suggestions")
Run cleaning → "Run Cleaning & Download ZIP"
Browser downloads [original]_Cleaned.zip

🗂 Changelog
# 🔹 v0.4 (current)

Separated backend & frontend folders
Modern glassmorphism UI
Improved missing value handling (type-aware)
Better dirty scoring & severity
ZIP always includes before/after scores in log
Removed experimental chat UI

# 🔸 v0.3 Dev

Multi-file support + unique naming
Excel support
Normalized dirty score
Issues log in ZIP
Basic chat-style interface (experimental)

# 🔹 v0.2 Alpha

Initial web UI
File upload + JSON editor
In-memory sessions
Dirty detection

# 🔹 v0.1 Alpha

CLI-style cleaner
Config-based pipeline
Basic dtype, missing, text, duplicates, outliers, sorting