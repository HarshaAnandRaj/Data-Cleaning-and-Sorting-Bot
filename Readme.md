CSV Cleaning & Sorting Bot (v0.2 Alpha)
An interactive data cleaning tool built with FastAPI and Pandas.

Users can upload CSV files, get automated cleaning suggestions, tweak rules via a simple chat or JSON config, and download a cleaned CSV. The app also detects whether the dataset looks “dirty” (missing values / duplicates) and warns the user before running the pipeline.

This is a foundational personal project focused on handling messy real‑world data — designed to be extended into future ML, analytics, or automation pipelines.

Features (v0.2 Alpha)
Web UI (single HTML page served by FastAPI)
File upload form (CSV)
Chat area to apply simple natural‑language cleaning rules
JSON config editor (auto‑filled, fully editable)
Run button to download cleaned.csv
In‑memory sessions
Each upload gets a session_id
Data never hits disk (in this version)
Dirty dataset detection
Warns if:
Any column has missing values
There are duplicate rows
Dirty messages are:
Shown in the UI
Also returned as an X-Dataset-Dirty header on download
Config‑driven pipeline
Data types (dtypes)
Missing values:
Drop rows with missing values in specific columns
Fill with mean / median / mode / constant
Text cleaning:
Lowercasing
Trimming spaces
Removing custom character patterns via regex
Duplicates removal
Outlier handling via Z-score
Sorting by one or more columns
Optional train / validation / test split (config based)
Simple chat interface (rule‑based)
Understands commands like:
drop rows with missing label
sort by created_at descending
Updates the JSON config to match your message
Tech Stack
FastAPI – Backend & API
Pandas – Data processing
Scikit-learn – Dataset splitting
PyYAML – Config-driven cleaning rules
Uvicorn – ASGI server
Folder Structure
.
├── main.py          # FastAPI app + cleaning pipeline + UI
├── config.yaml      # Example config (for CLI / future use)
├── requirements.txt # Python dependencies
└── README.md
Setup & Run Locally
1. Clone the repository
git clone https://github.com/<your-username>/Data-Cleaning-and-Sorting-Bot.git
cd Data-Cleaning-and-Sorting-Bot
(or your actual repo name/path)

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
For development (with auto‑reload):

python main.py
This starts Uvicorn via the if __name__ == "__main__": block:

if __name__=="__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
5. Open in browser
http://127.0.0.1:8000
How to Use
Upload CSV

Click “Choose file” and select a .csv file.
Click Upload & Suggest Config.
Backend:
Stores the DataFrame in an in‑memory session
Generates a basic config (dtypes, outlier columns, etc.)
Checks if the dataset is “dirty” (missing values / duplicates)
Review the dirty warning

If the dataset looks dirty, a red warning appears:
Missing values columns
Number of duplicate rows
Chat to adjust rules (optional)

Example messages:
drop rows with missing label
sort by created_at descending
The config JSON is updated automatically and shown in the editor.
Review / edit JSON config

The Config textarea shows the current config.
You can manually tweak any field (dtypes, missing strategy, sort columns, etc.).
Run cleaning

Click Run Cleaning.
The app:
Runs the pipeline (apply_dtypes → handle_missing → text_clean → drop_duplicates → handle_outliers → sort → split (optional))
Streams back cleaned.csv as a download.
If the dataset is still dirty after cleaning, messages are also included in response headers.
Changelog
v0.2 Alpha
Added web UI with:
File upload form
Chat area
Live JSON config editor
Switched to in‑memory session storage (SESSIONS) for uploaded DataFrames.
Introduced dirty dataset detection:
Detect missing values and duplicate rows
Expose status in UI and response headers
Added simple chat endpoint (/chat) that:
Handles commands like “drop rows with missing X”, “sort by Y descending”
Mutates the current config accordingly
Refactored CSVCleaner to:
Accept either a config path or a config dict
Return (df_clean, dirty, messages) from run()
Improved UI messaging and workflow.
v0.1 Alpha
Initial CLI‑style cleaner with:
Config‑based CSV loading
Data type application
Missing values handling
Text cleaning
Duplicate removal
Z-score outlier handling
Sorting and optional train/val/test splitting
No web UI, chat, or in‑memory sessions.