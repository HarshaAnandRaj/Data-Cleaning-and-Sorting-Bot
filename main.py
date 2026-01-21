import io
from pathlib import Path

import pandas as pd
import yaml
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from sklearn.model_selection import train_test_split

app = FastAPI(title="CSV/Excel Cleaning Bot")

class CSVCleaner:
    def __init__(self, config_path: str):
        with open(config_path, "r") as f:
            self.cfg = yaml.safe_load(f)

    def load(self) -> pd.DataFrame:
        input_path = self.cfg["input_path"]
        if input_path.endswith(".csv"):
            df = pd.read_csv(input_path)
        elif input_path.endswith((".xls", ".xlsx")):
            df = pd.read_excel(input_path)
        else:
            raise ValueError("Unsupported input file type")
        return df

    def apply_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        dtypes = self.cfg.get("dtypes", {})
        for col, dtype in dtypes.items():
            if col not in df.columns:
                continue
            if dtype == "datetime":
                df[col] = pd.to_datetime(df[col], errors="coerce")
            elif dtype == "int":
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            elif dtype == "float":
                df[col] = pd.to_numeric(df[col], errors="coerce")
            elif dtype == "category":
                df[col] = df[col].astype("category")
            else:
                df[col] = df[col].astype(dtype)
        return df

    def handle_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        mcfg = self.cfg.get("missing", {})
        drop_cols = mcfg.get("drop_rows_if_missing_any_of", [])
        if drop_cols:
            df = df.dropna(subset=drop_cols)
        fill_cfg = mcfg.get("fill", {})
        for col, method in fill_cfg.items():
            if col not in df.columns:
                continue
            if method == "median":
                df[col] = df[col].fillna(df[col].median())
            elif method == "mean":
                df[col] = df[col].fillna(df[col].mean())
            elif method == "mode":
                df[col] = df[col].fillna(df[col].mode().iloc[0])
            else:
                df[col] = df[col].fillna(method)
        return df

    def text_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        tcfg = self.cfg.get("text_cleaning", {})
        for col in tcfg.get("lower_columns", []):
            if col in df.columns:
                df[col] = df[col].astype(str).str.lower()
        for col in tcfg.get("strip_spaces_columns", []):
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        rcfg = tcfg.get("remove_chars", {})
        cols = rcfg.get("columns", [])
        pattern = rcfg.get("pattern")
        if pattern:
            for col in cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(pattern, "", regex=True)
        return df

    def drop_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        dcfg = self.cfg.get("duplicates", {})
        subset = dcfg.get("subset")
        keep = dcfg.get("keep", "first")
        if subset:
            df = df.drop_duplicates(subset=subset, keep=keep)
        else:
            df = df.drop_duplicates(keep=keep)
        return df

    def handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        ocfg = self.cfg.get("outliers", {})
        zcfg = ocfg.get("zscore", {})
        cols = zcfg.get("columns", [])
        threshold = zcfg.get("threshold", 3.0)
        for col in cols:
            if col not in df.columns:
                continue
            col_vals = df[col]
            mean = col_vals.mean()
            std = col_vals.std()
            if std == 0:
                continue
            z = (col_vals - mean) / std
            df = df[z.abs() <= threshold]
        return df

    def sort(self, df: pd.DataFrame) -> pd.DataFrame:
        scfg = self.cfg.get("sort", {})
        by = scfg.get("by")
        ascending = scfg.get("ascending", True)
        if by:
            df = df.sort_values(by=by, ascending=ascending)
        return df

    def split(self, df: pd.DataFrame):
        scfg = self.cfg.get("split", {})
        if not scfg.get("enabled", False):
            return
        target = scfg.get("target_column")
        stratify = df[target] if scfg.get("stratify", False) and target in df.columns else None
        train_size = scfg.get("train_size", 0.7)
        val_size = scfg.get("val_size", 0.15)
        test_size = scfg.get("test_size", 0.15)
        temp_size = val_size + test_size
        df_train, df_temp = train_test_split(df, test_size=temp_size, stratify=stratify, random_state=42)
        relative_val_size = val_size / temp_size
        stratify_temp = df_temp[target] if stratify is not None else None
        df_val, df_test = train_test_split(df_temp, test_size=(1 - relative_val_size), stratify=stratify_temp, random_state=42)
        out_dir = Path(scfg.get("output_dir", "splits"))
        out_dir.mkdir(parents=True, exist_ok=True)
        df_train.to_csv(out_dir / "train.csv", index=False)
        df_val.to_csv(out_dir / "val.csv", index=False)
        df_test.to_csv(out_dir / "test.csv", index=False)

    def run(self):
        df = self.load()
        df = self.apply_dtypes(df)
        df = self.handle_missing(df)
        df = self.text_clean(df)
        df = self.drop_duplicates(df)
        df = self.handle_outliers(df)
        df = self.sort(df)
        Path(self.cfg["output_path"]).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.cfg["output_path"], index=False)
        self.split(df)


