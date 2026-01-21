import io
import json
from pathlib import Path

import pandas as pd
import yaml
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from sklearn.model_selection import train_test_split

app = FastAPI(title="CSV & Excel Cleaning Bot")

# ---------- Cleaner Class ----------

class CSVCleaner:
    def __init__(self, config_path: str = None, config_dict: dict = None):
        if config_dict:
            self.cfg = config_dict
        elif config_path:
            with open(config_path, "r") as f:
                self.cfg = yaml.safe_load(f)
        else:
            self.cfg = {}

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
        df_train, df_temp = train_test_split(
            df, test_size=temp_size, stratify=stratify, random_state=42
        )
        relative_val_size = val_size / temp_size
        stratify_temp = df_temp[target] if stratify is not None else None
        df_val, df_test = train_test_split(
            df_temp, test_size=(1 - relative_val_size), stratify=stratify_temp, random_state=42
        )
        out_dir = Path(scfg.get("output_dir", "splits"))
        out_dir.mkdir(parents=True, exist_ok=True)
        df_train.to_csv(out_dir / "train.csv", index=False)
        df_val.to_csv(out_dir / "val.csv", index=False)
        df_test.to_csv(out_dir / "test.csv", index=False)

    def is_dirty(self, df: pd.DataFrame) -> tuple[bool, list]:
        dirty = False
        messages = []
        missing_cols = df.columns[df.isna().any()].tolist()
        if missing_cols:
            dirty = True
            messages.append(f"Missing values in: {missing_cols}")
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            dirty = True
            messages.append(f"{dup_count} duplicate rows detected")
        return dirty, messages

    def run(self, df: pd.DataFrame = None):
        if df is None:
            df = self.load()
        df = self.apply_dtypes(df)
        df = self.handle_missing(df)
        df = self.text_clean(df)
        df = self.drop_duplicates(df)
        df = self.handle_outliers(df)
        df = self.sort(df)
        self.split(df)
        dirty, messages = self.is_dirty(df)
        return df, dirty, messages


# ---------- In-memory sessions ----------

SESSIONS: dict[str, pd.DataFrame] = {}


# ---------- HTML UI with chat, config editor, dirty message ----------

@app.get("/", response_class=HTMLResponse)
async def root():
    html = """
<!DOCTYPE html>
<html>
<head>
<title>CSV Cleaning Bot</title>
<style>
body { font-family: sans-serif; margin: 20px; }
#chat { border: 1px solid #ccc; padding: 10px; height: 250px; overflow-y: auto; }
.msg-user { color: blue; }
.msg-bot { color: green; }
#config-area { width: 100%; height: 180px; }
#dirty-msg { color: red; font-weight: bold; margin-bottom: 10px; }
</style>
</head>
<body>
<h2>CSV Cleaning & Sorting Bot</h2>
<div id="dirty-msg" style="display:none;">
⚠️ Your dataset looks dirty. This tool will help clean it. Verify cleaning rules before running.
</div>

<h3>1. Upload CSV</h3>
<form id="upload-form">
<input type="file" id="file-input" accept=".csv" required />
<button type="submit">Upload & Suggest Config</button>
</form>
<p id="upload-status"></p>

<h3>2. Chat about cleaning rules</h3>
<div id="chat"></div>
<input type="text" id="chat-input" placeholder="Ask e.g. 'Sort by date, drop rows with missing label'"/>
<button id="send-btn">Send</button>

<h3>3. Config (you can edit manually)</h3>
<textarea id="config-area"></textarea><br/>
<button id="run-btn">Run Cleaning</button>
<p id="run-status"></p>

<script>
let currentConfig = null;
let sessionId = null;

function appendMessage(sender,text){
  const chat=document.getElementById("chat");
  const div=document.createElement("div");
  div.className=sender==="user"?"msg-user":"msg-bot";
  div.textContent=sender+": "+text;
  chat.appendChild(div);
  chat.scrollTop=chat.scrollHeight;
}

document.getElementById("upload-form").addEventListener("submit", async function(e){
  e.preventDefault();
  const fileInput=document.getElementById("file-input");
  if(!fileInput.files.length) return;

  const formData=new FormData();
  formData.append("file",fileInput.files[0]);

  document.getElementById("upload-status").textContent="Uploading...";
  const res=await fetch("/upload_csv",{method:"POST",body:formData});
  const data=await res.json();
  if(res.ok){
    sessionId=data.session_id;
    currentConfig=data.config;
    document.getElementById("config-area").value=JSON.stringify(currentConfig,null,2);
    document.getElementById("upload-status").textContent="Uploaded. Basic config suggested.";

    if(data.is_dirty){
      document.getElementById("dirty-msg").style.display="block";
    } else {
      document.getElementById("dirty-msg").style.display="none";
    }

    appendMessage("bot","Basic cleaning config suggested. You can tweak via chat or JSON.");
  } else {
    document.getElementById("upload-status").textContent="Error: "+data.detail;
  }
});

document.getElementById("send-btn").addEventListener("click", async function(){
  const input=document.getElementById("chat-input");
  const text=input.value.trim();
  if(!text||!sessionId) return;
  appendMessage("user",text);
  input.value="";

  const res=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({session_id:sessionId,message:text,config:currentConfig})});
  const data=await res.json();
  if(res.ok){
    appendMessage("bot",data.reply);
    currentConfig=data.config;
    document.getElementById("config-area").value=JSON.stringify(currentConfig,null,2);
  }else{
    appendMessage("bot","Error: "+data.detail);
  }
});

document.getElementById("run-btn").addEventListener("click", async function(){
  if(!sessionId){
    document.getElementById("run-status").textContent="Upload a CSV first.";
    return;
  }
  let cfgText=document.getElementById("config-area").value;
  try{currentConfig=JSON.parse(cfgText);}catch(e){document.getElementById("run-status").textContent="Config is not valid JSON.";return;}
  document.getElementById("run-status").textContent="Running cleaning...";
  const res=await fetch("/run_cleaning",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({session_id:sessionId,config:currentConfig})});
  if(res.ok){
    const blob=await res.blob();
    const url=window.URL.createObjectURL(blob);
    const a=document.createElement("a");
    a.href=url;
    a.download="cleaned.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    document.getElementById("run-status").textContent="Cleaning finished. File downloaded.";
  }else{
    const data=await res.json();
    document.getElementById("run-status").textContent="Error: "+data.detail;
  }
});
</script>
</body>
</html>
"""
    return HTMLResponse(html)


