// app.js - Merged & cleaned version (V0.4 frontend)

let sessionId = null;
let originalConfig = null;

// ── Theme Handling ──────────────────────────────────────────────────────────
function initTheme() {
  const saved = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  if (saved === 'dark' || (!saved && prefersDark)) {
    document.documentElement.classList.add('dark');
  }
  updateThemeIcons(document.documentElement.classList.contains('dark'));
}

function updateThemeIcons(isDark) {
  document.querySelectorAll('#theme-icon, #theme-icon-header').forEach(el => {
    el.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
  });
  const themeText = document.getElementById('theme-text');
  if (themeText) {
    themeText.textContent = isDark ? 'Light Mode' : 'Dark Mode';
  }
}

function toggleTheme() {
  const isDark = !document.documentElement.classList.contains('dark');
  document.documentElement.classList.toggle('dark', isDark);
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  updateThemeIcons(isDark);
}

// ── Sidebar (desktop hover + mobile toggle) ────────────────────────────────
const sidebar = document.getElementById('sidebar');
const trigger = document.getElementById('sidebar-trigger');

if (trigger) {
  trigger.addEventListener('mouseenter', () => {
    sidebar.classList.remove('-translate-x-full');
  });
}

if (sidebar) {
  sidebar.addEventListener('mouseleave', () => {
    sidebar.classList.add('-translate-x-full');
  });
}

function closeSidebar() {
  sidebar?.classList.add('-translate-x-full');
  document.getElementById('overlay')?.classList.add('hidden');
}

document.getElementById('menu-btn')?.addEventListener('click', () => {
  sidebar?.classList.remove('-translate-x-full');
  document.getElementById('overlay')?.classList.remove('hidden');
});

document.getElementById('close-sidebar')?.addEventListener('click', closeSidebar);
document.getElementById('overlay')?.addEventListener('click', closeSidebar);

// ── UI Reset ────────────────────────────────────────────────────────────────
function resetUI() {
  document.getElementById("config-area").value = "";
  document.getElementById("dirty-msg")?.classList.add("hidden");
  document.getElementById("dirty-score").textContent = "";
  document.getElementById("upload-status").textContent = "";
  document.getElementById("run-status").textContent = "";
  document.getElementById("preview-section")?.classList.add("hidden");
  document.getElementById("preview-table").innerHTML = "";
  document.getElementById("run-btn-text").textContent = "Run Cleaning & Download ZIP";
  document.getElementById("run-spinner")?.classList.add("hidden");
  sessionId = null;
  originalConfig = null;
}

// ── Upload & Analysis ───────────────────────────────────────────────────────
document.getElementById("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  resetUI();

  const file = document.getElementById("file-input").files[0];
  if (!file) {
    document.getElementById("upload-status").textContent = "Please select a file.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  const status = document.getElementById("upload-status");
  status.textContent = "Uploading and analyzing...";

  try {
    const res = await fetch("http://localhost:8000/upload_csv", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Upload failed");
    }

    const data = await res.json();

    sessionId = data.session_id;
    originalConfig = data.config;
    document.getElementById("config-area").value = JSON.stringify(data.config, null, 2);

    if (data.severity !== "INFO") {
      const msgEl = document.getElementById("dirty-msg");
      msgEl?.classList.remove("hidden");
      msgEl?.classList.add("alert-enter");
    }

    document.getElementById("dirty-score").textContent = 
      `Current Dirty Score: ${data.dirty_score}% (${data.severity})`;

    // Preview table
    if (data.preview?.length > 0) {
      let html = '<thead class="bg-gray-100 dark:bg-gray-800"><tr>';
      Object.keys(data.preview[0]).forEach(key => {
        html += `<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">${key}</th>`;
      });
      html += '</tr></thead><tbody class="divide-y divide-gray-200 dark:divide-gray-700">';
      
      data.preview.forEach(row => {
        html += '<tr class="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition">';
        Object.values(row).forEach(val => {
          html += `<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">${val ?? '-'}</td>`;
        });
        html += '</tr>';
      });
      html += '</tbody>';

      document.getElementById("preview-table").innerHTML = html;
      document.getElementById("preview-section")?.classList.remove("hidden");
      document.getElementById("preview-section")?.classList.add("slide-in");
    }

    status.textContent = "Analysis complete. Review preview and config.";
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
    console.error(err);
  }
});

// ── Accept Suggestions Button ──────────────────────────────────────────────
document.getElementById("accept-suggestions-btn")?.addEventListener("click", () => {
  if (originalConfig) {
    document.getElementById("config-area").value = JSON.stringify(originalConfig, null, 2);
    document.getElementById("run-status").textContent = "All suggested rules applied — ready to clean.";
  } else {
    document.getElementById("run-status").textContent = "No suggestions available yet.";
  }
});

// ── Run Cleaning & Download ZIP ────────────────────────────────────────────
document.getElementById("run-btn").addEventListener("click", async () => {
  if (!sessionId) {
    document.getElementById("run-status").textContent = "Please upload a file first.";
    return;
  }

  let cfg;
  try {
    cfg = JSON.parse(document.getElementById("config-area").value || "{}");
  } catch {
    document.getElementById("run-status").textContent = "Invalid JSON format in config area.";
    return;
  }

  const btnText = document.getElementById("run-btn-text");
  const spinner = document.getElementById("run-spinner");
  const status = document.getElementById("run-status");

  btnText.textContent = "Cleaning...";
  spinner?.classList.remove("hidden");
  status.textContent = "";

  try {
    const res = await fetch("http://localhost:8000/run_cleaning", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, config: cfg })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Cleaning failed");
    }

    const blob = await res.blob();
    const originalName = document.getElementById("file-input").files[0].name;
    const baseName = originalName.split('.')[0] || "cleaned";
    const fileName = `${baseName}_Cleaned.zip`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    status.textContent = "Success! Cleaned ZIP downloaded.";
    resetUI();
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
    console.error(err);
  } finally {
    btnText.textContent = "Run Cleaning & Download ZIP";
    spinner?.classList.add("hidden");
  }
});

// ── Initialize ──────────────────────────────────────────────────────────────
initTheme();
document.querySelectorAll('#theme-toggle, #theme-toggle-header').forEach(btn => {
  btn.addEventListener("click", toggleTheme);
});