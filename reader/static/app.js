const state = {
  articles: [],
  digests: [],
  byId: new Map(),
  focusAreas: new Set(),
  sources: new Set(),
  query: "",
  sort: "newest",
  ranked: null,          // ids in relevance order while a search is active
  snippets: new Map(),   // id -> the matching stretch of summary
};

const el = (id) => document.getElementById(id);

function escapeHtml(text) {
  return (text || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// The digest summaries are markdown; render the small subset that actually appears.
function renderInline(text) {
  return escapeHtml(text)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
}

function renderParagraphs(text) {
  return (text || "")
    .split(/\n{2,}/)
    .filter(Boolean)
    .map((p) => `<p>${renderInline(p)}</p>`)
    .join("");
}

function displayDate(article) {
  if (article.published_raw) return article.published_raw;
  if (article.published_iso) return article.published_iso;
  return `digest ${article.first_seen}`;
}

const when = (a) => a.published_iso || a.first_seen;
const sorters = {
  newest: (a, b) => when(b).localeCompare(when(a)) || a.title.localeCompare(b.title),
  oldest: (a, b) => when(a).localeCompare(when(b)) || a.title.localeCompare(b.title),
  source: (a, b) => a.source.localeCompare(b.source) || when(b).localeCompare(when(a)),
  title: (a, b) => a.title.localeCompare(b.title),
};

// Ranking happens on the server, where the whole summary text is indexed.
// Substring matching here would rank nothing and miss "research" for
// "researchers".
async function runSearch() {
  const query = state.query.trim();
  if (!query) {
    state.ranked = null;
    state.snippets.clear();
    renderArticles();
    return;
  }
  try {
    const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=500`);
    const data = await response.json();
    if (state.query.trim() !== query) return;   // a later keystroke already won
    state.ranked = data.results.map((r) => r.article.id);
    state.snippets = new Map(data.results.map((r) => [r.article.id, r.snippet]));
  } catch (error) {
    state.ranked = [];
    state.snippets.clear();
  }
  renderArticles();
}

function visibleArticles() {
  const passesFilters = (a) =>
    (state.focusAreas.size === 0 || state.focusAreas.has(a.focus_area)) &&
    (state.sources.size === 0 || state.sources.has(a.source));

  if (state.ranked) {
    const rows = state.ranked
      .map((id) => state.byId.get(id))
      .filter((a) => a && passesFilters(a));
    return state.sort === "relevance" ? rows : rows.sort(sorters[state.sort]);
  }
  const rows = state.articles.filter(passesFilters);
  return rows.sort(sorters[state.sort === "relevance" ? "newest" : state.sort]);
}

function articleCard(article) {
  const li = document.createElement("li");
  li.className = "card";
  const repeats = article.repeats.length
    ? `<span>· repeated in ${article.repeats.length} later digest${article.repeats.length > 1 ? "s" : ""}</span>`
    : "";
  li.innerHTML = `
    <h3><a href="${escapeHtml(article.url)}" target="_blank" rel="noopener">${escapeHtml(article.title)}</a></h3>
    <p class="meta">
      <strong>${escapeHtml(article.source)}</strong>
      <span>· ${escapeHtml(displayDate(article))}</span>
      <span class="badge">${escapeHtml(article.focus_area)}</span>
      <span>· first in digest ${escapeHtml(article.first_seen)}</span>
      ${repeats}
    </p>
    <div class="summary">${renderParagraphs(state.snippets.get(article.id) || article.summary)}</div>
    ${article.note ? `<p class="card-note">${renderInline(article.note)}</p>` : ""}
    <div class="card-actions">
      <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener">Read the article →</a>
      <button type="button" class="link-button" data-ask="${escapeHtml(article.title)}" data-ask-id="${escapeHtml(article.id)}">Ask about this</button>
    </div>`;
  return li;
}

function renderArticles() {
  const rows = visibleArticles();
  const list = el("articles");
  list.replaceChildren(...rows.map(articleCard));
  el("empty").hidden = rows.length > 0;
  el("result-count").textContent =
    rows.length === state.articles.length
      ? `${rows.length} articles`
      : `${rows.length} of ${state.articles.length} articles`;
}

function renderFilterGroup(containerId, values, selected, counts) {
  const container = el(containerId);
  container.replaceChildren();
  values.forEach((value) => {
    const label = document.createElement("label");
    label.innerHTML = `<input type="checkbox" value="${escapeHtml(value)}">
      <span>${escapeHtml(value)}</span><span class="count">${counts[value] || 0}</span>`;
    const box = label.querySelector("input");
    box.checked = selected.has(value);
    box.addEventListener("change", () => {
      box.checked ? selected.add(value) : selected.delete(value);
      renderArticles();
    });
    container.appendChild(label);
  });
}

function countBy(key) {
  return state.articles.reduce((acc, a) => {
    acc[a[key]] = (acc[a[key]] || 0) + 1;
    return acc;
  }, {});
}

async function ask(question, articleIds) {
  const panel = el("answer");
  panel.hidden = false;
  el("answer-question").textContent = question;
  el("answer-notice").hidden = true;
  el("answer-sources").textContent = "";
  const useSource = el("use-source").checked ? "fetch" : "cached";
  el("answer-body").innerHTML = useSource === "fetch"
    ? '<p class="thinking">Reading the source articles…</p>'
    : '<p class="thinking">Looking through the digest…</p>';
  el("ask-button").disabled = true;
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, use_source: useSource, article_ids: articleIds }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || response.statusText);

    el("answer-body").innerHTML = data.answer
      ? renderParagraphs(data.answer)
      : '<p class="thinking">Closest entries in the digest:</p>';
    if (data.notice) {
      el("answer-notice").textContent = data.notice;
      el("answer-notice").hidden = false;
    }
    if (data.matches && data.matches.length) {
      el("answer-sources").innerHTML =
        "Based on: " +
        data.matches
          .slice(0, 6)
          .map((m) => `<a href="${escapeHtml(m.url)}" target="_blank" rel="noopener">${escapeHtml(m.title)}</a>`)
          .join(" · ");
    }
  } catch (error) {
    el("answer-body").innerHTML = `<p>Could not answer that: ${escapeHtml(error.message)}</p>`;
  } finally {
    el("ask-button").disabled = false;
  }
}

function wireUp() {
  let searchTimer;
  el("search").addEventListener("input", (event) => {
    state.query = event.target.value;
    if (state.query.trim() && state.sort !== "relevance") {
      state.sort = "relevance";
      el("sort").value = "relevance";
    }
    clearTimeout(searchTimer);
    searchTimer = setTimeout(runSearch, 150);
  });
  el("sort").addEventListener("change", (event) => {
    state.sort = event.target.value;
    renderArticles();
  });
  el("reset").addEventListener("click", () => {
    state.query = "";
    state.ranked = null;
    state.snippets.clear();
    state.focusAreas.clear();
    state.sources.clear();
    state.sort = "newest";
    el("search").value = "";
    el("sort").value = "newest";
    renderFilters();
    renderArticles();
  });
  el("ask-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const question = el("ask-input").value.trim();
    if (question) ask(question);
  });
  el("answer-close").addEventListener("click", () => {
    el("answer").hidden = true;
  });
  el("articles").addEventListener("click", (event) => {
    const button = event.target.closest("[data-ask]");
    if (!button) return;
    const question = `What does the digest say about "${button.dataset.ask}"?`;
    el("ask-input").value = question;
    ask(question, [button.dataset.askId]);
  });
}

function renderFilters() {
  renderFilterGroup("focus-areas", state.focusAreas_all, state.focusAreas, countBy("focus_area"));
  renderFilterGroup("sources", state.sources_all, state.sources, countBy("source"));
}

async function init() {
  const data = await (await fetch("/api/digest")).json();
  state.articles = data.articles;
  state.digests = data.digests;
  state.byId = new Map(data.articles.map((a) => [a.id, a]));
  state.focusAreas_all = data.focus_areas;
  state.sources_all = data.sources;

  const s = data.stats;
  el("stats").textContent =
    `${s.articles} articles · ${s.digests} digests · ${s.first_digest} to ${s.last_digest}` +
    (s.duplicates_folded ? ` · ${s.duplicates_folded} repeats folded` : "");

  renderFilters();
  renderArticles();
  wireUp();
}

init().catch((error) => {
  el("stats").textContent = `Could not load the digest: ${error.message}`;
});
