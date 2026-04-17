async function loadData() {
  if (window.MOCK_LIBRARY_DATA) {
    return window.MOCK_LIBRARY_DATA;
  }
  const response = await fetch("./mock-library.json");
  return response.json();
}

const RUNNER_PRESETS = [
  {
    id: "current",
    label: "Current Runtime",
    description: "Use the runtime detected by the planner export.",
  },
  {
    id: "proton_experimental",
    label: "Proton Experimental",
    description: "Steam's fast-moving compatibility branch.",
  },
  {
    id: "ge_proton",
    label: "GE-Proton",
    description: "Community Proton variant for edge-case compatibility.",
  },
  {
    id: "system_wine",
    label: "System Wine",
    description: "Manual advanced runner path outside the default flow.",
  },
];

const TOGGLE_DEFS = [
  {
    id: "use_mangohud",
    label: "MangoHud",
    description: "Overlay via mangohud %command%",
  },
  {
    id: "use_gamemode",
    label: "GameMode",
    description: "Performance wrapper via gamemoderun %command%",
  },
  {
    id: "disable_nvapi",
    label: "Disable NVAPI",
    description: "Turn off NVIDIA's NVAPI support library for problematic titles.",
  },
  {
    id: "hide_nvidia_gpu",
    label: "Hide NVIDIA GPU",
    description: "Pretend the GPU is AMD for Windows-only NVIDIA detection issues.",
  },
  {
    id: "use_wined3d",
    label: "wined3d Fallback",
    description: "Switch from DXVK to OpenGL-based wined3d for troubleshooting.",
  },
  {
    id: "disable_fsync",
    label: "Disable fsync",
    description: "Fallback for Proton synchronization issues.",
  },
  {
    id: "disable_esync",
    label: "Disable esync",
    description: "Additional compatibility fallback for unstable titles.",
  },
  {
    id: "integer_scaling",
    label: "Integer Scaling",
    description: "Enable sharp integer scaling when the title benefits from it.",
  },
  {
    id: "proton_log",
    label: "Proton Logging",
    description: "Write a launch log for debugging failed starts.",
  },
];

