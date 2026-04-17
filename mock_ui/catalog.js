async function loadData() {
  if (window.MOCK_LIBRARY_DATA) {
    return window.MOCK_LIBRARY_DATA;
  }
  const response = await fetch("./mock-library.json");
  return response.json();
}

const state = {
  data: null,
  search: "",
};

function createNode(tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}

function versionSortKey(versionId) {
  return String(versionId)
    .replace(/^v/, "")
    .split(".")
    .map((part) => Number.parseInt(part, 10) || 0);
}

function compareVersions(left, right) {
  const leftParts = versionSortKey(left);
  const rightParts = versionSortKey(right);
  const maxLength = Math.max(leftParts.length, rightParts.length);
  for (let index = 0; index < maxLength; index += 1) {
    const leftValue = leftParts[index] || 0;
    const rightValue = rightParts[index] || 0;
    if (leftValue !== rightValue) {
      return rightValue - leftValue;
    }
  }
  return 0;
}

function getCatalogEntries() {
  const query = state.search.trim().toLowerCase();
  const entries = state.data.dlss_versions
    .filter((entry) => entry.id !== "game_default")
    .sort((left, right) => compareVersions(left.id, right.id));

  if (!query) {
    return entries;
  }

  return entries.filter((entry) =>
    [entry.id, entry.label, entry.release_name, entry.asset_name]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(query)
  );
}

function renderSummary() {
  const entries = state.data.dlss_versions.filter((entry) => entry.id !== "game_default");
  const downloaded = entries.filter((entry) => entry.downloaded).length;
  const latest = entries.slice().sort((left, right) => compareVersions(left.id, right.id))[0];
  const root = document.getElementById("catalog-summary");
  root.innerHTML = "";

  [
    ["Official versions", String(entries.length)],
    ["Downloaded", String(downloaded)],
    ["Latest", latest ? latest.label : "n/a"],
    ["Source", "NVIDIA/DLSS releases"],
  ].forEach(([label, value]) => {
    const row = createNode("div", "info-row");
    row.append(createNode("span", "", label), createNode("span", "chip", value));
    root.appendChild(row);
  });
}

function renderCatalog() {
  const entries = getCatalogEntries();
  const root = document.getElementById("catalog-list");
  document.getElementById("catalog-count").textContent = `${entries.length} visible versions`;
  root.innerHTML = "";

  if (entries.length === 0) {
    root.appendChild(createNode("div", "empty-list", "No DLSS versions match the current filter."));
    return;
  }

  entries.forEach((entry) => {
    const card = createNode("article", "catalog-card");

    const header = createNode("div", "catalog-header");
    const titleWrap = createNode("div", "");
    titleWrap.append(
      createNode("div", "detail-overline", "Official NVIDIA Release"),
      createNode("h3", "catalog-title", entry.label),
      createNode("p", "subtle", entry.release_name || entry.asset_name || "Official NVIDIA asset")
    );
    const badges = createNode("div", "banner-badges");
    badges.append(
      createNode("span", `badge ${entry.downloaded ? "status-ok" : "badge-support"}`, entry.downloaded ? "Downloaded" : "Not Downloaded"),
      createNode("span", "badge badge-support", entry.published_at ? entry.published_at.slice(0, 10) : "n/a")
    );
    header.append(titleWrap, badges);

    const details = createNode("div", "catalog-meta");
    [
      ["Version", entry.id],
      ["Asset", entry.asset_name || "n/a"],
      ["Runtime path", entry.runtime_path || "not extracted"],
      ["Local zip", entry.local_asset_exists ? "present" : "missing"],
    ].forEach(([label, value]) => {
      const row = createNode("div", "stack-row");
      row.append(createNode("strong", "", label), createNode("code", "", value));
      details.appendChild(row);
    });

    const actions = createNode("div", "catalog-actions");
    const managed = createNode("div", "command-preview");
    managed.append(
      createNode("div", "command-label", "Managed download"),
      createNode("pre", "command-code", entry.download_command || `python3 main.py download-dlss ${entry.id}`)
    );
    actions.appendChild(managed);

    const links = createNode("div", "action-links");
    const releaseLink = createNode("a", "nav-action", "Release Page");
    releaseLink.href = entry.release_url || "#";
    releaseLink.target = "_blank";
    releaseLink.rel = "noreferrer";
    links.appendChild(releaseLink);

    const assetLink = createNode("a", "nav-action", "Official Asset");
    assetLink.href = entry.browser_download_url || "#";
    assetLink.target = "_blank";
    assetLink.rel = "noreferrer";
    links.appendChild(assetLink);
    actions.appendChild(links);

    card.append(header, details, actions);
    root.appendChild(card);
  });
}

function initialize(data) {
  state.data = data;
  document.getElementById("catalog-search").addEventListener("input", (event) => {
    state.search = event.target.value;
    renderCatalog();
  });
  renderSummary();
  renderCatalog();
}

loadData().then(initialize).catch((error) => {
  document.getElementById("catalog-list").textContent = `Failed to load catalog: ${error}`;
});