# ---------- Helper for generating basic config ----------
def suggest_basic_config(df: pd.DataFrame) -> dict:
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    object_cols = df.select_dtypes(include=["object"]).columns.tolist()
    cfg: dict = {
        "input_path": "__in_memory__",
        "output_path": "__in_memory__",
        "dtypes": {},
        "missing": {"drop_rows_if_missing_any_of": [], "fill": {}},
        "text_cleaning": {"lower_columns": object_cols, "strip_spaces_columns": object_cols, "remove_chars": {"columns": [], "pattern": None}},
        "duplicates": {"subset": None, "keep": "first"},
        "outliers": {"zscore": {"columns": numeric_cols, "threshold": 3.0}},
        "sort": {"by": [], "ascending": True},
        "split": {"enabled": False},
    }
    for col in numeric_cols:
        cfg["dtypes"][col] = "float"
        cfg["missing"]["fill"][col] = "mean"
    for col in object_cols:
        cfg["dtypes"][col] = "category"
    return cfg


# ---------- API endpoints ----------
@app.get("/", response_class=HTMLResponse)
async def root():
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>CSV/Excel Cleaning Bot</title></head>
    <body>
    <h2>Upload CSV or Excel for Cleaning</h2>
    <form id="upload-form">
    <input type="file" id="file-input" accept=".csv,.xls,.xlsx"/>
    <button type="submit">Upload & Suggest Config</button>
    </form>
    <div id="chat"></div>
    <textarea id="config-area"></textarea>
    <button id="run-btn">Run Cleaning</button>
    <script>
    // ... (same JS as before, no need to change for upload types)
    </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


SESSIONS: dict[str, pd.DataFrame] = {}


@app.post("/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".csv", ".xls", ".xlsx")):
        return JSONResponse(status_code=400, content={"detail": "Only CSV or Excel files are supported."})
    contents = await file.read()
    try:
        if file.filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": f"Could not read file: {e}"})
    session_id = f"sess_{len(SESSIONS) + 1}"
    SESSIONS[session_id] = df
    cfg = suggest_basic_config(df)
    return {"session_id": session_id, "config": cfg}


@app.post("/run_cleaning")
async def run_cleaning(payload: dict):
    session_id = payload.get("session_id")
    config = payload.get("config", {})
    if session_id not in SESSIONS:
        return JSONResponse(status_code=400, content={"detail": "Unknown session_id."})
    df = SESSIONS[session_id]
    cleaner_cfg = config.copy()
    cleaner_cfg["input_path"] = "__in_memory__"
    cleaner_cfg["output_path"] = "__in_memory__"
    cleaner = CSVCleaner.__new__(CSVCleaner)
    cleaner.cfg = cleaner_cfg
    df_clean = df.copy()
    df_clean = cleaner.apply_dtypes(df_clean)
    df_clean = cleaner.handle_missing(df_clean)
    df_clean = cleaner.text_clean(df_clean)
    df_clean = cleaner.drop_duplicates(df_clean)
    df_clean = cleaner.handle_outliers(df_clean)
    df_clean = cleaner.sort(df_clean)
    buf = io.StringIO()
    df_clean.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(buf, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=cleaned.csv"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
