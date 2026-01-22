

- Dirty messages are:
- Shown in the UI
- Included in `[filename]_issuelog.txt`
- Severity levels:
- INFO / WARNING / CRITICAL
- User overrides logged in issues log

### ⚙️ Config‑Driven Pipeline

- **Data types (dtypes)**
- **Missing values**
- Drop rows with missing values in specific columns
- Fill with mean / median / mode / constant
- **Text cleaning**
- Lowercasing
- Trimming spaces
- Removing custom characters via regex
- **Duplicate removal**
- **Outlier handling** via Z‑score
- **Sorting** by one or more columns
- **Optional train/validation/test split** (config‑based)

### 💬 Chat Interface (rule‑based)

- Commands like:
- `drop rows with missing label`
- `sort by created_at descending`
- Updates **JSON config** automatically
- **Future v0.4**: LLM-powered intelligent commands

---

## 🛠 Tech Stack

- **FastAPI** – Backend & API
- **Pandas** – Data processing
- **Scikit-learn** – Dataset splitting
- **PyYAML** – Config-driven cleaning rules
- **Uvicorn** – ASGI server

---

## 📁 Folder Structure



```

.
├── main.py          # FastAPI app + pipeline + UI
├── config.yaml      # Example config (CLI / future use)
├── requirements.txt # Python dependencies
└── README.md

````

---

## 🚀 Setup & Run Locally

### 1️⃣ Clone the repository

```bash
git clone https://github.com/HarshaAnandRaj/Data-Cleaning-and-Sorting-Bot.git
cd Data-Cleaning-and-Sorting-Bot
````

### 2️⃣ Create and activate virtual environment

```bash
python -m venv venv
```

Activate:

* **Windows**

  ```bash
  venv\Scripts\activate
  ```

* **macOS / Linux**

  ```bash
  source venv/bin/activate
  ```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Run the app (with auto‑reload)

```bash
python main.py
```

### 5️⃣ Open in browser

👉 [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📝 How to Use

### 📌 Upload CSV

1. Click **Choose file** and select a `.csv` file.
2. Click **Upload & Suggest Config**

   * Backend stores the DataFrame in a session
   * Generates basic config (dtypes, missing, etc.)
   * Checks for dirty dataset

### 📌 Review Dirty Warning

* If missing values or duplicates are found, a red warning appears.

### 💬 Chat to Adjust Rules (Optional)

Example messages:

* `drop rows with missing label`
* `sort by price descending`

(The chat updates config JSON automatically.)

### ✏️ Edit JSON Config

You can manually edit any field:

* dtypes
* missing handling
* sort columns
* etc.

### 🧼 Run Cleaning

* Click **Run Cleaning**
* Pipeline runs:
  `apply_dtypes → handle_missing → text_clean → drop_duplicates → handle_outliers → sort → split (optional)`
* Downloads `cleaned.csv`
* Dirty messages included if still dirty after cleaning

---

## 🗂 Changelog

### 🔹 v0.3 Dev

* **Multi-file support** with unique ZIP & CSV naming
* **Excel upload support**
* **Normalized dirty score** calculation
* **Live dirty score on upload**
* **Severity levels** (INFO / WARNING / CRITICAL)
* **Issues log** inside ZIP (`_issuelog.txt`)
* **User override acknowledgements** logged
* **UI resets** after upload or cleaning
* Improved file naming:
  - `[uploadedfile]_Cleaned.zip`
  - `[uploadedfile]_cleaned.csv`
  - `[uploadedfile]_issuelog.txt`
* Minor UI updates (V0.3 Devnet UI)
* Ready for **V0.4 LLM integration** for intelligent chat commands

### 🔸 v0.2 Alpha

* Added **Web UI**:
  - File upload
  - Chat interface
  - JSON config editor
* Switched to **in-memory session storage**
* Introduced **dirty dataset detection**
* Added `/chat` endpoint
* Refactored `CSVCleaner` with `(df_clean, dirty, messages)` return
* Improved UI workflow & messaging

### 🔹 v0.1 Alpha

* CLI-style cleaner
* Config-based CSV loading
* Data type application
* Missing value handling
* Text cleaning & duplicates removal
* Outlier handling via Z-score
* Sorting & optional splitting
* No web UI, chat, or session management
