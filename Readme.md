# CSV & Excel Cleaning Bot

An interactive data cleaning tool built with **FastAPI** and **Pandas**.

Users can upload **CSV or Excel (`.xlsx`) files**, get automated cleaning suggestions, tweak rules via chat or JSON config, and download a cleaned CSV.

This is a **foundational personal project** focused on handling messy real-world data — designed to be extended into future ML, analytics, or automation pipelines.

---

## Features

- Upload **CSV** or **Excel (`.xlsx`)** files
- Automatic data type detection & cleaning suggestions
- Handle missing values (drop or fill)
- Text cleaning:
  - Lowercasing
  - Trimming spaces
  - Removing special characters
- Drop duplicate rows
- Handle outliers using **Z-score**
- Sort data by one or more columns
- Optional **train / validation / test split** (config-based)
- Simple rule-based chat to adjust cleaning rules
- Download cleaned dataset as **CSV**

---

## Tech Stack

- **FastAPI** – Backend & API
- **Pandas** – Data processing
- **Scikit-learn** – Dataset splitting
- **PyYAML** – Config-driven cleaning rules
- **Uvicorn** – ASGI server

---

## Folder Structure

```text
.
├── main.py          # FastAPI application + cleaning pipeline
├── config.yaml      # Example cleaning rules & settings
├── requirements.txt # Python dependencies
└── README.md
Setup & Run Locally
1. Clone the repository
git clone https://github.com/<your-username>/Data-Cleaning-and-Sorting-Bot.git
cd Data-Cleaning-and-Sorting-Bot
2. Create and activate a virtual environment
python -m venv venv
Activate it:

Windows

venv\Scripts\activate
macOS / Linux

source venv/bin/activate
3. Install dependencies
pip install -r requirements.txt
4. Run the app
uvicorn main:app --reload
5. Open in browser
http://127.0.0.1:8000