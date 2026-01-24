let sessionId = null;
let lastUploadMeta = null;
const API_BASE = "http://localhost:8000";

function getEl(selector) {
  const el = document.querySelector(selector);
  if (!el) console.warn(`Element not found: ${selector}`);
  return el;
}

async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  let res;
  try {
    res = await fetch(url, options);
  } catch (networkErr) {
    throw new Error(
      `Cannot reach backend at ${API_BASE}. Is it running? (${networkErr.message})`
    );
  }

  let data;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    const detail = data && data.detail ? data.detail : res.statusText || `Request failed with status ${res.status}`;
    throw new Error(detail);
  }
  return data;
}

function severityClass(severity) {
  switch (severity) {
    case "CLEAN":   return "text-green-600 dark:text-green-400";
    case "GOOD":    return "text-emerald-600 dark:text-emerald-400";
    case "WARNING": return "text-yellow-600 dark:text-yellow-400";
    default:        return "text-red-600 dark:text-red-400";
  }
}

function setButtonLoading(textEl, spinnerEl, loadingText) {
  if (textEl) textEl.textContent = loadingText;
  if (spinnerEl) spinnerEl.classList.remove("hidden");
}

function clearButtonLoading(textEl, spinnerEl, normalText) {
  if (textEl) textEl.textContent = normalText;
  if (spinnerEl) spinnerEl.classList.add("hidden");
}

function downloadBlob(blob, filename) {
  if (!blob) return;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// Theme handling
function initTheme() {
  const saved = localStorage.getItem("theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  if (saved === "dark" || (!saved && prefersDark)) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
  updateThemeIcons(document.documentElement.classList.contains("dark"));
}

function updateThemeIcons(isDark) {
  document.querySelectorAll("#theme-icon, #theme-icon-header").forEach((el) => {
    if (!el) return;
    el.classList.remove("fa-moon", "fa-sun");
    el.classList.add(isDark ? "fa-sun" : "fa-moon");
    el.classList.add("fas");
  });
  const themeText = getEl("#theme-text");
  if (themeText) themeText.textContent = isDark ? "Light Mode" : "Dark Mode";
}

function toggleTheme() {
  const isDark = !document.documentElement.classList.contains("dark");
  document.documentElement.classList.toggle("dark", isDark);
  localStorage.setItem("theme", isDark ? "dark" : "light");
  updateThemeIcons(isDark);
}

// All initialization & event binding inside DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
  // Init theme
  initTheme();
  document.querySelectorAll("#theme-toggle, #theme-toggle-header").forEach((btn) => {
    if (!btn) return;
    btn.addEventListener("click", toggleTheme);
  });

  // Sidebar hover/draw
  const sidebar = getEl("#sidebar");
  const trigger = getEl("#sidebar-trigger");
  const overlay = getEl("#overlay");
  const menuBtn = getEl("#menu-btn");
  const closeSidebarBtn = getEl("#close-sidebar");

  if (trigger && sidebar) {
    trigger.addEventListener("mouseenter", () => sidebar.classList.remove("-translate-x-full"));
    sidebar.addEventListener("mouseleave", () => sidebar.classList.add("-translate-x-full"));
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.add("-translate-x-full");
    if (overlay) overlay.classList.add("hidden");
  }

  if (menuBtn && sidebar && overlay) {
    menuBtn.addEventListener("click", () => {
      sidebar.classList.remove("-translate-x-full");
      overlay.classList.remove("hidden");
    });
  }

  if (closeSidebarBtn) closeSidebarBtn.addEventListener("click", closeSidebar);
  if (overlay) overlay.addEventListener("click", closeSidebar);

  // Upload handler
  const uploadForm = getEl("#upload-form");
  if (uploadForm) {
    uploadForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const fileInput = getEl("#file-input");
      const status = getEl("#upload-status");
      const dirtyScoreEl = getEl("#dirty-score");
      const dirtyMsgEl = getEl("#dirty-msg");
      const uploadText = getEl("#upload-text");
      const uploadSpinner = getEl("#upload-spinner");
      const runStatus = getEl("#run-status");

      if (!fileInput || !status || !dirtyScoreEl) return;

      const files = fileInput.files;
      if (!files || files.length === 0) {
        status.textContent = "Please select at least one file.";
        return;
      }

      const formData = new FormData();
      for (const file of files) formData.append("files", file);

      // Reset previous state
      sessionId = null;
      lastUploadMeta = null;
      dirtyScoreEl.innerHTML = "--";
      if (dirtyMsgEl) dirtyMsgEl.classList.add("hidden");
      if (runStatus) runStatus.textContent = "";

      status.textContent = `Analyzing ${files.length} file${files.length > 1 ? "s" : ""}...`;

      setButtonLoading(uploadText, uploadSpinner, "Analyzing...");
      uploadForm.querySelectorAll("button, input[type=submit]").forEach(el => el.disabled = true);

      try {
        const data = await apiFetch("/upload_csv", {
          method: "POST",
          body: formData,
        });

        sessionId = data.session_id;
        lastUploadMeta = data;

        let scoreHtml = `<div class="text-sm font-medium mb-2">Dirty Scores (${data.file_count} file${data.file_count > 1 ? "s" : ""}):</div><ul class="space-y-1">`;
        data.file_stats.forEach((stat) => {
          const sevClass = severityClass(stat.severity);
          scoreHtml += `<li><span class="font-medium">${stat.filename}:</span> <span class="${sevClass}">${stat.dirty_score}% (${stat.severity})</span></li>`;
        });
        scoreHtml += "</ul>";
        dirtyScoreEl.innerHTML = scoreHtml;

        if (
          dirtyMsgEl &&
          data.file_stats.some((s) => s.severity !== "CLEAN" && s.severity !== "GOOD")
        ) {
          dirtyMsgEl.classList.remove("hidden");
        }

        status.textContent = `Analysis complete (${data.file_count} file${data.file_count > 1 ? "s" : ""}). Click Run to clean all files.`;
      } catch (err) {
        console.error(err);
        status.textContent = `Error: ${err.message}`;
      } finally {
        clearButtonLoading(uploadText, uploadSpinner, "Analyze Files");
        uploadForm.querySelectorAll("button, input[type=submit]").forEach(el => el.disabled = false);
      }
    });
  }

  // Run cleaning
  const runBtn = getEl("#run-btn");
  if (runBtn) {
    runBtn.addEventListener("click", async () => {
      const status = getEl("#run-status");
      const btnText = getEl("#run-btn-text");
      const spinner = getEl("#run-spinner");

      if (!sessionId) {
        if (status) status.textContent = "Upload files first.";
        return;
      }

      setButtonLoading(btnText, spinner, "Cleaning all files...");
      runBtn.disabled = true;

      try {
        const res = await fetch(`${API_BASE}/run_cleaning`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId }),
        });

        if (!res.ok) {
          let msg = res.statusText || "Failed";
          try {
            const data = await res.json();
            if (data && data.detail) msg = data.detail;
          } catch {}
          throw new Error(msg);
        }

        const blob = await res.blob();
        downloadBlob(blob, "cleaned_files.zip");

        if (status) status.textContent = "All files cleaned & downloaded!";
      } catch (err) {
        console.error(err);
        if (status) status.textContent = `Error: ${err.message}`;
      } finally {
        clearButtonLoading(btnText, spinner, "Run Cleaning & Download ZIP");
        runBtn.disabled = false;
      }
    });
  }
});