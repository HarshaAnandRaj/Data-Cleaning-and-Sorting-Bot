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
import asyncio
import time

app = FastAPI(title="CSV & Excel Cleaning Bot – V0.6")

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
    if isinstance(obj, np.integer): return int(obj)
    if isinstance(obj, np.floating): return float(obj)
    if isinstance(obj, np.bool_): return bool(obj)
    if isinstance(obj, np.ndarray): return obj.tolist()
    if isinstance(obj, (list, tuple)): return [to_python(item) for item in obj]
    if isinstance(obj, dict): return {k: to_python(v) for k, v in obj.items()}
    if isinstance(obj, pd.Series): return to_python(obj.to_dict())
    if isinstance(obj, pd.DataFrame): return to_python(obj.to_dict(orient="records"))
    return obj


def compute_dirty_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute detailed dirty stats – pre & post cleaning."""
    missing = int(
        df.isna().sum().sum()
        + df.apply(lambda x: x.astype(str).str.strip() == "").sum().sum()
    )
    dups = int(df.duplicated().sum())
    total = int(df.shape[0] * df.shape[1])

    dirty_score = round((missing + dups) / total * 100, 2) if total else 0.0

    imputed_ratio = 0.0  # updated post-clean

    severity = "CLEAN" if dirty_score == 0 else "GOOD" if dirty_score < 5 else "WARNING" if dirty_score < 15 else "CRITICAL"

    missing_pct = (missing / total * 100) if total else 0
    dup_pct = (dups / df.shape[0] * 100) if df.shape[0] else 0

    unsalvageable = False
    unsalvage_reasons = []

    if missing_pct > 75:
        unsalvageable = True
        unsalvage_reasons.append(f"{missing_pct:.1f}% of cells missing/blank — most data would be fabricated")
    if dup_pct > 50:
        unsalvageable = True
        unsalvage_reasons.append(f"{dup_pct:.1f}% duplicate rows — very little unique signal")
    high_missing_cols = [col for col in df.columns if df[col].isna().mean() > 0.85]
    if high_missing_cols:
        unsalvageable = True
        unsalvage_reasons.append(f"Critical columns {', '.join(high_missing_cols[:3])} {'and more' if len(high_missing_cols) > 3 else ''} are >85% missing")

    return {
        "dirty_score": dirty_score,
        "severity": severity,
        "missing_count": missing,
        "duplicate_rows": dups,
        "total_cells": total,
        "imputed_ratio": imputed_ratio,
        "unsalvageable": unsalvageable,
        "unsalvage_reasons": unsalvage_reasons
    }


class RunCleaningPayload(BaseModel):
    session_id: str
    config: Dict[str, Any] = {}
    override_warnings: bool = False


class CSVCleaner:
    def run(self, df: pd.DataFrame, config: Dict[str, Any] = None) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any], List[str], List[str]]:
        config = config or {}
        changes = []
        messages = []

        df_orig = df.copy()
        orig_stats = compute_dirty_stats(df_orig)

        imputed_count = 0

        # Simulate progress (real async processing would replace this)
        async def simulate_progress():
            for i in range(1, 101, 10):
                await asyncio.sleep(0.3)  # simulate work
                # In real app, update frontend via WebSocket or SSE

        asyncio.create_task(simulate_progress())

        # Missing value handling
        df = df.replace(r"^\s*$", pd.NA, regex=True)
        fill_strategy = config.get("missing_fill", "auto")

        for col in df.columns:
            if not df[col].isna().any():
                continue

            try:
                if fill_strategy == "zero" or (fill_strategy == "auto" and pd.api.types.is_numeric_dtype(df[col])):
                    val = 0
                elif fill_strategy == "unknown":
                    val = "unknown"
                elif pd.api.types.is_numeric_dtype(df[col]):
                    val = df[col].median()
                    val = 0 if pd.isna(val) else val
                else:
                    mode_series = df[col].mode()
                    val = mode_series.iloc[0] if not mode_series.empty else "unknown"

                imputed_count += df[col].isna().sum()
                df[col] = df[col].fillna(val)
                changes.append(f"Filled '{col}' missing with {val!r} (strategy: {fill_strategy})")
            except Exception as exc:
                fallback = 0 if pd.api.types.is_numeric_dtype(df[col]) else "unknown"
                imputed_count += df[col].isna().sum()
                df[col] = df[col].fillna(fallback)
                changes.append(f"Fallback fill for '{col}' with {fallback!r} (due to {type(exc).__name__})")

        # Text cleaning
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].astype(str).str.strip().str.lower()
            changes.append(f"Cleaned text in '{col}' (strip + lowercase)")

        # Duplicates
        before = len(df)
        df = df.drop_duplicates()
        removed = before - len(df)
        if removed > 0:
            changes.append(f"Removed {removed} duplicate rows")

        # Outliers
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

        # Final stats
        final_stats = compute_dirty_stats(df)
        final_stats["imputed_ratio"] = round(imputed_count / orig_stats["total_cells"] * 100, 2) if orig_stats["total_cells"] else 0.0

        # ML readiness verdict
        verdict = "✅ Fit for ML training"
        if final_stats["imputed_ratio"] > 40 or final_stats["dirty_score"] > 10:
            verdict = "⚠️ Usable with caution"
        if final_stats["imputed_ratio"] > 70 or (orig_stats["missing_count"] / orig_stats["total_cells"] * 100 if orig_stats["total_cells"] else 0) > 80:
            verdict = "❌ Not recommended for ML"

        messages.append(f"ML TRAINING READINESS: {verdict}")

        return df, orig_stats, final_stats, changes, messages


@app.post("/upload_csv")
async def upload_csv(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
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

        stats = compute_dirty_stats(df)
        stats["filename"] = filename

        file_stats.append(stats)

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
    session_id = payload.session_id

    if session_id not in SESSIONS:
        raise HTTPException(400, "Unknown session")

    session = SESSIONS[session_id]
    originals = session["originals"]
    filenames = session["filenames"]
    cleaned_files = []
    all_logs = []

    cleaner = CSVCleaner()

    has_unsalvageable = any(
        compute_dirty_stats(df).get("unsalvageable", False)
        for df in originals
    )

    if has_unsalvageable and not payload.override_warnings:
        raise HTTPException(400, "Some files are unsalvageable. Override required.")

    for idx, df in enumerate(originals):
        df_clean, orig_stats, final_stats, changes, messages = cleaner.run(df, config=payload.config)

        cleaned_files.append(df_clean)

        log = {
            "filename": filenames[idx],
            "dirty_before": orig_stats["dirty_score"],
            "dirty_after": final_stats["dirty_score"],
            "severity": final_stats["severity"],
            "changes": changes,
            "messages": messages
        }
        all_logs.append(log)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, df_clean in enumerate(cleaned_files):
            safe_name = re.sub(r'[^\w\-_. ]', '_', filenames[idx])
            zf.writestr(f"{safe_name}_cleaned.csv", df_clean.to_csv(index=False))

        report = "Multi-File Cleaning Report – V0.6\n" + "=" * 60 + "\n\n"

        if has_unsalvageable and payload.override_warnings:
            report += "⚠️ USER OVERRIDE – Proceeded despite unsalvageable/high-risk warnings on some files.\n\n"

        for log in all_logs:
            report += f"File: {log['filename']}\n"
            report += f"  Dirty BEFORE: {log['dirty_before']:.2f}%\n"
            report += f"  Dirty AFTER : {log['dirty_after']:.2f}%\n"
            report += f"  Severity: {log['severity']}\n"
            report += "  Changes applied:\n" + "\n".join(f"    • {c}" for c in log['changes'] or ["(none)"]) + "\n"
            report += "  Messages / Verdict:\n" + "\n".join(f"    • {m}" for m in log['messages'] or ["(none)"]) + "\n"
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