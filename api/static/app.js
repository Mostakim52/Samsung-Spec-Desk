const SAMPLE_QUERIES = [
  "What are the camera specs of the Samsung Galaxy S23?",
  "Which Samsung phone has the best battery life?",
  "How does the Galaxy S23 compare to the S22 in terms of performance?",
];

const chatEl = document.getElementById("chat");
const receiptsEl = document.getElementById("receipts");
const pipelineEl = document.getElementById("pipeline");
const queryInput = document.getElementById("query");
const askForm = document.getElementById("ask-form");
const askBtn = askForm.querySelector(".ask-btn");
const countEl = document.getElementById("count");
const footerCountEl = document.getElementById("footer-count");
const phoneListEl = document.getElementById("phone-list");

let catalog = [];

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = "";
    try { detail = (await res.json()).detail || ""; } catch (e) { /* no body */ }
    const err = new Error(detail || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

function renderCatalog(phones) {
  phoneListEl.innerHTML = "";
  for (const phone of phones) {
    const li = document.createElement("li");
    li.className = "phone-item";
    li.tabIndex = 0;
    li.setAttribute("role", "button");
    li.setAttribute("aria-label", `Ask about ${phone.name}`);
    li.appendChild(specRow("Chip", shortChip(phone.processor)));
    li.appendChild(specRow("Battery", shortBattery(phone.battery_capacity)));
    li.addEventListener("click", () => askAbout(phone.name));
    li.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); askAbout(phone.name); }
    });
    const nameRow = document.createElement("div");
    nameRow.className = "phone-name";
    const nameSpan = document.createElement("span");
    nameSpan.textContent = phone.name;
    const reviewBtn = document.createElement("button");
    reviewBtn.className = "review-link";
    reviewBtn.type = "button";
    reviewBtn.textContent = "Review";
    reviewBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      requestReview(phone.name);
    });
    nameRow.appendChild(nameSpan);
    nameRow.appendChild(reviewBtn);
    li.prepend(nameRow);
    phoneListEl.appendChild(li);
  }
}

function specRow(label, value) {
  const row = document.createElement("div");
  row.className = "spec-leader";
  const labelSpan = document.createElement("span");
  labelSpan.textContent = label;
  const dots = document.createElement("span");
  dots.className = "leader-dots";
  const valueSpan = document.createElement("span");
  valueSpan.textContent = value;
  row.appendChild(labelSpan);
  row.appendChild(dots);
  row.appendChild(valueSpan);
  return row;
}

function shortChip(chipset) {
  const match = chipset.match(/(Snapdragon 8 Gen \d|Exynos \d+)/);
  return match ? match[1] : chipset.split(" (")[0].slice(0, 24);
}

function shortBattery(battery) {
  const match = battery.match(/\d+\s*mAh/);
  return match ? match[0] : battery.slice(0, 12);
}

