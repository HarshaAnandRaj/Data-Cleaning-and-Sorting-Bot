import io
import json
from pathlib import Path
import zipfile
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import re

app = FastAPI(title="CSV & Excel Cleaning Bot – V0.4")

# Allow CORS so frontend can talk to backend (even if opened as file://)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory sessions: session_id → DataFrame
SESSIONS = {}

def normalize_col_name(name: str) -> str:
    """Normalize column names for more forgiving matching"""
    return re.sub(r'[\s_-]+', '_', name.strip().lower())


class CSVCleaner:
    def __init__(self, config_path: str = None, config_dict: dict = None):
        if config_dict is not None:
            self.cfg = config_dict
        elif config_path:
            with open(config_path, "r") as f:
                self.cfg = yaml.safe_load(f)
        else:
            self.cfg = {}   # ← explicit empty config

    def apply_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        dtypes = self.cfg.get("dtypes", {})
        for col, dtype in dtypes.items():
            if col not in df.columns:
                continue
            try:
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
            except Exception:
                pass  # silent fail — better than crash
        return df

    def handle_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        mcfg = self.cfg.get("missing", {})

        # Drop rows missing critical columns
        drop_rows_cols = mcfg.get("drop_rows_if_missing_any_of", [])
        if drop_rows_cols:
            existing = [c for c in drop_rows_cols if c in df.columns]
            if existing:
                df = df.dropna(subset=existing)

        # Fill missing values – type-aware
        fill_cfg = mcfg.get("fill", {})
        for col, method in fill_cfg.items():
            if col not in df.columns:
                continue

            # Skip numeric-only methods on non-numeric columns
            if method in ["median", "mean"] and not pd.api.types.is_numeric_dtype(df[col]):
                # Fallback to mode for categorical / object
                if not df[col].mode().empty:
                    df[col] = df[col].fillna(df[col].mode().iloc[0])
                else:
                    df[col] = df[col].fillna("unknown")
                continue

            try:
                if method == "median" and pd.api.types.is_numeric_dtype(df[col]):
                    val = df[col].median()
                    df[col] = df[col].fillna(0 if pd.isna(val) else val)
                elif method == "mean" and pd.api.types.is_numeric_dtype(df[col]):
                    val = df[col].mean()
                    df[col] = df[col].fillna(0 if pd.isna(val) else val)
                elif method == "mode":
                    if not df[col].mode().empty:
                        df[col] = df[col].fillna(df[col].mode().iloc[0])
                    else:
                        df[col] = df[col].fillna("unknown")
                elif method in ["0", 0, "zero"]:
                    df[col] = df[col].fillna(0)
                else:
                    # constant value
                    df[col] = df[col].fillna(method)
            except Exception:
                # Ultimate safe fallback
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(0)
                else:
                    df[col] = df[col].fillna("unknown")

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
        if pattern and cols:
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
            vals = df[col]
            mean = vals.mean()
            std = vals.std()
            if std == 0:
                continue
            z = (vals - mean) / std
            df = df[z.abs() <= threshold]
        return df

    def sort(self, df: pd.DataFrame) -> pd.DataFrame:
        scfg = self.cfg.get("sort", {})
        by = scfg.get("by")
        ascending = scfg.get("ascending", True)
        if by:
            df = df.sort_values(by=by, ascending=ascending)
        return df

    def is_dirty(self, df: pd.DataFrame) -> tuple[float, str, list]:
        messages = []
        missing_count = df.isna().sum().sum()
        dup_count = df.duplicated().sum()
        total_cells = df.shape[0] * df.shape[1]
        dirty_score = round((missing_count + dup_count) / total_cells * 100, 2) if total_cells else 0.0

        if missing_count > 0:
            messages.append(f"Missing values: {missing_count:,}")
        if dup_count > 0:
            messages.append(f"Duplicate rows: {dup_count:,}")

        if dirty_score == 0:
            severity = "INFO"
        elif dirty_score < 5:
            severity = "LOW"
        elif dirty_score < 20:
            severity = "MEDIUM"
        else:
            severity = "HIGH"

        return dirty_score, severity, messages

    def run(self, df: pd.DataFrame):
        dirty_before, _, _ = self.is_dirty(df)
        df_clean = self.apply_dtypes(df)
        df_clean = self.handle_missing(df_clean)
        df_clean = self.text_clean(df_clean)
        df_clean = self.drop_duplicates(df_clean)
        df_clean = self.handle_outliers(df_clean)
        df_clean = self.sort(df_clean)
        dirty_after, severity, messages = self.is_dirty(df_clean)
        return df_clean, dirty_before, dirty_after, severity, messages


# ── Upload endpoint ─────────────────────────────────────────────────────────
@app.post("/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    filename_lower = file.filename.lower()
    if not filename_lower.endswith((".csv", ".xls", ".xlsx")):
        raise HTTPException(400, "Only CSV/Excel supported")

    contents = await file.read()
    try:
        if filename_lower.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(400, f"Could not read file: {str(e)}")

    session_id = f"sess_{len(SESSIONS)+1}"
    SESSIONS[session_id] = df

    # Use empty config for initial dirty check
    cleaner = CSVCleaner(config_dict={})
    dirty_score, severity, messages = cleaner.is_dirty(df)

    config = {
        "dtypes": {col: "float" if pd.api.types.is_numeric_dtype(df[col]) else "category" for col in df.columns},
        "missing": {
            "drop_rows_if_missing_any_of": [],
            "fill": {}
        },
        "text_cleaning": {"lower_columns": [], "strip_spaces_columns": []},
        "duplicates": {"subset": None, "keep": "first"},
        "outliers": {
            "zscore": {
                "columns": [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])],
                "threshold": 3.0
            }
        },
        "sort": {"by": [], "ascending": True},
        "split": {"enabled": False}
    }

    return {
        "session_id": session_id,
        "config": config,
        "dirty_score": dirty_score,
        "severity": severity,
        "messages": messages,
        "filename": file.filename.rsplit(".", 1)[0]
    }


@app.post("/run_cleaning")
async def run_cleaning(payload: dict):
    session_id = payload.get("session_id")
    config = payload.get("config", {})

    if session_id not in SESSIONS:
        raise HTTPException(400, "Unknown session")

    df = SESSIONS[session_id]
    cleaner = CSVCleaner(config_dict=config)
    df_clean, dirty_before, dirty_after, severity, messages = cleaner.run(df)

    zip_buffer = io.BytesIO()
    uploaded_name = payload.get("filename") or f"file_{session_id}"
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{uploaded_name}_cleaned.csv", df_clean.to_csv(index=False))
        log_content = (
            f"Dirty score BEFORE: {dirty_before}%\n"
            f"Dirty score AFTER : {dirty_after}%\n"
            f"Severity: {severity}\n\n"
            "Messages:\n" + "\n".join(messages)
        )
        zf.writestr(f"{uploaded_name}_issuelog.txt", log_content)

    zip_buffer.seek(0)
    headers = {"Content-Disposition": f"attachment; filename={uploaded_name}_Cleaned.zip"}

    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)