# ---------- API Endpoints ----------

@app.post("/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        return JSONResponse(status_code=400, content={"detail":"Only .csv files supported."})

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail":f"Could not read CSV: {e}"})

    session_id = f"sess_{len(SESSIONS)+1}"
    SESSIONS[session_id] = df

    cleaner = CSVCleaner()
    is_dirty, messages = cleaner.is_dirty(df)

    # Suggest basic config for now
    config = {
        "dtypes": {col:"float" if pd.api.types.is_numeric_dtype(df[col]) else "category" for col in df.columns},
        "missing":{"drop_rows_if_missing_any_of":[],"fill":{}},
        "text_cleaning":{"lower_columns":[],"strip_spaces_columns":[],"remove_chars":{"columns":[],"pattern":None}},
        "duplicates":{"subset":None,"keep":"first"},
        "outliers":{"zscore":{"columns":[col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])],"threshold":3.0}},
        "sort":{"by":[],"ascending":True},
        "split":{"enabled":False}
    }

    return {"session_id":session_id,"config":config,"is_dirty":is_dirty,"messages":messages}


@app.post("/chat")
async def chat(payload: dict):
    session_id = payload.get("session_id")
    message = payload.get("message","")
    config = payload.get("config",{})

    if session_id not in SESSIONS:
        return JSONResponse(status_code=400,content={"detail":"Unknown session_id."})

    msg_lower = message.lower()
    if "drop rows" in msg_lower and "missing" in msg_lower:
        parts=message.strip().split()
        col=parts[-1]
        config.setdefault("missing",{}).setdefault("drop_rows_if_missing_any_of",[])
        if col not in config["missing"]["drop_rows_if_missing_any_of"]:
            config["missing"]["drop_rows_if_missing_any_of"].append(col)

    if "sort by" in msg_lower:
        try:
            after_sort=message.lower().split("sort by",1)[1].strip()
            words=after_sort.split()
            col=words[0].strip(",.")
            config.setdefault("sort",{})
            config["sort"]["by"]=[col]
            config["sort"]["ascending"]="desc" not in msg_lower and "descending" not in msg_lower
        except: pass

    reply="Updated config based on your message."
    return {"reply":reply,"config":config}


@app.post("/run_cleaning")
async def run_cleaning(payload: dict):
    session_id = payload.get("session_id")
    config = payload.get("config",{})

    if session_id not in SESSIONS:
        return JSONResponse(status_code=400,content={"detail":"Unknown session_id"})

    df = SESSIONS[session_id]
    cleaner = CSVCleaner(config_dict=config)
    df_clean, dirty, messages = cleaner.run(df)

    buf = io.StringIO()
    df_clean.to_csv(buf,index=False)
    buf.seek(0)
    headers = {"Content-Disposition":"attachment; filename=cleaned.csv"}
    if dirty:
        headers["X-Dataset-Dirty"] = "; ".join(messages)

    return StreamingResponse(buf,media_type="text/csv",headers=headers)


# ---------- Run server ----------
if __name__=="__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