function appendQuestion(text) {
  const div = document.createElement("div");
  div.className = "msg msg-question";
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function appendAnswer(text, sources) {
  const div = document.createElement("div");
  div.className = "msg msg-answer";
  div.innerHTML = formatAnswer(text, sources);
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function appendError(text) {
  const div = document.createElement("div");
  div.className = "msg msg-answer msg-error";
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function formatAnswer(text, sources) {
  const escaped = escapeHTML(text);
  let html = escaped;
  for (const source of sources || []) {
    html = highlightModel(html, escapeHTML(source));
  }
  const withSections = html
    .replace(/^## (.+)$/gm, "<h3><span class='section-marker'>Â§</span> $1</h3>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  return withSections;
}

function highlightModel(text, modelName) {
  return text.replace(
    new RegExp(`(?<![^\\s])(${modelName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "g"),
    "<mark class='hl'>$1</mark>"
  );
}

function escapeHTML(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function renderReceipts(sourceNames) {
  receiptsEl.innerHTML = "";
  if (!sourceNames.length) {
    const p = document.createElement("p");
    p.className = "receipt-empty";
    p.textContent = "No receipts yet â€” ask something.";
    receiptsEl.appendChild(p);
    return;
  }
  for (const name of sourceNames) {
    let phone;
    try {
      phone = await fetchJSON(`/api/phones/${encodeURIComponent(name)}`);
    } catch (e) {
      phone = catalog.find((p) => p.name === name) || { name };
    }
    const card = document.createElement("div");
    card.className = "receipt-card";
    const nameP = document.createElement("p");
    const nameSpan = document.createElement("span");
    nameSpan.className = "receipt-name";
    nameSpan.textContent = name;
    nameP.appendChild(nameSpan);
    card.appendChild(nameP);
    card.appendChild(specRow("Display", firstWords(phone.display_size, 3)));
    card.appendChild(specRow("Chip", shortChip(phone.processor || "")));
    card.appendChild(specRow("Battery", shortBattery(phone.battery_capacity || "")));
    receiptsEl.appendChild(card);
  }
}

function firstWords(text, n) {
  return String(text).split(" ").slice(0, n).join(" ");
}

async function askAbout(name) {
  queryInput.value = `Tell me about the ${name}`;
  await submitQuery();
}

async function submitQuery() {
  const query = queryInput.value.trim();
  if (!query || askBtn.disabled) return;
  appendQuestion(query);
  queryInput.value = "";
  askBtn.disabled = true;
  try {
    const result = await fetchJSON("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    appendAnswer(result.answer, result.sources);
    await renderReceipts(result.sources);
  } catch (e) {
    appendError(
      e.status === 404
        ? "No phone by that name in the catalog."
        : "The desk is unreachable. Check the API is running."
    );
  } finally {
    askBtn.disabled = false;
    queryInput.focus();
  }
}

async function requestReview(phoneName) {
  appendQuestion(`Write a review of the ${phoneName}`);
  pipelineEl.hidden = false;
  const steps = pipelineEl.querySelectorAll(".pipeline-step");
  steps.forEach((s) => s.classList.remove("active", "done"));
  steps[0].classList.add("active");
  try {
    const [reviewPromise, stepTimer] = await Promise.all([
      fetchJSON("/api/review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phoneName }),
      }),
      new Promise((resolve) => setTimeout(() => {
        steps[0].classList.remove("active");
        steps[0].classList.add("done");
        steps[1].classList.add("active");
        resolve();
      }, 600)),
    ]);
    steps[1].classList.remove("active");
    steps[1].classList.add("done");
    setTimeout(() => { pipelineEl.hidden = true; }, 1200);
    const div = document.createElement("div");
    div.className = "msg msg-answer msg-review";
    div.innerHTML = formatAnswer(reviewPromise.review, [phoneName]);
    chatEl.appendChild(div);
    chatEl.scrollTop = chatEl.scrollHeight;
    await renderReceipts([reviewPromise.phone || phoneName]);
  } catch (e) {
    pipelineEl.hidden = true;
    appendError(
      e.status === 404
        ? "No phone by that name in the catalog."
        : "The agent pipeline hit an error. Check the API is running."
    );
  }
}

askForm.addEventListener("submit", (e) => {
  e.preventDefault();
  submitQuery();
});

document.querySelectorAll(".chip").forEach((chip, i) => {
  chip.textContent = SAMPLE_QUERIES[i];
  chip.addEventListener("click", () => {
    queryInput.value = SAMPLE_QUERIES[i];
    submitQuery();
  });
});

(async function init() {
  try {
    catalog = await fetchJSON("/api/phones");
    renderCatalog(catalog);
    countEl.textContent = catalog.length;
    footerCountEl.textContent = `${catalog.length} phones`;
    await renderReceipts([]);
  } catch (e) {
    countEl.textContent = "0";
    footerCountEl.textContent = "0 phones";
    appendError("The desk is unreachable. Check the API is running.");
  }
})();
