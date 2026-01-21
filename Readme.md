
# 🧹 CSV Cleaning & Sorting Bot (v0.2 Alpha)

An interactive data cleaning tool built with **FastAPI** and **Pandas**.

Users can upload CSV files, get automated cleaning suggestions, tweak rules via a simple chat or JSON config, and download a cleaned CSV. The app also detects whether the dataset looks **“dirty”** (missing values / duplicates) and warns the user before running the pipeline.

This is a foundational personal project focused on handling messy real‑world data — designed to be extended into future ML, analytics, or automation pipelines.

---

## ✨ Features (v0.2 Alpha)

- **Web UI** (single HTML page served by FastAPI)
- **File upload form**: CSV (.csv) files
- **Chat area** to apply simple natural‑language cleaning rules
- **JSON config editor** (auto‑filled, fully editable)
- **Run button** to download `cleaned.csv`
- **In‑memory sessions**
  - Each upload gets a `session_id`
  - Data never hits disk (in this version)

### 🧩 Dirty Dataset Detection

- Warns if:
  - Any column has missing values
  - There are duplicate rows
- Dirty messages are:
  - Shown in the UI
  - Returned as an `X-Dataset-Dirty` header on download

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

### 💬 Simple Chat Interface (rule‑based)

- Understands commands like:
  - `drop rows with missing label`
  - `sort by created_at descending`
- Updates the **JSON config** automatically

---

## 🛠 Tech Stack

- **FastAPI** – Backend & API
- **Pandas** – Data processing
- **Scikit‑learn** – Dataset splitting
- **PyYAML** – Config‑driven cleaning rules
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

### 🔹 v0.2 Alpha

* Added **Web UI** with:

  * File upload
  * Chat interface
  * Live JSON config editor
* Switched to **in‑memory session storage**
* Introduced **dirty dataset detection**

  * Detect missing values & duplicates
  * Exposed in UI + headers
* Added simple chat endpoint (`/chat`)

  * Handles commands like “drop rows…”, “sort by…”
* Refactored `CSVCleaner`

  * Accepts either config path or dict
  * Returns `(df_clean, dirty, messages)`
* Improved UI messaging & workflow

### 🔸 v0.1 Alpha

* Initial CLI style cleaner:

  * Config‑based CSV loading
  * Data type application
  * Missing value handling
  * Text cleaning & duplicates removal
  * Z‑score outliers
  * Sorting & optional splitting
* No web UI, chat, etc.

---

## 🔮 Future Ideas (v0.3+)

* Export a **readable `.txt` report** summarizing changes
* Support **Excel uploads** (`.xlsx`)
* Improved natural‑language understanding in chat
* Automatic outlier detection



