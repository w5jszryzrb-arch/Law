/* NZ Law Assistant — frontend helpers */

// ── Toast ────────────────────────────────────────────────────────────────────
function toast(msg, kind = "info", ms = 3500) {
    let c = document.querySelector(".toast-container");
    if (!c) {
        c = document.createElement("div");
        c.className = "toast-container";
        document.body.appendChild(c);
    }
    const t = document.createElement("div");
    t.className = `toast ${kind}`;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => t.remove(), ms);
}

// ── Tabs ─────────────────────────────────────────────────────────────────────
function initTabs(scope = document) {
    scope.querySelectorAll(".tabs").forEach(tabs => {
        const buttons = tabs.querySelectorAll(".tab-button");
        const panels = tabs.parentElement.querySelectorAll(":scope > .tab-panel");
        buttons.forEach((btn, i) => {
            btn.addEventListener("click", () => {
                buttons.forEach(b => b.classList.remove("active"));
                panels.forEach(p => p.classList.remove("active"));
                btn.classList.add("active");
                const target = btn.dataset.target;
                if (target) {
                    const panel = tabs.parentElement.querySelector(`#${target}`);
                    if (panel) panel.classList.add("active");
                } else if (panels[i]) {
                    panels[i].classList.add("active");
                }
            });
        });
    });
}

// ── Streaming POST ───────────────────────────────────────────────────────────
async function streamPost(url, body, onChunk, onDone) {
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let full = "";
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        full += chunk;
        onChunk && onChunk(chunk, full);
    }
    full += decoder.decode();
    onDone && onDone(full);
    return full;
}

// Render markdown into an output box during streaming (light formatting).
function renderOutput(boxEl, text, streaming = true) {
    const escaped = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    // Simple bold/italic and headers; full markdown isn't necessary for streaming.
    let html = escaped
        .replace(/^### (.+)$/gm, "<h3>$1</h3>")
        .replace(/^## (.+)$/gm, "<h2>$1</h2>")
        .replace(/^# (.+)$/gm, "<h1>$1</h1>")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<em>$1</em>")
        .replace(/`([^`]+)`/g, "<code>$1</code>");
    if (streaming) html += '<span class="cursor"></span>';
    boxEl.innerHTML = html;
}

// Convenience wrapper: streams into a target element, manages button state.
async function runStreaming({ url, body, outputEl, button, onSuccess }) {
    if (!outputEl) return;
    outputEl.innerHTML = '<span class="cursor"></span>';
    let originalBtnHTML = "";
    if (button) {
        originalBtnHTML = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<span class="spinner"></span> Generating...';
    }
    try {
        const full = await streamPost(url, body, (_chunk, total) => {
            renderOutput(outputEl, total, true);
        }, (final) => {
            renderOutput(outputEl, final, false);
        });
        onSuccess && onSuccess(full);
        return full;
    } catch (err) {
        outputEl.innerHTML = `<div style="color:var(--red);">Error: ${err.message}</div>`;
        toast(err.message, "error", 5000);
        throw err;
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = originalBtnHTML;
        }
    }
}

// ── Multi-select widget (checkboxes) ─────────────────────────────────────────
function getMultiSelectValues(container) {
    if (!container) return [];
    return Array.from(container.querySelectorAll('input[type="checkbox"]:checked')).map(c => c.value);
}

// ── Download utility ─────────────────────────────────────────────────────────
function downloadText(filename, text) {
    const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

// ── Persistence ──────────────────────────────────────────────────────────────
async function saveConversation(page, data) {
    try {
        await fetch("/api/save-conversation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ page, data }),
        });
    } catch (e) { /* silent */ }
}

// ── Init on load ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    initTabs();

    // Auto-save subject from sidebar input on change
    const subjectInput = document.getElementById("sidebar-subject");
    if (subjectInput) {
        let timer;
        subjectInput.addEventListener("input", () => {
            const pid = subjectInput.dataset.projectId;
            if (!pid) return;
            clearTimeout(timer);
            timer = setTimeout(async () => {
                await fetch(`/api/projects/${pid}/update`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ subject: subjectInput.value }),
                });
                toast("Subject updated", "success", 1500);
            }, 700);
        });
    }

    // Leave project button
    document.querySelectorAll("[data-action='leave-project']").forEach(btn => {
        btn.addEventListener("click", async () => {
            const res = await fetch("/api/leave-project", { method: "POST" });
            const j = await res.json();
            if (j.redirect) window.location.href = j.redirect;
        });
    });
});
