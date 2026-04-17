async function loadData() {
  if (window.MOCK_LIBRARY_DATA) {
    return window.MOCK_LIBRARY_DATA;
  }
  const response = await fetch("./mock-library.json");
  return response.json();
}

const state = {
  data: null,
  selectedGameId: null,
  selectedProfile: null,
};

function statusClass(status) {
  return `status-${status}`;
}

function formatJson(value) {
  return JSON.stringify(value, null, 2);
}

function getSelectedGame() {
  return state.data.games.find((game) => game.id === state.selectedGameId);
}

function getSelectedView(game) {
  return game.profiles[state.selectedProfile] || game.profiles[game.default_profile];
}

function setSelectedGame(gameId) {
  state.selectedGameId = gameId;
  syncFormControls();
  renderLibrary();
  renderDetail();
}

function setSelectedProfile(profileName) {
  state.selectedProfile = profileName;
  syncFormControls();
  renderLibrary();
  renderDetail();
}

function syncFormControls() {
  const gameSelect = document.getElementById("game-select");
  const profileSelect = document.getElementById("profile-select");
  if (state.selectedGameId && gameSelect.value !== state.selectedGameId) {
    gameSelect.value = state.selectedGameId;
  }
  if (state.selectedProfile && profileSelect.value !== state.selectedProfile) {
    profileSelect.value = state.selectedProfile;
  }
}

function renderCapabilities() {
  const summary = {
    generated_at: state.data.generated_at,
    steam_available: state.data.capabilities.steam_available,
    vulkan_available: state.data.capabilities.vulkan_available,
    nvidia_driver_present: state.data.capabilities.nvidia_driver_present,
    smooth_motion_supported: state.data.capabilities.smooth_motion_supported,
    steam_path: state.data.capabilities.steam_path,
    vulkaninfo_path: state.data.capabilities.vulkaninfo_path,
    nvidia_smi_path: state.data.capabilities.nvidia_smi_path,
  };
  document.getElementById("capabilities-summary").textContent = formatJson(summary);
}

function renderSelectors() {
  const gameSelect = document.getElementById("game-select");
  const profileSelect = document.getElementById("profile-select");

  gameSelect.innerHTML = "";
  state.data.games.forEach((game) => {
    const option = document.createElement("option");
    option.value = game.id;
    option.textContent = game.name;
    gameSelect.appendChild(option);
  });

  profileSelect.innerHTML = "";
  state.data.profiles.forEach((profile) => {
    const option = document.createElement("option");
    option.value = profile;
    option.textContent = profile;
    profileSelect.appendChild(option);
  });

  gameSelect.addEventListener("change", (event) => setSelectedGame(event.target.value));
  profileSelect.addEventListener("change", (event) => setSelectedProfile(event.target.value));
  syncFormControls();
}

function renderLibrary() {
  const root = document.getElementById("library");
  root.innerHTML = "";

  state.data.games.forEach((game) => {
    const view = getSelectedView(game);
    const plan = view.launch_plan;

    const button = document.createElement("button");
    button.className = `library-item ${game.id === state.selectedGameId ? "is-active" : ""}`.trim();
    button.innerHTML = `
      <strong>${game.name}</strong>
      <div class="subtle">${game.launcher} • ${game.runtime}</div>
      <div class="subtle">profile: ${state.selectedProfile}</div>
      <div class="subtle">status: ${plan.compatibility_status}</div>
    `;
    button.addEventListener("click", () => setSelectedGame(game.id));
    root.appendChild(button);
  });
}

function renderDetail() {
  const game = getSelectedGame();
  if (!game) {
    return;
  }

  const view = getSelectedView(game);
  const plan = view.launch_plan;
  const policy = view.policy_report;

  document.getElementById("detail-empty").classList.add("hidden");
  document.getElementById("detail").classList.remove("hidden");
  document.getElementById("game-name").textContent = game.name;
  document.getElementById("game-meta").textContent =
    `${game.launcher} • ${game.runtime} • profile=${state.selectedProfile}`;

  const badge = document.getElementById("status-badge");
  badge.textContent = plan.compatibility_status;
  badge.className = `badge ${statusClass(plan.compatibility_status)}`;

  document.getElementById("game-summary").textContent = formatJson({
    library_summary: game.library_summary,
    override_mode: game.override_mode,
    supports_dlss_override: game.supports_dlss_override,
    supports_dlss_version_selection: game.supports_dlss_version_selection,
    notes: game.notes,
  });
  document.getElementById("profile-settings").textContent = formatJson(view.profile_config);
  document.getElementById("effective-profile").textContent = formatJson(view.effective_profile_config);
  document.getElementById("override-config").textContent = formatJson(game.override_config);
  document.getElementById("anti-cheat").textContent = formatJson(plan.anti_cheat_assessment);
  document.getElementById("features").textContent = formatJson(plan.requested_features);
  document.getElementById("policy-reasons").textContent = formatJson(plan.policy_reasons);
  document.getElementById("warnings").textContent = formatJson(plan.warnings);
  document.getElementById("blocked").textContent = formatJson(plan.blocked_reasons);
  document.getElementById("actions").textContent = formatJson({
    safe_actions: policy.anti_cheat.safe_actions,
    blocked_actions: policy.anti_cheat.blocked_actions,
  });
  document.getElementById("preview").textContent = formatJson({
    command_preview: plan.command_preview,
    env: plan.env,
    wrappers: plan.wrappers,
    args: plan.args,
    dlss_version_selection: plan.dlss_version_selection,
    notes: plan.notes,
  });
  document.getElementById("mutation-plan").textContent = formatJson(plan.mutation_plan);
  document.getElementById("cli-commands").textContent = formatJson(game.cli_commands);
  document.getElementById("rollbacks").textContent = formatJson(
    state.data.rollbacks.filter((entry) => entry.install_id === game.id)
  );
  document.getElementById("policy-report").textContent = formatJson(policy);
}

function initialize(data) {
  state.data = data;
  state.selectedProfile = data.default_profile || data.profiles[0];
  state.selectedGameId = data.games[0]?.id || null;

  renderCapabilities();
  renderSelectors();
  renderLibrary();
  if (state.selectedGameId && state.selectedProfile) {
    renderDetail();
  }
}

loadData()
  .then(initialize)
  .catch((error) => {
    document.getElementById("detail-empty").textContent = `Failed to load mock data: ${error}`;
  });