const state = {
  data: null,
  selectedGameId: null,
  selectedProfile: null,
  search: "",
  ui: {
    payloadByGame: {},
    runnerByGame: {},
    togglesByGame: {},
  },
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

function statusClass(status) {
  return `status-${status}`;
}

function titleCase(value) {
  return String(value || "")
    .split(/[_-\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatSupport(value) {
  return titleCase(value || "unknown");
}

function formatBoolean(value, positive = "Yes", negative = "No") {
  return value ? positive : negative;
}

function formatAssessment(assessment) {
  if (!assessment || assessment.level === "none") {
    return "No anti-cheat markers";
  }
  const vendor = assessment.vendor || "Unknown vendor";
  return `${vendor} • ${titleCase(assessment.policy)}`;
}

function summarizeCount(items, singular, plural = `${singular}s`) {
  return `${items} ${items === 1 ? singular : plural}`;
}

function getSelectedGame() {
  return state.data.games.find((game) => game.id === state.selectedGameId);
}

function getSelectedView(game) {
  return game.profiles[state.selectedProfile] || game.profiles[game.default_profile];
}

function getFilteredGames() {
  const query = state.search.trim().toLowerCase();
  if (!query) {
    return state.data.games;
  }
  return state.data.games.filter((game) => {
    const view = getSelectedView(game);
    const haystack = [
      game.name,
      game.launcher,
      game.runtime,
      game.release_support,
      view.launch_plan.compatibility_status,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

function getRollbacksForGame(gameId) {
  return state.data.rollbacks.filter((entry) => entry.install_id === gameId);
}

function getPayloadLabel(payloadId) {
  const version = state.data.dlss_versions.find((entry) => entry.id === payloadId);
  if (version) {
    return version.label;
  }
  return payloadId === "game_default" ? "Game Default" : payloadId;
}

function ensureGameUiState(game, view) {
  const currentPayload =
    view.launch_plan.dlss_version_selection ||
    view.effective_profile_config.dlss_version ||
    view.effective_profile_config.dlss_mode ||
    "game_default";

  if (!state.ui.payloadByGame[game.id]) {
    state.ui.payloadByGame[game.id] = currentPayload;
  }

  if (!state.ui.runnerByGame[game.id]) {
    state.ui.runnerByGame[game.id] = "current";
  }

  if (!state.ui.togglesByGame[game.id]) {
    const env = view.launch_plan.env || {};
    state.ui.togglesByGame[game.id] = {
      use_mangohud: Boolean(view.effective_profile_config.use_mangohud),
      use_gamemode: Boolean(view.effective_profile_config.use_gamemode),
      disable_nvapi: env.PROTON_DISABLE_NVAPI === "1" || view.effective_profile_config.enable_nvapi === false,
      hide_nvidia_gpu: env.PROTON_HIDE_NVIDIA_GPU === "1",
      use_wined3d: env.PROTON_USE_WINED3D === "1",
      disable_fsync: env.PROTON_NO_FSYNC === "1",
      disable_esync: env.PROTON_NO_ESYNC === "1",
      integer_scaling: env.WINE_FULLSCREEN_INTEGER_SCALING === "1",
      proton_log: env.PROTON_LOG === "1",
    };
  }
}

function setSelectedGame(gameId) {
  state.selectedGameId = gameId;
  renderLibrary();
  renderDetail();
}

function setSelectedProfile(profileName) {
  state.selectedProfile = profileName;
  renderSidebar();
  renderLibrary();
  renderDetail();
}

function setSearch(value) {
  state.search = value;
  const filteredGames = getFilteredGames();
  if (filteredGames.length > 0 && !filteredGames.some((game) => game.id === state.selectedGameId)) {
    state.selectedGameId = filteredGames[0].id;
  }
  renderLibrary();
  renderDetail();
}

function setPayload(gameId, payloadId) {
  state.ui.payloadByGame[gameId] = payloadId;
  renderDetail();
}

function setRunner(gameId, runnerId) {
  state.ui.runnerByGame[gameId] = runnerId;
  renderDetail();
}

function toggleOption(gameId, optionId) {
  state.ui.togglesByGame[gameId][optionId] = !state.ui.togglesByGame[gameId][optionId];
  renderDetail();
}

function renderSidebar() {
  document.getElementById("generated-at").textContent = state.data.generated_at;

  const browseRoot = document.getElementById("browse-summary");
  browseRoot.innerHTML = "";

  const counts = {
    total: state.data.games.length,
    supported: state.data.games.filter((game) => game.release_support === "supported").length,
    advanced: state.data.games.filter((game) => game.release_support === "advanced").length,
    experimental: state.data.games.filter((game) => game.release_support === "experimental").length,
  };

  [
    ["All Games", summarizeCount(counts.total, "title")],
    ["Supported", summarizeCount(counts.supported, "title")],
    ["Advanced", summarizeCount(counts.advanced, "title")],
    ["Experimental", summarizeCount(counts.experimental, "title")],
  ].forEach(([label, value]) => {
    const row = createNode("div", "info-row");
    row.append(createNode("span", "", label), createNode("span", "chip", value));
    browseRoot.appendChild(row);
  });

  const systemBadges = document.getElementById("system-badges");
  systemBadges.innerHTML = "";
  [
    ["Steam", formatBoolean(state.data.capabilities.steam_available, "Ready", "Missing")],
    ["Vulkan", formatBoolean(state.data.capabilities.vulkan_available, "Ready", "Missing")],
    ["NVIDIA", formatBoolean(state.data.capabilities.nvidia_driver_present, "Detected", "Missing")],
    ["Smooth Motion", formatBoolean(state.data.capabilities.smooth_motion_supported, "Supported", "Unavailable")],
  ].forEach(([label, value]) => {
    systemBadges.appendChild(createNode("span", "chip", `${label}: ${value}`));
  });

  const capabilityLines = document.getElementById("capability-lines");
  capabilityLines.innerHTML = "";
  [
    ["Steam path", state.data.capabilities.steam_path || "not found"],
    ["Vulkaninfo", state.data.capabilities.vulkaninfo_path || "not found"],
    ["NVIDIA SMI", state.data.capabilities.nvidia_smi_path || "not found"],
  ].forEach(([label, value]) => {
    const row = createNode("div", "stack-row");
    row.append(createNode("strong", "", label), createNode("code", "", value));
    capabilityLines.appendChild(row);
  });
}

function renderProfileSelect() {
  const profileSelect = document.getElementById("profile-select");
  profileSelect.innerHTML = "";
  state.data.profiles.forEach((profile) => {
    const option = document.createElement("option");
    option.value = profile;
    option.textContent = profile;
    if (profile === state.selectedProfile) {
      option.selected = true;
    }
    profileSelect.appendChild(option);
  });
}

function renderLibrary() {
  const root = document.getElementById("library");
  const filteredGames = getFilteredGames();
  document.getElementById("library-count").textContent = summarizeCount(filteredGames.length, "visible title");
  root.innerHTML = "";

  if (filteredGames.length === 0) {
    root.appendChild(createNode("div", "empty-list", "No titles match the current search."));
    return;
  }

  filteredGames.forEach((game) => {
    const view = getSelectedView(game);
    const plan = view.launch_plan;
    const button = document.createElement("button");
    button.className = `library-item ${game.id === state.selectedGameId ? "is-active" : ""}`.trim();

    const cover = createNode("div", "library-cover", game.name.slice(0, 1).toUpperCase());
    const meta = createNode("div", "library-meta");
    meta.append(
      createNode("strong", "", game.name),
      createNode("span", "", `${titleCase(game.launcher)} • ${game.runtime}`),
      createNode("span", "", `${formatSupport(game.release_support)} • ${titleCase(plan.compatibility_status)}`)
    );

    const side = createNode("div", "library-side");
    const status = createNode("span", `badge ${statusClass(plan.compatibility_status)}`, plan.compatibility_status);
    const support = createNode("span", "tiny-tag", game.release_support);
    side.append(status, support);

    button.append(cover, meta, side);
    button.addEventListener("click", () => setSelectedGame(game.id));
    root.appendChild(button);
  });
}

function renderMetaStrip(game, view) {
  const plan = view.launch_plan;
  const rollbacks = getRollbacksForGame(game.id);
  const items = [
    ["Runtime", game.runtime],
    ["Anti-Cheat", formatAssessment(plan.anti_cheat_assessment)],
    ["Payload", getPayloadLabel(state.ui.payloadByGame[game.id])],
    ["Rollbacks", summarizeCount(rollbacks.length, "snapshot")],
  ];

  const root = document.getElementById("detail-meta-strip");
  root.innerHTML = "";
  items.forEach(([label, value]) => {
    const card = createNode("div", "detail-meta-card");
    card.append(createNode("div", "subtle", label), createNode("strong", "", value));
    root.appendChild(card);
  });
}

function renderPayloadOptions(game) {
  const root = document.getElementById("payload-options");
  root.innerHTML = "";
  const selectedPayload = state.ui.payloadByGame[game.id];
  state.data.dlss_versions
    .filter((entry) => entry.selectable !== false)
    .forEach((entry) => {
      const button = createNode(
        "button",
        `choice-card ${entry.id === selectedPayload ? "is-active" : ""}`.trim()
      );
      button.append(
        createNode("strong", "", entry.label),
        createNode("span", "", entry.id === "game_default" ? "Use the shipped game payload." : "Switch the preview to this catalog version.")
      );
      button.addEventListener("click", () => setPayload(game.id, entry.id));
      root.appendChild(button);
    });
}

function renderRunnerOptions(game, view) {
  const root = document.getElementById("runner-options");
  root.innerHTML = "";
  const selectedRunner = state.ui.runnerByGame[game.id];
  RUNNER_PRESETS.forEach((preset) => {
    const button = createNode(
      "button",
      `choice-card ${preset.id === selectedRunner ? "is-active" : ""}`.trim()
    );
    const description =
      preset.id === "current"
        ? `${view.launch_plan.install.execution_strategy} • ${game.runtime}`
        : preset.description;
    button.append(createNode("strong", "", preset.label), createNode("span", "", description));
    button.addEventListener("click", () => setRunner(game.id, preset.id));
    root.appendChild(button);
  });
}

function renderRuntimeOptions(game) {
  const root = document.getElementById("runtime-options");
  root.innerHTML = "";
  const toggleState = state.ui.togglesByGame[game.id];
  TOGGLE_DEFS.forEach((definition) => {
    const row = createNode("div", "option-row");
    const meta = createNode("div", "");
    meta.append(createNode("strong", "", definition.label), createNode("span", "", definition.description));
    const toggle = createNode(
      "button",
      `toggle ${toggleState[definition.id] ? "is-on" : ""}`.trim()
    );
    toggle.type = "button";
    toggle.setAttribute("aria-pressed", toggleState[definition.id] ? "true" : "false");
    toggle.addEventListener("click", () => toggleOption(game.id, definition.id));
    row.append(meta, toggle);
    root.appendChild(row);
  });
}

function buildPreviewCommand(game, view, fallback = false) {
  const plan = view.launch_plan;
  const install = plan.install || {};
  const toggles = state.ui.togglesByGame[game.id];
  const env = { ...(plan.env || {}) };

  if (fallback) {
    env.PROTON_USE_WINED3D = "1";
    env.PROTON_NO_FSYNC = "1";
    env.PROTON_LOG = "1";
  } else {
    if (toggles.disable_nvapi) {
      delete env.PROTON_ENABLE_NVAPI;
      delete env.DXVK_ENABLE_NVAPI;
      env.PROTON_DISABLE_NVAPI = "1";
    } else {
      delete env.PROTON_DISABLE_NVAPI;
      if ((plan.env || {}).PROTON_ENABLE_NVAPI) {
        env.PROTON_ENABLE_NVAPI = (plan.env || {}).PROTON_ENABLE_NVAPI;
      }
      if ((plan.env || {}).DXVK_ENABLE_NVAPI) {
        env.DXVK_ENABLE_NVAPI = (plan.env || {}).DXVK_ENABLE_NVAPI;
      }
    }

    const toggleMap = [
      ["hide_nvidia_gpu", "PROTON_HIDE_NVIDIA_GPU"],
      ["use_wined3d", "PROTON_USE_WINED3D"],
      ["disable_fsync", "PROTON_NO_FSYNC"],
      ["disable_esync", "PROTON_NO_ESYNC"],
      ["integer_scaling", "WINE_FULLSCREEN_INTEGER_SCALING"],
      ["proton_log", "PROTON_LOG"],
    ];

    toggleMap.forEach(([toggleKey, envKey]) => {
      if (toggles[toggleKey]) {
        env[envKey] = "1";
      } else if (!(plan.env || {})[envKey]) {
        delete env[envKey];
      }
    });
  }

  const wrappers = [];
  if (!fallback && toggles.use_gamemode) {
    wrappers.push("gamemoderun");
  }
  if (!fallback && toggles.use_mangohud) {
    wrappers.push("mangohud");
  }

  const envPrefix = Object.entries(env)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}=${value}`)
    .join(" ");

  const baseCommand = Array.isArray(install.launch_command)
    ? install.launch_command.join(" ")
    : plan.command_preview;
  const args = plan.args ? ` ${plan.args}` : "";
  return [envPrefix, wrappers.join(" "), `${baseCommand}${args}`].filter(Boolean).join(" ");
}

function renderLaunchPreview(game, view) {
  document.getElementById("command-preview").textContent = buildPreviewCommand(game, view, false);
  document.getElementById("fallback-preview").textContent = buildPreviewCommand(game, view, true);

  const selectedRunner = RUNNER_PRESETS.find((preset) => preset.id === state.ui.runnerByGame[game.id]);
  const selectedPayload = getPayloadLabel(state.ui.payloadByGame[game.id]);
  const activeToggles = Object.values(state.ui.togglesByGame[game.id]).filter(Boolean).length;

  const summary = document.getElementById("selection-summary");
  summary.innerHTML = "";
  [
    ["Payload", selectedPayload],
    ["Runner", selectedRunner ? selectedRunner.label : "Current Runtime"],
    ["Active toggles", summarizeCount(activeToggles, "toggle")],
    ["Mutation mode", view.launch_plan.mutation_plan?.status || "planned"],
  ].forEach(([label, value]) => {
    const row = createNode("div", "info-row");
    row.append(createNode("span", "", label), createNode("span", "chip", value));
    summary.appendChild(row);
  });

  const commandsRoot = document.getElementById("cli-commands");
  commandsRoot.innerHTML = "";
  Object.entries(game.cli_commands).forEach(([label, command]) => {
    const row = createNode("div", "command-row");
    row.append(createNode("strong", "", titleCase(label)), createNode("code", "", command));
    commandsRoot.appendChild(row);
  });
}

function renderSafety(game, view) {
  const plan = view.launch_plan;
  const policy = view.policy_report;

  const safetyRoot = document.getElementById("safety-summary");
  safetyRoot.innerHTML = "";
  [
    ["Compatibility", plan.compatibility_status],
    ["Release support", formatSupport(game.release_support)],
    ["Anti-cheat policy", titleCase(plan.anti_cheat_assessment.policy || "unknown")],
    ["Safe actions", (policy.anti_cheat.safe_actions || []).join(", ") || "none"],
    ["Blocked actions", (policy.anti_cheat.blocked_actions || []).join(", ") || "none"],
  ].forEach(([label, value]) => {
    const row = createNode("div", "stack-row");
    row.append(createNode("strong", "", label), createNode("code", "", value));
    safetyRoot.appendChild(row);
  });
}

function renderWarnings(view) {
  const root = document.getElementById("warnings-list");
  root.innerHTML = "";
  const warnings = [...(view.launch_plan.warnings || []), ...(view.launch_plan.blocked_reasons || [])];
  if (warnings.length === 0) {
    root.appendChild(createNode("div", "empty-list", "No warnings or blocked reasons for the selected profile."));
    return;
  }
  warnings.forEach((warning) => {
    const row = createNode("div", "stack-row");
    row.append(createNode("strong", "", "Planner note"), createNode("span", "subtle", warning));
    root.appendChild(row);
  });
}

function renderPolicyReasons(view) {
  const root = document.getElementById("policy-list");
  root.innerHTML = "";
  const reasons = view.launch_plan.policy_reasons || [];
  if (reasons.length === 0) {
    root.appendChild(createNode("div", "empty-list", "No explicit policy reasons for this install."));
    return;
  }
  reasons.forEach((reason) => {
    const row = createNode("div", "stack-row");
    row.append(createNode("strong", "", "Policy reason"), createNode("span", "subtle", reason));
    root.appendChild(row);
  });
}

function renderRollbacks(game) {
  const root = document.getElementById("rollback-list");
  root.innerHTML = "";
  const rollbacks = getRollbacksForGame(game.id);
  if (rollbacks.length === 0) {
    root.appendChild(createNode("div", "empty-list", "No rollback manifests recorded for this install."));
    return;
  }
  rollbacks.slice(0, 4).forEach((entry) => {
    const row = createNode("div", "stack-row");
    row.append(
      createNode("strong", "", entry.rollback_id || entry.id || "rollback"),
      createNode("span", "subtle", entry.created_at || "timestamp unavailable")
    );
    root.appendChild(row);
  });
}

function renderDetail() {
  const filteredGames = getFilteredGames();
  const empty = document.getElementById("detail-empty");
  const detail = document.getElementById("detail-view");

  if (state.data.games.length === 0 || filteredGames.length === 0) {
    empty.classList.remove("hidden");
    detail.classList.add("hidden");
    empty.textContent = state.data.games.length === 0
      ? "No exported installs available yet. Run python3 main.py export-mock-ui-data after discovery to populate the GUI."
      : "No visible titles match the current search.";
    return;
  }

  const game = getSelectedGame() || filteredGames[0];
  state.selectedGameId = game.id;
  const view = getSelectedView(game);
  ensureGameUiState(game, view);

  empty.classList.add("hidden");
  detail.classList.remove("hidden");

  document.getElementById("game-name").textContent = game.name;
  document.getElementById("game-meta").textContent =
    `${titleCase(game.launcher)} • ${game.runtime} • ${formatAssessment(view.launch_plan.anti_cheat_assessment)}`;

  const statusBadge = document.getElementById("status-badge");
  statusBadge.textContent = view.launch_plan.compatibility_status;
  statusBadge.className = `badge ${statusClass(view.launch_plan.compatibility_status)}`;

  const releaseBadge = document.getElementById("release-badge");
  releaseBadge.textContent = formatSupport(game.release_support);

  renderMetaStrip(game, view);
  renderPayloadOptions(game);
  renderRunnerOptions(game, view);
  renderRuntimeOptions(game);
  renderLaunchPreview(game, view);
  renderSafety(game, view);
  renderWarnings(view);
  renderPolicyReasons(view);
  renderRollbacks(game);
}

function initialize(data) {
  state.data = data;
  state.selectedProfile = data.default_profile || data.profiles[0] || null;
  state.selectedGameId = data.games[0]?.id || null;

  document.getElementById("search-input").addEventListener("input", (event) => {
    setSearch(event.target.value);
  });
  document.getElementById("profile-select").addEventListener("change", (event) => {
    setSelectedProfile(event.target.value);
  });

  renderSidebar();
  renderProfileSelect();
  renderLibrary();
  renderDetail();
}

loadData()
  .then(initialize)
  .catch((error) => {
    const empty = document.getElementById("detail-empty");
    empty.classList.remove("hidden");
    empty.textContent = `Failed to load GUI data: ${error}`;
  });
