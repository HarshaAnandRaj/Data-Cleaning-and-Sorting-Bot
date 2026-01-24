from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io
import zipfile
import pandas as pd
import re
from typing import List, Dict, Any, Tuple
import numpy as np

app = FastAPI(title="CSV & Excel Cleaning Bot – V0.4")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS: Dict[str, Dict[str, Any]] = {}


def to_python(obj: Any) -> Any:
    """Convert NumPy/Pandas types to native Python for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (list, tuple)):
        return [to_python(item) for item in obj]
    if isinstance(obj, dict):
        return {k: to_python(v) for k, v in obj.items()}
    if isinstance(obj, pd.Series):
        return to_python(obj.to_dict())
    if isinstance(obj, pd.DataFrame):
        return to_python(obj.to_dict(orient="records"))
    return obj


def compute_dirty_stats(df: pd.DataFrame) -> Tuple[float, str, int, int]:
    """
    Compute dirty score and severity for a DataFrame.
    Counts NaN + empty/whitespace strings as missing.

    Returns:
        dirty_score: float (0–100)
        severity: CLEAN / GOOD / WARNING / CRITICAL
        missing: count of missing/blank cells
        dups: count of duplicate rows
    """
    # Missing = NaN + empty / whitespace strings
    missing = int(
        df.isna().sum().sum()
        + df.apply(lambda x: x.astype(str).str.strip() == "").sum().sum()
    )
    dups = int(df.duplicated().sum())
    total = int(df.shape[0] * df.shape[1])

    dirty_score = round((missing + dups) / total * 100, 2) if total else 0.0

    if dirty_score == 0:
        severity = "CLEAN"
    elif dirty_score < 5:
        severity = "GOOD"
    elif dirty_score < 15:
        severity = "WARNING"
    else:
        severity = "CRITICAL"

    return dirty_score, severity, missing, dups


class RunCleaningPayload(BaseModel):
    session_id: str


class CSVCleaner:
    """Config-free cleaning pipeline with basic imputations and outlier removal."""

    def run(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, float, float, str, List[str], List[str]]:
        """
        Run the cleaning pipeline on a copy of df.

        Returns:
            df_clean
            dirty_before
            dirty_after
            severity_after
            remaining_issue_messages
            change_descriptions
        """
        changes: List[str] = []
        messages: List[str] = []

        df_orig = df.copy()

        # Treat empty strings / whitespace-only as missing
        df = df.replace(r"^\s*$", pd.NA, regex=True)

        # Fill missing values (type-aware, with safe fallback)
        for col in df.columns:
            if not df[col].isna().any():
                continue

            try:
                if pd.api.types.is_numeric_dtype(df[col]):
                    val = df[col].median()
                    val = 0 if pd.isna(val) else val
                    df[col] = df[col].fillna(val)
                    changes.append(f"Filled '{col}' missing with median ({val})")
                else:
                    mode_series = df[col].mode()
                    if not mode_series.empty:
                        val = mode_series.iloc[0]
                        df[col] = df[col].fillna(val)
                        changes.append(f"Filled '{col}' missing with mode ({val})")
                    else:
                        df[col] = df[col].fillna("unknown")
                        changes.append(f"Filled '{col}' missing with 'unknown'")
            except Exception as exc:
                fallback = 0 if pd.api.types.is_numeric_dtype(df[col]) else "unknown"
                df[col] = df[col].fillna(fallback)
                changes.append(
                    f"Fallback fill for '{col}' with {fallback!r} "
                    f"(due to {type(exc).__name__})"
                )

        # Clean text columns (strip + lowercase)
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].astype(str).str.strip().str.lower()
            changes.append(f"Cleaned text in '{col}' (strip + lowercase)")

        # Remove duplicates
        before = len(df)
        df = df.drop_duplicates()
        removed = before - len(df)
        if removed > 0:
            changes.append(f"Removed {removed} duplicate rows")

        # Remove outliers (after imputation) using combined Z-score mask
        numeric_cols = df.select_dtypes(include=["number"]).columns
        removed_outliers = 0
        if len(numeric_cols) > 0:
            mask = pd.Series(True, index=df.index)
            for col in numeric_cols:
                mean = df[col].mean()
                std = df[col].std()
                if std == 0 or pd.isna(std):
                    continue
                z = (df[col] - mean) / std
                mask &= z.abs() <= 3

            before_len = len(df)
            df = df[mask]
            removed_outliers = before_len - len(df)

        if removed_outliers > 0:
            changes.append(f"Removed {removed_outliers} outlier rows (|z| > 3)")

        # Dirty score before & after cleaning
        dirty_before, _, missing_before, dups_before = compute_dirty_stats(df_orig)
        dirty_after, severity_after, missing_after, dups_after = compute_dirty_stats(df)

        if missing_after > 0:
            messages.append(f"Missing values: {missing_after:,} cells (including blanks)")
        if dups_after > 0:
            messages.append(f"Duplicate rows: {dups_after:,}")

        return df, dirty_before, dirty_after, severity_after, messages, changes


@app.post("/upload_csv")
async def upload_csv(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """
    Upload one or more CSV/Excel files, compute preview dirty stats,
    and register a new in-memory session.
    """
    if not files:
        raise HTTPException(400, "No files uploaded")

    session_id = f"sess_{len(SESSIONS)+1}"
    originals = []
    filenames = []
    file_stats = []

    for file in files:
        if not file.filename.lower().endswith((".csv", ".xls", ".xlsx")):
            continue

        contents = await file.read()
        try:
            if file.filename.lower().endswith(".csv"):
                df = pd.read_csv(io.BytesIO(contents))
            else:
                df = pd.read_excel(io.BytesIO(contents))
        except Exception:
            continue

        filename = file.filename.rsplit(".", 1)[0]
        originals.append(df)
        filenames.append(filename)

        dirty_score, severity, missing, dups = compute_dirty_stats(df)

        file_stats.append(
            {
                "filename": filename,
                "dirty_score": dirty_score,
                "severity": severity,
                "missing_count": missing,
                "duplicate_rows": dups,
            }
        )

    if not originals:
        raise HTTPException(400, "No valid files processed")

    SESSIONS[session_id] = {
        "originals": originals,
        "filenames": filenames,
        "cleaned": [],
        "logs": []
    }

    return to_python({
        "session_id": session_id,
        "file_count": len(originals),
        "filenames": filenames,
        "file_stats": file_stats
    })


@app.post("/run_cleaning")
async def run_cleaning(payload: RunCleaningPayload) -> StreamingResponse:
    """
    Run the cleaning pipeline for the given session_id and
    return a ZIP with cleaned CSVs + a consolidated report.
    """
    session_id = payload.session_id

    if session_id not in SESSIONS:
        raise HTTPException(400, "Unknown session")

    session = SESSIONS[session_id]
    originals = session["originals"]
    filenames = session["filenames"]
    cleaned_files = []
    all_logs = []

    cleaner = CSVCleaner()

    for idx, df in enumerate(originals):
        df_clean, dirty_before, dirty_after, severity, messages, changes = cleaner.run(df)
        cleaned_files.append(df_clean)

        log = {
            "filename": filenames[idx],
            "dirty_before": dirty_before,
            "dirty_after": dirty_after,
            "severity": severity,
            "changes": changes,
            "remaining_issues": messages
        }
        all_logs.append(log)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, df_clean in enumerate(cleaned_files):
            safe_name = re.sub(r'[^\w\-_. ]', '_', filenames[idx])
            zf.writestr(f"{safe_name}_cleaned.csv", df_clean.to_csv(index=False))

        report = "Multi-File Cleaning Report\n" + "=" * 60 + "\n\n"
        for log in all_logs:
            report += f"File: {log['filename']}\n"
            report += f"  Dirty BEFORE: {log['dirty_before']:.2f}%\n"
            report += f"  Dirty AFTER : {log['dirty_after']:.2f}%\n"
            report += f"  Severity: {log['severity']}\n"

            changes = log.get("changes") or []
            remaining = log.get("remaining_issues") or []

            report += "  Changes applied:\n"
            report += (
                "\n".join(f"    • {c}" for c in changes) + "\n"
                if changes
                else "    • (none)\n"
            )

            report += "  Remaining issues:\n"
            report += (
                "\n".join(f"    • {m}" for m in remaining) + "\n"
                if remaining
                else "    • (none)\n"
            )

            report += "-" * 60 + "\n\n"
        zf.writestr("CLEANING_REPORT.txt", report)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=cleaned_files.zip"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)