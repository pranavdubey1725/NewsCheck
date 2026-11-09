const $ = (id) => document.getElementById(id);
const form = $("form"), text = $("text"), go = $("go");
const steps = $("steps"), summary = $("summary"), report = $("report");

$("today").textContent = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

const esc =(s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function addStep(message, cls = "active") {
  steps.querySelectorAll("li.active").forEach((li) => li.classList.remove("active"));
  const li = document.createElement("li");
  li.className = cls;
  li.textContent = message;
  steps.appendChild(li);
}

function handle(ev) {
  if (ev.stage === "summary_token") {
    summary.hidden = false;
    summary.textContent += ev.message;
  } else if (ev.stage === "done") {
    steps.querySelectorAll("li.active").forEach((li) => li.classList.remove("active"));
    renderReport(ev.report || "");
  } else if (ev.stage === "error") {
    addStep(ev.message, "error");
  } else {
    addStep(ev.message);
  }
}

// The report is plain text (see newscheck/report.py); turn it into cards.
function renderReport(raw) {
  const lines = raw.split("\n");
  if (!raw.startsWith("CLAIM CHECKED:")) {
    report.innerHTML = `<p class="message">${esc(raw)}</p>`;
    $("report-block").hidden = false;
    return;
  }
  let html = "", card = null, headlineDone = false;
  const close = () => { if (card !== null) { html += card + "</div>"; card = null; } };

  for (const line of lines) {
    const t = line.trim();
    if (!t || t.startsWith("newscheck shows what news")) continue;
    let m;
    if ((m = line.match(/^CLAIM CHECKED: (.*)$/))) {
      html += `<div class="claim"><span class="k">Claim checked</span>${esc(m[1])}</div>`;
    } else if ((m = line.match(/^NOT CHECKED \(opinion\): (.*)$/))) {
      html += `<div class="claim"><span class="k">Set aside (opinion)</span>${esc(m[1])}</div>`;
    } else if ((m = line.match(/^- (.*)  \((.+)\)$/))) {
      close();
      const cls = m[2].startsWith("agrees") ? "agree" : m[2].startsWith("disagrees") ? "disagree" : "";
      card = `<div class="source"><span class="tag ${cls}">${esc(m[2])}</span><h3>${esc(m[1])}</h3>`;
    } else if (card !== null && t.startsWith("http")) {
      card += `<a href="${esc(t)}" target="_blank" rel="noopener">${esc(t)}</a>`;
    } else if (card !== null && t.startsWith('"')) {
      card += `<blockquote>${esc(t.replace(/^"|"$/g, ""))}</blockquote>`;
    } else if (card !== null) {
      card += `<p>${esc(t)}</p>`;
    } else if (!headlineDone) {
      html += `<p class="headline">${esc(t)}</p>`;
      headlineDone = true;
    }
  }
  close();
  report.innerHTML = html;
  $("report-block").hidden = false;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = text.value.trim();
  if (!body) return;

  go.disabled = true;
  go.textContent = "Checking…";
  steps.innerHTML = "";
  summary.textContent = "";
  summary.hidden = true;
  report.innerHTML = "";
  $("report-block").hidden = true;
  $("progress-block").hidden = false;
  $("empty").hidden = true;

  try {
    const res = await fetch("/api/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: body }),
    });
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n\n")) !== -1) {
        const chunk = buf.slice(0, i);
        buf = buf.slice(i + 2);
        const data = chunk.split("\n").filter((l) => l.startsWith("data: ")).map((l) => l.slice(6)).join("");
        if (data) handle(JSON.parse(data));
      }
    }
  } catch (err) {
    addStep("Couldn't reach the server. Please try again.", "error");
  } finally {
    go.disabled = false;
    go.textContent = "Check post";
  }
});
