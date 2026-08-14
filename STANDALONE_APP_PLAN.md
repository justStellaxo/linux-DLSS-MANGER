# DLLS Manager → Standalone Desktop App: Implementationsplan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Replace the FastAPI web UI and mock UI with a native PySide6 (Qt6) standalone desktop application. Update the DLSS catalog and domain logic to reflect the 2026 DLSS landscape (DLSS 310.7.0, separate SR/RR/FG DLLs, preset overrides, Frame Generation on Linux).

**Architecture:** The existing Python domain layer (discovery, policy, mutations, rollback, catalog) stays intact as a library. A new PySide6 GUI layer calls directly into the domain functions — no HTTP server, no browser, no FastAPI. The CLI remains as a thin alternative interface. Packaging via Flatpak + AppImage.

**Tech Stack:** Python 3.11+, PySide6 (Qt6 LGPL), existing domain layer, PyInstaller (AppImage bundling), Flatpak (Flathub-ready)

---

## Teil 0: Internet-Sweep Erkenntnisse (August 2026)

### 0.1 DLSS Versionen — was sich geändert hat

| Was | Repo-Stand (Jan 2026) | Realität (Aug 2026) |
|-----|----------------------|---------------------|
| Neueste DLSS SDK | 310.5.3 | **310.7.0** ( Released Juli 2026) |
| DLL-Struktur | Nur `nvngx_dlss.dll` (Super Resolution) | **3 separate DLLs**: `nvngx_dlss.dll` (SR), `nvngx_dlssd.dll` (Ray Reconstruction), `nvngx_dlssg.dll` (Frame Generation) |
| DLSS Presets | Nicht implementiert | Presets J, K, L, M (DLSS 4/4.5 Transformer-Modelle), steuerbar via `DXVK_NVAPI_DRS_*` Env-Vars |
| DLSS 4.5 | Unbekannt | SDK 310.6.0 = DLSS 4.5 (Transformer-Modelle L/M) |
| Streamline SDK | Nicht referenziert | Streamline 2.12.0 (Reflex, DirectSR, NIS) |

### 0.2 Linux DLSS/Proton Landscape — was sich geändert hat

**Frame Generation funktioniert jetzt auf Linux:**
- Proton Experimental + DXVK-NVAPI unterstützen DLSS Frame Generation
- Benötigt: `PROTON_ENABLE_NVAPI=1`, `WINEHAGS=1` (Hardware-accelerated GPU scheduling)
- Optional: `WINE_DISABLE_HARDWARE_SCHEDULING=0` (falls FG deaktiviert wurde)

**Wichtige Environment Variables (2026 Stand):**
```
# Basis DLSS
PROTON_ENABLE_NVAPI=1
PROTON_DLSS_UPGRADE=1                          # oder ="310.7" für spezifische Version
PROTON_ENABLE_NGX_UPDATER=1                     # NGX DLL Auto-Update

# DLSS Preset Overrides (DXVK-NVAPI DRS)
DXVK_NVAPI_DRS_SETTINGS=NGX_DLSS_SR_OVERRIDE=on,NGX_DLSS_RR_OVERRIDE=on,NGX_DLSS_FG_OVERRIDE=on,NGX_DLSS_SR_OVERRIDE_RENDER_PRESET_SELECTION=render_preset_latest,NGX_DLSS_RR_OVERRIDE_RENDER_PRESET_SELECTION=render_preset_latest

# Frame Generation
DXVK_NVAPI_DRS_NGX_DLSS_FG_OVERRIDE=on

# NVIDIA Reflex
DXVK_NVAPI_VKREFLEX=1

# Smooth Motion (für Games ohne FG-Support)
NVPRESENT_ENABLE_SMOOTH_MOTION=1

# DLSS Indicator (Debug)
DXVK_NVAPI_SET_NGX_DEBUG_OPTIONS=DLSSIndicator=1024,DLSSGIndicator=2
```

**Proton-Varianten mit erweitertem DLSS-Support:**
- GE-Proton 10-26+ (PROTON_DLSS_UPGRADE mit Versionierung)
- Proton-CachyOS (PROTON_DLSS_UPGRADE, auto DLL download)
- Proton-EM

### 0.3 Konkurrenz/Referenz-Projekte

| Projekt | Sprache/UI | Stars | Linux | Beschreibung |
|---------|-----------|-------|-------|-------------|
| **DLSS Updater** (Recol) | Python + Flet (Flutter) | 1.1k | Ja (Flatpak) | v4.6.3. Scannt alle Launcher, swappt DLSS/RR/FG/FSR/XeSS DLLs. Proton Upscalers Panel mit Env-Var-Generierung. Sein Hauptfeature: DLL-Swapping + Env-Var-Builder. |
| **Proton Forge** (theinvisible) | C++ / Qt6 | 29 | Ja (Flatpak+AppImage) | Sehr neu (Aug 2026). Qt6-native, Steam+GOG, DLSS SR/RR/FG Konfig, HDR, Proton-Management, MangoHud-Editor. Der direkteste Vergleich zu unserem Ziel. |
| **DLSS Swapper** (beeradmoore) | C# / .NET | — | Nein | Windows-only, Issue #104 offen seit Jahren. Kein Linux-Support geplant. |

### 0.4 GUI-Framework Entscheidung: PySide6

**Warum PySide6 (Qt6 for Python):**
- Native Linux-Desktop-Integration (KDE/GNOME, Wayland, X11)
- LGPL-Lizenz (kein Commercial-License-Problem wie PyQt6)
- Python-Binding → existing domain layer direkt nutzbar
- Proton Forge beweist: Qt6 ist der richtige Stack für genau dieses Problem
- PyInstaller + Flatpak (PySide6 BaseApp auf Flathub) gut dokumentiert
- Bessere Performance und native Feel als Flet (Flutter-basiert)
- Qt Designer für UI-Layouts verfügbar

**Warum nicht Flet (wie DLSS Updater):**
- Flutter-basiert → nicht-nativer Look auf Linux
- Bundled Flutter Engine → größere Binary
- DLSS Updater nutzt es, aber Proton Forge (das neuere, fokussiertere Projekt) nutzt Qt6

**Warum nicht Tauri/Electron:**
- User will "keine webui" → WebView-basierte Frameworks sind verkleidete WebUIs
- Zusätzliche Node.js/Rust Toolchain-Abhängigkeit

---

## Teil 1: WebUI entfernen, Domain-Layer bereinigen

### Task 1: FastAPI/WebUI-Abhängigkeiten aus pyproject.toml entfernen

**Objective:** FastAPI, uvicorn, playwright als dependencies streichen; PySide6 hinzufügen

**Files:**
- Modify: `pyproject.toml`

**Steps:**

1. Ersetze die `dependencies` Sektion:
```toml
dependencies = [
  "PySide6>=6.8,<7",
]
```

2. Ersetze die `dev` dependencies:
```toml
[project.optional-dependencies]
dev = [
  "pytest>=8.3,<9",
  "pytest-qt>=4.4,<5",
]
```

3. Entferne die `package-data` Sektion für `webapp.static`

4. Entferne den `mock_ui` exclude aus `[tool.ruff]`

5. Run: `pip install -e ".[dev]"` — expected: PySide6 installiert, fastapi/uvicorn nicht mehr als deps

**Commit:** `refactor: replace web dependencies with PySide6`

---

### Task 2: webapp/ Package löschen

**Objective:** Gesamte FastAPI-WebUI entfernen

**Files:**
- Delete: `dlls_manager/webapp/` (komplettes Verzeichnis: app.py, schemas.py, jobs.py, __main__.py, __init__.py, static/)

**Steps:**

1. `rm -rf dlls_manager/webapp/`

2. Entferne aus `dlls_manager/cli.py`:
   - Den Import `from dlls_manager.webapp.app import run_server` (Zeile 148)
   - Die Funktion `cmd_serve_ui` (Zeilen 147-150)
   - Den `serve-ui` subparser (Zeilen 301-304)

3. Run: `python3 -c "import dlls_manager.cli"` — expected: kein ImportError

**Commit:** `refactor: remove FastAPI webapp package`

---

### Task 3: mock_ui/ und web_jobs/ entfernen

**Objective:** Alle WebUI-bezogenen Artefakte löschen

**Files:**
- Delete: `mock_ui/` (Verzeichnis)
- Delete: `web_jobs/` (Verzeichnis)
- Delete: `dlls_manager/mock_data.py`
- Modify: `dlls_manager/cli.py` — entferne `cmd_export_mock_ui_data` und `export-mock-ui-data` subparser
- Modify: `dlls_manager/paths.py` — entferne `MOCK_UI_*`, `WEB_JOBS_DIR` Konstanten

**Steps:**

1. `rm -rf mock_ui/ web_jobs/`

2. Aus `cli.py` entfernen:
   - Imports: `from dlls_manager.mock_data import build_mock_ui_script, export_mock_ui_export_mock_library`
   - Imports: `from dlls_manager.paths import MOCK_UI_DATA_FILE, MOCK_UI_SCRIPT_FILE`
   - Funktion `cmd_export_mock_ui_data` (Zeilen 111-120)
   - Subparser `export-mock-ui-data` (Zeilen 277-284)

3. Aus `paths.py` entfernen:
   - `WEB_JOBS_DIR_NAME`, `WEB_JOBS_DIR`
   - `MOCK_UI_DIR`, `MOCK_UI_DATA_FILE`, `MOCK_UI_SCRIPT_FILE`

4. Run: `python3 -c "from dlls_manager.cli import build_parser; build_parser()"` — expected: OK

**Commit:** `refactor: remove mock UI and web jobs artifacts`

---

### Task 4: E2E Playwright-Tests entfernen, CLI-Tests behalten

**Objective:** tests_e2e/ (Playwright) löschen, da keine WebUI mehr existiert

**Files:**
- Delete: `tests_e2e/` (komplettes Verzeichnis)
- Modify: `pyproject.toml` — entferne `playwright` aus dev deps (bereits in Task 1 erledigt)

**Steps:**

1. `rm -rf tests_e2e/`

2. Run: `python3 -m pytest tests/ -v --co` — expected: alle unit tests collected, keine e2e

**Commit:** `test: remove playwright E2E tests (webUI gone)`

---

### Task 5: Webapp-Referenzen aus README und Plan-Docs entfernen

**Objective:** README aktualisieren — webUI/serve-ui/mock-ui Abschnitte raus

**Files:**
- Modify: `README.md` — entferne "Real UI", "Legacy Mock UI", "serve-ui" Abschnitte
- Delete: `REAL_UI_AND_PLAYWRIGHT_PLAN.md` (falls vorhanden)
- Modify: `TEST_MATRIX.md` (falls vorhanden) — entferne E2E/Playwright Referenzen

**Commit:** `docs: remove webUI references from README`

---

## Teil 2: DLSS Domain-Layer auf 2026 Stand bringen

### Task 6: dlss_catalog.py — Separate DLL-Extraktion (SR, RR, FG)

**Objective:** Nicht nur `nvngx_dlss.dll` extrahieren, sondern auch `nvngx_dlssd.dll` (RR) und `nvngx_dlssg.dll` (FG)

**Files:**
- Modify: `dlls_manager/dlss_catalog.py`

**Steps:**

1. Schreibe Test in `tests/test_dlss_catalog.py`:
```python
def test_extract_all_dlss_dlls_from_zip(tmp_path):
    # Erstelle Test-ZIP mit nvngx_dlss.dll, nvngx_dlssd.dll, nvngx_dlssg.dll
    # Rufe extract_all_dlss_dlls auf
    # Assert: alle 3 DLLs im target_dir vorhanden
```

2. Run test → expected: FAIL (Funktion existiert nicht)

3. Implementiere `extract_all_dlss_dlls(zip_path, target_dir)`:
```python
DLSS_DLL_NAMES = {
    "nvngx_dlss.dll",   # Super Resolution
    "nvngx_dlssd.dll",  # Ray Reconstruction
    "nvngx_dlssg.dll",  # Frame Generation
}

def extract_all_dlss_dlls_from_zip(zip_path: Path, target_dir: Path) -> list[str]:
    """Extract all DLSS DLL variants from the SDK ZIP."""
    extracted = []
    with zipfile.ZipFile(zip_path) as archive:
        for dll_name in DLSS_DLL_NAMES:
            matching = [n for n in archive.namelist() if n.lower().endswith(f"/{dll_name}")]
            if not matching:
                continue
            target = target_dir / dll_name
            ensure_directory(target_dir)
            with archive.open(matching[0]) as src, NamedTemporaryFile(dir=target_dir, delete=False) as tmp:
                shutil.copyfileobj(src, tmp)
                Path(tmp.name).replace(target)
            extracted.append(dll_name)
    return extracted
```

4. Aktualisiere `download_dlss_version()` um alle 3 DLLs zu extrahieren

5. Run test → expected: PASS

**Commit:** `feat: extract SR, RR, and FG DLLs from DLSS SDK ZIPs`

---

### Task 7: DlssVersionRecord um FG/RR-Metadaten erweitern

**Objective:** Model erweitern um `has_rr_dll`, `has_fg_dll`, `fg_runtime_path`, `rr_runtime_path`

**Files:**
- Modify: `dlls_manager/models.py` — `DlssVersionRecord` TypedDict erweitern
- Modify: `dlls_manager/dlss_catalog.py` — `_with_local_state()` um RR/FG-Checks erweitern

**Steps:**

1. Erweitere `DlssVersionRecord` in models.py:
```python
class DlssVersionRecord(TypedDict):
    # ... existing fields ...
    rr_runtime_path: NotRequired[str]
    fg_runtime_path: NotRequired[str]
    has_rr_dll: NotRequired[bool]
    has_fg_dll: NotRequired[bool]
```

2. Aktualisiere `_with_local_state()` in dlss_catalog.py:
```python
runtime_dir = DLSS_RUNTIME_DIR / entry["id"]
sr_path = runtime_dir / "nvngx_dlss.dll"
rr_path = runtime_dir / "nvngx_dlssd.dll"
fg_path = runtime_dir / "nvngx_dlssg.dll"
enriched["runtime_path"] = str(sr_path)
enriched["downloaded"] = sr_path.exists()
enriched["rr_runtime_path"] = str(rr_path)
enriched["has_rr_dll"] = rr_path.exists()
enriched["fg_runtime_path"] = str(fg_path)
enriched["has_fg_dll"] = fg_path.exists()
```

3. Run: `python3 -m pytest tests/test_dlss_catalog.py -v` — expected: PASS (bzw. bestehende Tests + neue)

**Commit:** `feat: track RR and FG DLL availability in catalog entries`

---

### Task 8: DLSS Preset-Override Support im Domain-Layer

**Objective:** Neue Profile-Felder für DLSS SR/RR/FG Preset-Overrides (render_preset_j/k/l/m/latest)

**Files:**
- Modify: `dlls_manager/models.py` — `Profile` TypedDict erweitern
- Modify: `dlls_manager/profile_db.py` — Validation + Defaults
- Modify: `dlls_manager/launch_plan.py` — Env-Vars generieren
- Modify: `profiles/default.json`, `profiles/safe.json`, `profiles/experimental.json`

**Steps:**

1. Erweitere `Profile` in models.py:
```python
class Profile(TypedDict):
    # ... existing ...
    dlss_sr_preset: str | None       # "latest", "j", "k", "l", "m", None
    dlss_rr_preset: str | None       # same options
    dlss_fg_override: str | None     # "on", "off", None
    enable_ngx_updater: bool         # PROTON_ENABLE_NGX_UPDATER
    enable_hags: bool                # WINEHAGS=1
    enable_vkreflex: bool            # DXVK_NVAPI_VKREFLEX
```

2. Aktualisiere `validate_profile()` in profile_db.py mit Defaults für neue Felder

3. Aktualisiere `build_profile_env_and_wrappers()` in launch_plan.py:
```python
if profile.get("enable_ngx_updater"):
    env["PROTON_ENABLE_NGX_UPDATER"] = "1"
if profile.get("enable_hags"):
    env["WINEHAGS"] = "1"
if profile.get("enable_vkreflex"):
    env["DXVK_NVAPI_VKREFLEX"] = "1"

# DRS Settings String bauen
drs_parts = []
if profile.get("dlss_sr_preset"):
    drs_parts.append("NGX_DLSS_SR_OVERRIDE=on")
    drs_parts.append(f"NGX_DLSS_SR_OVERRIDE_RENDER_PRESET_SELECTION=render_preset_{profile['dlss_sr_preset']}")
if profile.get("dlss_rr_preset"):
    drs_parts.append("NGX_DLSS_RR_OVERRIDE=on")
    drs_parts.append(f"NGX_DLSS_RR_OVERRIDE_RENDER_PRESET_SELECTION=render_preset_{profile['dlss_rr_preset']}")
if profile.get("dlss_fg_override"):
    drs_parts.append(f"NGX_DLSS_FG_OVERRIDE={profile['dlss_fg_override']}")
if drs_parts:
    env["DXVK_NVAPI_DRS_SETTINGS"] = ",".join(drs_parts)
```

4. Schreibe Test für neue Preset-Env-Var-Generierung

5. Run test → expected: PASS

**Commit:** `feat: add DLSS SR/RR/FG preset override support`

---

### Task 9: PROTON_DLSS_UPGRADE Env-Var Support

**Objective:** `PROTON_DLSS_UPGRADE=1` oder `PROTON_DLSS_UPGRADE="310.7"` als Profile-Option

**Files:**
- Modify: `dlls_manager/models.py` — `Profile` um `proton_dlss_upgrade` Feld erweitern
- Modify: `dlls_manager/profile_db.py`
- Modify: `dlls_manager/launch_plan.py`

**Steps:**

1. `Profile` erweitern: `proton_dlss_upgrade: str | None  # "1", "310.7", None`

2. In `build_profile_env_and_wrappers()`:
```python
upgrade = profile.get("proton_dlss_upgrade")
if upgrade:
    env["PROTON_DLSS_UPGRADE"] = upgrade
```

3. Profile-Default: `None` (off)

4. Test schreiben + run

**Commit:** `feat: add PROTON_DLSS_UPGRADE env var support`

---

### Task 10: dlss_versions.json auf 310.7.0 aktualisieren

**Objective:** Catalog auf aktuellen Stand bringen

**Files:**
- Modify: `dlss_versions.json` — manuell oder via `refresh-dlss-catalog` CLI

**Steps:**

1. Run: `python3 main.py refresh-dlss-catalog`
2. Verify: `python3 main.py list-dlss-catalog` — 310.7.0 sollte neueste sein
3. Falls GitHub API Rate-Limit: manuell Eintrag für 310.7.0 hinzufügen
4. Test: `python3 -m pytest tests/test_dlss_catalog.py -v`

**Commit:** `chore: refresh DLSS catalog to 310.7.0`

---

## Teil 3: PySide6 GUI aufbauen

### Task 11: GUI Package-Struktur erstellen

**Objective:** Grundgerüst für `dlls_manager/gui/`

**Files:**
- Create: `dlls_manager/gui/__init__.py`
- Create: `dlls_manager/gui/main_window.py`
- Create: `dlls_manager/gui/pages/` (library.py, catalog.py, profiles.py, rollbacks.py, system.py)
- Create: `dlls_manager/gui/widgets/` (game_card.py, env_var_preview.py, preset_selector.py)
- Create: `dlls_manager/gui/styles.py` (Dark Theme, Steam-inspiriert)

**Steps:**

1. Verzeichnisstruktur + leere `__init__.py` Files erstellen

2. Minimaler `main_window.py`:
```python
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QDockWidget
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DLSS Manager")
        self.setMinimumSize(1200, 800)
        # Sidebar + Stacked Pages
```

3. Run: `python3 -c "from dlls_manager.gui.main_window import MainWindow"` — expected: OK (kein Crash)

**Commit:** `feat: create PySide6 GUI package structure`

---

### Task 12: Entry Point `dlls-manager-gui`

**Objective:** Neuen CLI-Entry-Point für die GUI

**Files:**
- Modify: `pyproject.toml` — `project.scripts` erweitern
- Create: `dlls_manager/gui/__main__.py`

**Steps:**

1. In pyproject.toml:
```toml
[project.scripts]
dlls-manager = "dlls_manager.cli:main"
dlls-manager-gui = "dlls_manager.gui.__main__:main"
```

2. `dlls_manager/gui/__main__.py`:
```python
import sys
from PySide6.QtWidgets import QApplication
from dlls_manager.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DLSS Manager")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

3. Run: `pip install -e . && dlls-manager-gui` — expected: Fenster öffnet sich

**Commit:** `feat: add dlls-manager-gui entry point`

---

### Task 13: Sidebar-Navigation (Steam-inspiriert)

**Objective:** Linke Sidebar mit Icons + Labels für Library, Catalog, Profiles, Rollbacks, System

**Files:**
- Create: `dlls_manager/gui/sidebar.py`
- Modify: `dlls_manager/gui/main_window.py`

**Steps:**

1. `sidebar.py` — `QListWidget` mit 5 Einträgen:
   - Library (Spiele/Installs)
   - Catalog (DLSS Versionen)
   - Profiles (Profile)
   - Rollbacks (Rollback-Verwaltung)
   - System (System-Info)

2. `MainWindow` verdrahten: Sidebar-Auswahl → `QStackedWidget` Seitenwechsel

3. Test: `pytest tests/test_gui_sidebar.py` (pytest-qt: Sidebar hat 5 Items)

**Commit:** `feat: add sidebar navigation`

---

### Task 14: Library Page — Spiele-Liste mit Game-Cards

**Objective:** Installierte Spiele als Karten anzeigen (Name, Launcher, Runtime, Status-Badge)

**Files:**
- Create: `dlls_manager/gui/pages/library.py`
- Create: `dlls_manager/gui/widgets/game_card.py`
- Modify: `dlls_manager/gui/main_window.py`

**Steps:**

1. `game_card.py` — `QFrame` mit:
   - Game-Name (fett)
   - Launcher-Icon + Runtime
   - Anti-Cheat Status Badge (grün/gelb/rot)
   - DLSS-Support Badge
   - Release-Support Badge

2. `library.py` — `QScrollArea` mit `QVBoxLayout` von Game-Cards:
   - Ruft `list_installs_summary()` auf
   - "Refresh" Button → `discover_and_cache_installs()` im Thread

3. Search-Bar zum Filtern der Karten

4. Test: `pytest tests/test_gui_library.py` — 2 Mock-Installs → 2 Cards gerendert

**Commit:** `feat: add library page with game cards`

---

### Task 15: Library Page — Detail-Panel pro Install

**Objective:** Rechtsseite der Library zeigt Details + Actions für ausgewähltes Spiel

**Files:**
- Modify: `dlls_manager/gui/pages/library.py`
- Create: `dlls_manager/gui/widgets/detail_panel.py`
- Create: `dlls_manager/gui/widgets/env_var_preview.py`

**Steps:**

1. `detail_panel.py` zeigt:
   - Install-Metadaten (source, launcher, store, runtime, prefix_path)
   - Validation-Errors/Warnings (falls vorhanden)
   - Anti-Cheat Assessment
   - Command Preview (read-only `QPlainTextEdit`)
   - Action Buttons: Validate, Explain Policy, Prepare, Dry-Run, Apply, Launch

2. `env_var_preview.py` — Live-Preview der generierten Env-Vars:
   - Zeigt `PROTON_ENABLE_NVAPI=1`, `DXVK_NVAPI_DRS_SETTINGS=...`, etc.
   - "Copy to Clipboard" Button (für Steam Launch Options)
   - "Write to Steam" Button (für `sync_to_launcher`)

3. Actions rufen direkt die Domain-Funktionen auf:
   - `validate_install(install_id)`
   - `explain_install_policy(install_id, profile)`
   - `prepare_launch(install_id, profile)`
   - `launch_install(install_id, profile, dry_run=True/False)`

4. Async Ausführung via `QThread` (damit UI nicht blockiert)

5. Test: `pytest tests/test_gui_detail.py`

**Commit:** `feat: add install detail panel with actions and env-var preview`

---

### Task 16: Override Editor im Detail-Panel

**Objective:** Per-Install Override-Editor direkt im Detail-Panel

**Files:**
- Modify: `dlls_manager/gui/widgets/detail_panel.py`

**Steps:**

1. Form-Fields für `InstallOverride`:
   - DLSS Version Dropdown (aus Catalog)
   - DLSS Target Path (Text Input)
   - Launch Args (Text Input)
   - Toggle: MangoHud, GameMode, NVAPI, Smooth Motion, Unsupported Override, Sync to Launcher
   - Extra Env (Textarea, KEY=value)
   - Extra Wrappers (Text Input, comma-separated)

2. "Save" Button → `apply_install_override_updates(install_id, updates)`

3. "Safe Launch" Button → Override speichern + Launch mit `dry_run=True`

4. Test: `pytest tests/test_gui_override_editor.py`

**Commit:** `feat: add per-install override editor in detail panel`

---

### Task 17: Catalog Page — DLSS Versionen verwalten

**Objective:** DLSS Catalog als Tabelle: Version, Datum, SR/RR/FG verfügbar, Downloaded, Download-Button

**Files:**
- Create: `dlls_manager/gui/pages/catalog.py`
- Modify: `dlls_manager/gui/main_window.py`

**Steps:**

1. `QTableWidget` mit Spalten:
   - Version (z.B. "310.7.0")
   - Label
   - Published At
   - SR DLL (✓/✗)
   - RR DLL (✓/✗)
   - FG DLL (✓/✗)
   - Downloaded (✓/✗)
   - Action: Download / Redownload

2. "Refresh Catalog" Button → `refresh_dlss_catalog()` im `QThread`

3. Download-Button → `download_dlss_version(version_id)` im `QThread` mit Progress-Callback

4. Test: `pytest tests/test_gui_catalog.py`

**Commit:** `feat: add DLSS catalog page with download management`

---

### Task 18: Profiles Page — Profile bearbeiten

**Objective:** Profile-Editor mit allen Feldern inkl. neuer DLSS-Preset-Optionen

**Files:**
- Create: `dlls_manager/gui/pages/profiles.py`
- Modify: `dlls_manager/gui/main_window.py`

**Steps:**

1. Linken Seite: Liste der Profile (default, safe, experimental)
2. Rechte Seite: Form für ausgewähltes Profile:
   - Toggles: Enable NVAPI, Smooth Motion, GameMode, MangoHud, NGX Updater, HAGS, VKReflex
   - DLSS Version Dropdown
   - DLSS SR Preset Dropdown (Latest, J, K, L, M, None)
   - DLSS RR Preset Dropdown (Latest, J, K, L, M, None)
   - DLSS FG Override Dropdown (On, Off, None)
   - PROTON_DLSS_UPGRADE Input (z.B. "1" oder "310.7" oder leer)
   - Safety Mode Dropdown (strict, balanced, unsafe)
   - Launch Args (Text Input)
   - Custom Env (Textarea, KEY=value)
3. "Save" Button → `apply_profile_updates(profile_name, updates)`

4. Test: `pytest tests/test_gui_profiles.py`

**Commit:** `feat: add profiles page with DLSS preset configuration`

---

### Task 19: Rollbacks Page

**Objective:** Rollback-Verwaltung: Liste + Detail + Execute

**Files:**
- Create: `dlls_manager/gui/pages/rollbacks.py`

**Steps:**

1. `QTableWidget`: Rollback ID, Install ID, Profile, Created At, Files, Status, Action
2. Detail-Panel bei Auswahl: `load_rollback_record(id)` → zeigt betroffene Files
3. "Restore" Button → `rollback_mutation(id)` mit Bestätigungs-Dialog
4. Test: `pytest tests/test_gui_rollbacks.py`

**Commit:** `feat: add rollbacks page`

---

### Task 20: System Page

**Objective:** System-Info + Capability-Detection

**Files:**
- Create: `dlls_manager/gui/pages/system.py`

**Steps:**

1. `detect_capabilities()` aufrufen und formatiert anzeigen:
   - OS, Python Version
   - NVIDIA GPU + Driver
   - Vulkan Info
   - Steam, MangoHud, GameMode, Gamescope Verfügbarkeit
   - Smooth Motion Support
2. "Re-detect" Button
3. Test: `pytest tests/test_gui_system.py`

**Commit:** `feat: add system info page`

---

### Task 21: Dark Theme (Steam-inspiriert)

**Objective:** Konsistentes Dark Theme für die ganze App

**Files:**
- Create: `dlls_manager/gui/styles.py`
- Modify: `dlls_manager/gui/__main__.py`

**Steps:**

1. QSS (Qt Style Sheet) definieren:
   - Dunkles Farbschema (#1b2838, #171a21, #2a475e — Steam-Palette)
   - Buttons, Scrollbars, Table-Headers, Inputs
   - Status-Badges (grün/gelb/rot)

2. In `__main__.py`: `app.setStyleSheet(DARK_THEME)`

3. Test: visuelle Inspektion (kein automatisierter Test nötig)

**Commit:** `feat: apply Steam-inspired dark theme`

---

### Task 22: Async Job-Runner (QThread-basiert)

**Objective:** Längerlaufende Operationen (Discovery, Download, Apply, Launch) ohne UI-Freeze

**Files:**
- Create: `dlls_manager/gui/workers.py`

**Steps:**

1. Generic `JobWorker(QThread)`:
```python
class JobWorker(QThread):
    progress = Signal(str)
    finished = Signal(object)  # result dict
    error = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

2. Alle Pages nutzen `JobWorker` für Blocking-Calls

3. Progress-Indicator (Spinner oder ProgressBar) während Jobs laufen

4. Test: `pytest tests/test_gui_workers.py`

**Commit:** `feat: add QThread-based async job runner`

---

## Teil 4: Packaging & Distribution

### Task 23: .desktop File und App-Icon

**Objective:** Linux-Desktop-Integration

**Files:**
- Create: `dlls_manager/gui/assets/dlss-manager.desktop`
- Create: `dlls_manager/gui/assets/icon.png` (oder SVG)
- Modify: `pyproject.toml` — package-data für GUI-Assets

**Steps:**

1. `.desktop` File:
```ini
[Desktop Entry]
Name=DLSS Manager
Comment=Manage DLSS versions and Proton launch options
Exec=dlls-manager-gui
Icon=dlss-manager
Terminal=false
Type=Application
Categories=Game;Utility;
```

2. In pyproject.toml package-data aufnehmen

**Commit:** `feat: add desktop file and app icon`

---

### Task 24: PyInstaller Spec für Standalone-Binary

**Objective:** Eine einzige Binary die alles enthält

**Files:**
- Create: `dlls-manager-gui.spec` (PyInstaller spec)

**Steps:**

1. Spec-File:
```python
# dlls-manager-gui.spec
a = Analysis(
    ['dlls_manager/gui/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('dlls_manager/gui/assets', 'dlls_manager/gui/assets'),
        ('profiles', 'profiles'),
        ('anti_cheat_rules.json', '.'),
        ('games.json', '.'),
    ],
    hiddenimports=['PySide6'],
    hookspath=['pyinstaller_hooks'],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name='DLSS-Manager', console=False)
```

2. Run: `pyinstaller dlls-manager-gui.spec` — expected: `dist/DLSS-Manager` Binary

3. Verify: `./dist/DLSS-Manager` öffnet die GUI

**Commit:** `build: add PyInstaller spec for standalone binary`

---

### Task 25: Flatpak Manifest

**Objective:** Flathub-ready Flatpak-Build

**Files:**
- Create: `flatpak/io.github.stella.dlls-manager.yml`
- Create: `flatpak/io.github.stella.dlls-manager.desktop`
- Create: `flatpak/io.github.stella.dlls-manager.appdata.xml`

**Steps:**

1. Flatpak-Manifest mit PySide6 BaseApp:
```yaml
app-id: io.github.stella.dlls-manager
runtime: org.kde.Platform
runtime-version: '6.8'
sdk: org.kde.Sdk
base: io.qt.PySide.BaseApp
base-version: '6.8'
command: dlls-manager-gui
modules:
  - name: dlls-manager
    buildsystem: simple
    build-commands:
      - pip install --no-index --find-links=. .
      - install -Dm644 io.github.stella.dlls-manager.desktop /app/share/applications/
      - install -Dm644 icon.png /app/share/icons/hicolor/256x256/apps/dlss-manager.png
    sources:
      - type: dir
        path: ..
```

2. Build-Test: `flatpak-builder --user --install flatpak_build flatpak/io.github.stella.dlls-manager.yml`

3. Run: `flatpak run io.github.stella.dlls-manager`

**Commit:** `build: add Flatpak manifest`

---

### Task 26: AppImage Build (optional, aber empfohlen)

**Objective:** AppImage als einfache Distribution ohne Flatpak-Setup

**Files:**
- Create: `packaging/appimage/build.sh`

**Steps:**

1. Build-Script:
```bash
#!/bin/bash
# 1. PyInstaller binary bauen
pyinstaller dlls-manager-gui.spec
# 2. AppImage erstellen
./appimagetool-x86_64.AppImage dist/DLSS-Manager DLSS-Manager-x86_64.AppImage
```

2. Test: AppImage bauen und ausführen

**Commit:** `build: add AppImage build script`

---

## Teil 5: Domain-Layer Verbesserungen (aus Internet-Sweep Erkenntnissen)

### Task 27: Steam Launch-Options Generator für DXVK_NVAPI_DRS_SETTINGS

**Objective:** Den bestehenden `build_steam_launch_options()` um die neuen DRS-Settings erweitern

**Files:**
- Modify: `dlls_manager/launcher_persistence.py`

**Steps:**

1. `build_steam_launch_options()` erweitern um:
   - `PROTON_ENABLE_NGX_UPDATER=1`
   - `WINEHAGS=1` (wenn FG aktiv)
   - `DXVK_NVAPI_VKREFLEX=1`
   - `DXVK_NVAPI_DRS_SETTINGS=...` (kompletter Preset-Override-String)

2. Test: `pytest tests/test_launcher_persistence.py` — verifiziere dass neue Env-Vars in Launch-Options-String auftauchen

**Commit:** `feat: extend Steam launch options with DRS settings and HAGS`

---

### Task 28: Proton-Version-Detection

**Objective:** Erkennen welches Proton ein Spiel nutzt (wie Proton Forge es macht)

**Files:**
- Modify: `dlls_manager/detector.py` — `detect_capabilities()` erweitern
- Create: `dlls_manager/proton_db.py` — Proton-Versionen scannen

**Steps:**

1. Scanne `~/.steam/steam/steamapps/common/` nach `Proton *` Verzeichnissen
2. Scanne `~/.local/share/Steam/compatibilitytools.d/` nach GE-Proton, Proton-CachyOS etc.
3. Pro Install: Lese `steamapps/compatdata/<appid>/config_info` für aktive Proton-Version
4. Zeige in GUI: welche Proton-Version läuft für dieses Spiel

5. Test: `pytest tests/test_proton_db.py`

**Commit:** `feat: detect installed Proton versions and per-game assignment`

---

### Task 29: Community Blacklist Integration

**Objective:** DLSS-Updater-Blacklist integrieren (wie DLSS Updater es macht)

**Files:**
- Create: `dlls_manager/blacklist.py`
- Create: `blacklist.json` (oder CSV-Import)

**Steps:**

1. Blacklist-Source: https://github.com/Recol/DLSS-Updater-Blacklist (CSV)
2. `load_blacklist()` — lädt CSV, cached lokal
3. `is_blacklisted(install_id)` — prüft ob Spiel auf Blacklist
4. In Policy-Evaluation: `blocked_reasons.append("Game is community-blacklisted for DLL swapping.")`
5. In GUI: Badge "Blacklisted" + Override-Möglichkeit

6. Test: `pytest tests/test_blacklist.py`

**Commit:** `feat: integrate community DLSS blacklist`

---

## Teil 6: Polish & Testing

### Task 30: GUI-Unit-Tests mit pytest-qt

**Objective:** Tests für alle GUI-Pages

**Files:**
- Create: `tests/test_gui_sidebar.py`
- Create: `tests/test_gui_library.py`
- Create: `tests/test_gui_catalog.py`
- Create: `tests/test_gui_profiles.py`
- Create: `tests/test_gui_rollbacks.py`
- Create: `tests/test_gui_system.py`
- Create: `tests/test_gui_workers.py`
- Create: `tests/conftest.py` — pytest-qt fixtures

**Steps:**

1. `conftest.py`:
```python
import pytest
from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="session")
def qapp():
    app = QApplication([])
    yield app
    app.quit()
```

2. Pro Page: Test dass Model-Daten korrekt gerendert werden, Buttons klickbar, Actions korrekte Domain-Funktionen aufrufen (mock)

3. Run: `python3 -m pytest tests/ -v` — expected: alle PASS

**Commit:** `test: add pytest-qt GUI unit tests`

---

### Task 31: README neu schreiben

**Objective:** README reflects standalone desktop app

**Files:**
- Modify: `README.md` — kompletter Rewrite

**Steps:**

1. Neue README:
   - "Standalone Desktop App" (keine WebUI erwähnen)
   - Screenshots (später hinzufügen)
   - Installation: `pip install`, Flatpak, AppImage
   - Features: Library, Catalog, Profiles, Rollbacks, System
   - CLI bleibt als Alternative

**Commit:** `docs: rewrite README for standalone desktop app`

---

## Zusammenfassung: Was raus, was rein

| Komponente | Aktuell | Ziel |
|-----------|---------|------|
| FastAPI webapp | `dlls_manager/webapp/` | **Gelöscht** |
| Mock UI | `mock_ui/` | **Gelöscht** |
| Web Jobs | `web_jobs/` | **Gelöscht** |
| Playwright E2E | `tests_e2e/` | **Gelöscht** |
| serve-ui CLI | `cmd_serve_ui` | **Gelöscht** |
| export-mock-ui-data | `cmd_export_mock_ui_data` | **Gelöscht** |
| PySide6 GUI | — | **Neu: `dlls_manager/gui/`** |
| dlls-manager-gui | — | **Neuer Entry-Point** |
| DLSS DLL Extraktion | Nur `nvngx_dlss.dll` | **SR + RR + FG DLLs** |
| DLSS Presets | — | **J/K/L/M via DRS Settings** |
| PROTON_DLSS_UPGRADE | — | **Profile-Option** |
| HAGS / VKReflex / NGX Updater | — | **Profile-Toggles** |
| Proton-Version-Detection | — | **Neu** |
| Community Blacklist | — | **Neu** |
| Flatpak | — | **Neu** |
| AppImage | — | **Neu** |
| Packaging | nur pip | **pip + Flatpak + AppImage** |

## Priorisierung

**Phase 1 (Kern):** Tasks 1-5 (WebUI entfernen) + Tasks 11-13 (GUI-Gerüst)
**Phase 2 (Features):** Tasks 6-10 (DLSS Domain Update) + Tasks 14-20 (GUI-Pages)
**Phase 3 (Polish):** Tasks 21-22 (Theme + Async) + Tasks 27-29 (Domain-Verbesserungen)
**Phase 4 (Distribution):** Tasks 23-26 (Packaging) + Tasks 30-31 (Tests + Docs)
**Phase 5 (Test-Suite):** Tasks 32-46 (Unit + Smoke + Playwright-basierte GUI-Tests)

---

## Teil 7: Test-Suite — Unit, Smoke und Playwright-basierte GUI-Tests

### Test-Architektur Übersicht

Drei Test-Ebenen, jede mit klarer Verantwortung:

| Ebene | Verzeichnis | Framework | Zweck | Anzahl Tests |
|-------|------------|-----------|------|-------------|
| **Unit** | `tests/` | pytest + pytest-qt | Domain-Layer + GUI-Komponenten isoliert testen | ~40 |
| **Smoke** | `tests_smoke/` | pytest + subprocess | App startet, CLI funktioniert, GUI öffnet sich, keine Crash-on-boot | ~8 |
| **Playwright** | `tests_e2e/` | pytest + playwright (Qt-WebDriver) | GUI-Interaktion wie ein User: Klicken, Tippen, Navigation, Drag&Drop | ~15 |

**Test-Runner:** `pytest` für alle Ebenen. Marker separieren: `@pytest.mark.unit`, `@pytest.mark.smoke`, `@pytest.mark.e2e`.

**CI-Matrix:**

```
pytest tests/ -m unit          # schnell, headless, kein Display nötig
pytest tests_smoke/ -m smoke   # subprocess-basiert, braucht PySide6 installiert
pytest tests_e2e/ -m e2e       # braucht Qt-WebDriver + Display (Xvfb oder real)
```

### 7.1 Unit Tests — Domain-Layer (Bestehende erweitern)

Die bestehenden `tests/` nutzen `unittest` (nicht pytest). Wir migrieren auf pytest und erweitern.

---

### Task 32: pytest conftest.py und Fixtures erstellen

**Objective:** Gemeinsame pytest-Fixtures für Domain- und GUI-Tests

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/fixtures/` (Verzeichnis für Test-Daten)

**Steps:**

1. `tests/conftest.py`:
```python
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch
import pytest


@pytest.fixture
def tmp_project(tmp_path):
    """Temporarily redirect all DLLS_Manager paths to tmp_path."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        env = {
            "DLLS_MANAGER_PROFILES_DIR": str(root / "profiles"),
            "DLLS_MANAGER_INSTALL_OVERRIDES_DIR": str(root / "overrides"),
            "DLLS_MANAGER_ROLLBACKS_DIR": str(root / "rollbacks"),
            "DLLS_MANAGER_DLSS_RUNTIME_DIR": str(root / "dlss_runtime"),
            "DLLS_MANAGER_DLSS_DOWNLOADS_DIR": str(root / "dlss_downloads"),
            "DLLS_MANAGER_SNAPSHOTS_DIR": str(root / "snapshots"),
            "DLLS_MANAGER_INSTALLS_FILE": str(root / "installs.json"),
            "DLLS_MANAGER_DLSS_VERSIONS_FILE": str(root / "dlss_versions.json"),
            "DLLS_MANAGER_GAMES_FILE": str(root / "games.json"),
            "DLLS_MANAGER_ANTI_CHEAT_RULES_FILE": str(root / "anti_cheat_rules.json"),
        }
        import os
        old_env = dict(os.environ)
        os.environ.update(env)
        (root / "profiles").mkdir()
        yield root
        os.environ.clear()
        os.environ.update(old_env)


@pytest.fixture
def sample_install(tmp_project):
    """Create a minimal install record in installs.json."""
    install = {
        "id": "steam:test-game",
        "display_name": "Test Game",
        "source": "steam",
        "source_id": "test-game",
        "launcher_family": "steam",
        "store_family": "steam",
        "execution_strategy": "steam_app",
        "runtime": "proton-dx11",
        "install_root": str(tmp_project / "game"),
        "prefix_path": None,
        "runner_name": None,
        "runner_path": None,
        "exe_path": None,
        "script_path": None,
        "desktop_file": None,
        "app_id": "123456",
        "launch_command": ["steam", "-applaunch", "123456"],
        "launch_env": {},
        "launch_args": "",
        "wrapper_chain": [],
        "working_directory": None,
        "scan_paths": [],
        "notes": [],
        "validation_errors": [],
        "validation_warnings": [],
        "discovery_confidence": "high",
        "anti_cheat": "none",
        "anti_cheat_vendor": None,
        "anti_cheat_policy": "verified_supported",
        "supports_dlss_override": True,
        "supports_dlss_version_selection": True,
        "override_mode": "experimental",
    }
    (tmp_project / "game").mkdir()
    (tmp_project / "installs.json").write_text(
        json.dumps({"created_at": "2026-01-01T00:00:00Z", "warnings": [], "installs": [install]})
    )
    return install


@pytest.fixture
def dlss_zip_with_three_dlls(tmp_path):
    """Create a ZIP containing nvngx_dlss.dll, nvngx_dlssd.dll, nvngx_dlssg.dll."""
    zip_path = tmp_path / "test_dlss.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("sdk/bin/nvngx_dlss.dll", b"sr-dll-bytes")
        archive.writestr("sdk/bin/nvngx_dlssd.dll", b"rr-dll-bytes")
        archive.writestr("sdk/bin/nvngx_dlssg.dll", b"fg-dll-bytes")
    return zip_path


@pytest.fixture
def default_profile(tmp_project):
    """Create a default profile in tmp_project."""
    from dlls_manager.profile_db import save_profile
    save_profile("default", {
        "enable_nvapi": True,
        "enable_smooth_motion": False,
        "use_gamemode": True,
        "use_mangohud": False,
        "launch_args": "",
        "custom_env": {},
        "dlss_mode": "game_default",
        "dlss_version": None,
        "allow_unsupported_override": False,
        "safety_mode": "strict",
    })
    return "default"
```

2. Run: `python3 -m pytest tests/conftest.py --co` — expected: keine Errors

**Commit:** `test: add pytest conftest with shared fixtures`

---

### Task 33: Unit Tests — DLSS Multi-DLL Extraction (SR + RR + FG)

**Objective:** Test dass `extract_all_dlss_dlls_from_zip()` alle 3 DLLs extrahiert

**Files:**
- Create: `tests/test_dlss_multi_dll.py`

**Steps:**

1. Tests:
```python
import pytest
from dlls_manager.dlss_catalog import extract_all_dlss_dlls_from_zip


class TestExtractAllDlssDlls:
    def test_extracts_all_three_dlls(self, dlss_zip_with_three_dlls, tmp_path):
        target_dir = tmp_path / "runtime"
        extracted = extract_all_dlss_dlls_from_zip(dlss_zip_with_three_dlls, target_dir)
        assert set(extracted) == {"nvngx_dlss.dll", "nvngx_dlssd.dll", "nvngx_dlssg.dll"}
        assert (target_dir / "nvngx_dlss.dll").read_bytes() == b"sr-dll-bytes"
        assert (target_dir / "nvngx_dlssd.dll").read_bytes() == b"rr-dll-bytes"
        assert (target_dir / "nvngx_dlssg.dll").read_bytes() == b"fg-dll-bytes"

    def test_extracts_only_available_dlls(self, tmp_path):
        import zipfile
        zip_path = tmp_path / "partial.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("bin/nvngx_dlss.dll", b"sr-only")
        target_dir = tmp_path / "runtime"
        extracted = extract_all_dlss_dlls_from_zip(zip_path, target_dir)
        assert extracted == ["nvngx_dlss.dll"]
        assert not (target_dir / "nvngx_dlssd.dll").exists()

    def test_returns_empty_list_for_zip_without_dlls(self, tmp_path):
        import zipfile
        zip_path = tmp_path / "empty.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("readme.txt", b"no dlls here")
        target_dir = tmp_path / "runtime"
        extracted = extract_all_dlss_dlls_from_zip(zip_path, target_dir)
        assert extracted == []

    def test_overwrites_existing_dlls(self, dlss_zip_with_three_dlls, tmp_path):
        target_dir = tmp_path / "runtime"
        target_dir.mkdir()
        (target_dir / "nvngx_dlss.dll").write_bytes(b"old-bytes")
        extract_all_dlss_dlls_from_zip(dlss_zip_with_three_dlls, target_dir)
        assert (target_dir / "nvngx_dlss.dll").read_bytes() == b"sr-dll-bytes"
```

2. Run: `python3 -m pytest tests/test_dlss_multi_dll.py -v` — expected: 4 passed

**Commit:** `test: add unit tests for multi-DLL extraction`

---

### Task 34: Unit Tests — DLSS Preset Override Env-Var Generierung

**Objective:** Test dass Profile mit Preset-Overrides korrekte Env-Vars generiert

**Files:**
- Create: `tests/test_dlss_presets.py`

**Steps:**

1. Tests:
```python
import pytest
from dlls_manager.launch_plan import build_profile_env_and_wrappers
from dlls_manager.profile_db import save_profile


class TestDlssPresetEnvVars:
    def test_sr_preset_generates_drs_settings(self, tmp_project):
        save_profile("test", {
            "enable_nvapi": True, "enable_smooth_motion": False,
            "use_gamemode": False, "use_mangohud": False,
            "launch_args": "", "custom_env": {},
            "dlss_mode": "game_default", "dlss_version": None,
            "allow_unsupported_override": False, "safety_mode": "strict",
            "dlss_sr_preset": "latest", "dlss_rr_preset": None,
            "dlss_fg_override": None, "enable_ngx_updater": False,
            "enable_hags": False, "enable_vkreflex": False,
            "proton_dlss_upgrade": None,
        })
        from dlls_manager.profile_db import load_profile
        profile = load_profile("test")
        env, _ = build_profile_env_and_wrappers(profile)
        assert "DXVK_NVAPI_DRS_SETTINGS" in env
        assert "NGX_DLSS_SR_OVERRIDE=on" in env["DXVK_NVAPI_DRS_SETTINGS"]
        assert "render_preset_latest" in env["DXVK_NVAPI_DRS_SETTINGS"]

    def test_rr_and_sr_presets_generate_combined_drs(self, tmp_project):
        save_profile("test", {
            "enable_nvapi": True, "enable_smooth_motion": False,
            "use_gamemode": False, "use_mangohud": False,
            "launch_args": "", "custom_env": {},
            "dlss_mode": "game_default", "dlss_version": None,
            "allow_unsupported_override": False, "safety_mode": "strict",
            "dlss_sr_preset": "j", "dlss_rr_preset": "k",
            "dlss_fg_override": None, "enable_ngx_updater": False,
            "enable_hags": False, "enable_vkreflex": False,
            "proton_dlss_upgrade": None,
        })
        from dlls_manager.profile_db import load_profile
        profile = load_profile("test")
        env, _ = build_profile_env_and_wrappers(profile)
        drs = env["DXVK_NVAPI_DRS_SETTINGS"]
        assert "render_preset_j" in drs
        assert "render_preset_k" in drs

    def test_fg_override_on_adds_fg_to_drs(self, tmp_project):
        save_profile("test", {
            "enable_nvapi": True, "enable_smooth_motion": False,
            "use_gamemode": False, "use_mangohud": False,
            "launch_args": "", "custom_env": {},
            "dlss_mode": "game_default", "dlss_version": None,
            "allow_unsupported_override": False, "safety_mode": "strict",
            "dlss_sr_preset": None, "dlss_rr_preset": None,
            "dlss_fg_override": "on", "enable_ngx_updater": False,
            "enable_hags": False, "enable_vkreflex": False,
            "proton_dlss_upgrade": None,
        })
        from dlls_manager.profile_db import load_profile
        profile = load_profile("test")
        env, _ = build_profile_env_and_wrappers(profile)
        assert "NGX_DLSS_FG_OVERRIDE=on" in env["DXVK_NVAPI_DRS_SETTINGS"]

    def test_no_presets_no_drs_settings(self, tmp_project):
        save_profile("test", {
            "enable_nvapi": True, "enable_smooth_motion": False,
            "use_gamemode": False, "use_mangohud": False,
            "launch_args": "", "custom_env": {},
            "dlss_mode": "game_default", "dlss_version": None,
            "allow_unsupported_override": False, "safety_mode": "strict",
            "dlss_sr_preset": None, "dlss_rr_preset": None,
            "dlss_fg_override": None, "enable_ngx_updater": False,
            "enable_hags": False, "enable_vkreflex": False,
            "proton_dlss_upgrade": None,
        })
        from dlls_manager.profile_db import load_profile
        profile = load_profile("test")
        env, _ = build_profile_env_and_wrappers(profile)
        assert "DXVK_NVAPI_DRS_SETTINGS" not in env

    def test_hags_generates_winehags_env(self, tmp_project):
        save_profile("test", {
            "enable_nvapi": True, "enable_smooth_motion": False,
            "use_gamemode": False, "use_mangohud": False,
            "launch_args": "", "custom_env": {},
            "dlss_mode": "game_default", "dlss_version": None,
            "allow_unsupported_override": False, "safety_mode": "strict",
            "dlss_sr_preset": None, "dlss_rr_preset": None,
            "dlss_fg_override": None, "enable_ngx_updater": False,
            "enable_hags": True, "enable_vkreflex": False,
            "proton_dlss_upgrade": None,
        })
        from dlls_manager.profile_db import load_profile
        profile = load_profile("test")
        env, _ = build_profile_env_and_wrappers(profile)
        assert env.get("WINEHAGS") == "1"

    def test_vkreflex_generates_env(self, tmp_project):
        save_profile("test", {
            "enable_nvapi": True, "enable_smooth_motion": False,
            "use_gamemode": False, "use_mangohud": False,
            "launch_args": "", "custom_env": {},
            "dlss_mode": "game_default", "dlss_version": None,
            "allow_unsupported_override": False, "safety_mode": "strict",
            "dlss_sr_preset": None, "dlss_rr_preset": None,
            "dlss_fg_override": None, "enable_ngx_updater": False,
            "enable_hags": False, "enable_vkreflex": True,
            "proton_dlss_upgrade": None,
        })
        from dlls_manager.profile_db import load_profile
        profile = load_profile("test")
        env, _ = build_profile_env_and_wrappers(profile)
        assert env.get("DXVK_NVAPI_VKREFLEX") == "1"

    def test_ngx_updater_generates_env(self, tmp_project):
        save_profile("test", {
            "enable_nvapi": True, "enable_smooth_motion": False,
            "use_gamemode": False, "use_mangohud": False,
            "launch_args": "", "custom_env": {},
            "dlss_mode": "game_default", "dlss_version": None,
            "allow_unsupported_override": False, "safety_mode": "strict",
            "dlss_sr_preset": None, "dlss_rr_preset": None,
            "dlss_fg_override": None, "enable_ngx_updater": True,
            "enable_hags": False, "enable_vkreflex": False,
            "proton_dlss_upgrade": None,
        })
        from dlls_manager.profile_db import load_profile
        profile = load_profile("test")
        env, _ = build_profile_env_and_wrappers(profile)
        assert env.get("PROTON_ENABLE_NGX_UPDATER") == "1"

    def test_proton_dlss_upgrade_env(self, tmp_project):
        save_profile("test", {
            "enable_nvapi": True, "enable_smooth_motion": False,
            "use_gamemode": False, "use_mangohud": False,
            "launch_args": "", "custom_env": {},
            "dlss_mode": "game_default", "dlss_version": None,
            "allow_unsupported_override": False, "safety_mode": "strict",
            "dlss_sr_preset": None, "dlss_rr_preset": None,
            "dlss_fg_override": None, "enable_ngx_updater": False,
            "enable_hags": False, "enable_vkreflex": False,
            "proton_dlss_upgrade": "310.7",
        })
        from dlls_manager.profile_db import load_profile
        profile = load_profile("test")
        env, _ = build_profile_env_and_wrappers(profile)
        assert env.get("PROTON_DLSS_UPGRADE") == "310.7"
```

2. Run: `python3 -m pytest tests/test_dlss_presets.py -v` — expected: 8 passed

**Commit:** `test: add unit tests for DLSS preset override env-var generation`

---

### Task 35: Unit Tests — Catalog mit RR/FG DLL-State

**Objective:** Test dass `_with_local_state()` korrekt RR/FG DLL-Verfügbarkeit meldet

**Files:**
- Create: `tests/test_dlss_catalog_state.py`

**Steps:**

1. Tests:
```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from dlls_manager.dlss_catalog import _with_local_state


class TestCatalogLocalState:
    def test_all_three_dlls_present(self, tmp_path):
        runtime_dir = tmp_path / "dlss_runtime" / "310.7.0"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "nvngx_dlss.dll").write_bytes(b"sr")
        (runtime_dir / "nvngx_dlssd.dll").write_bytes(b"rr")
        (runtime_dir / "nvngx_dlssg.dll").write_bytes(b"fg")

        entry = {"id": "310.7.0", "label": "DLSS 310.7.0", "selectable": True}
        with patch("dlls_manager.dlss_catalog.DLSS_RUNTIME_DIR", tmp_path / "dlss_runtime"):
            result = _with_local_state(entry)
        assert result["downloaded"] is True
        assert result["has_rr_dll"] is True
        assert result["has_fg_dll"] is True

    def test_only_sr_dll_present(self, tmp_path):
        runtime_dir = tmp_path / "dlss_runtime" / "3.7.10"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "nvngx_dlss.dll").write_bytes(b"sr")

        entry = {"id": "3.7.10", "label": "DLSS 3.7.10", "selectable": True}
        with patch("dlls_manager.dlss_catalog.DLSS_RUNTIME_DIR", tmp_path / "dlss_runtime"):
            result = _with_local_state(entry)
        assert result["downloaded"] is True
        assert result["has_rr_dll"] is False
        assert result["has_fg_dll"] is False

    def test_no_dlls_present(self, tmp_path):
        runtime_dir = tmp_path / "dlss_runtime" / "999.0.0"
        runtime_dir.mkdir(parents=True)

        entry = {"id": "999.0.0", "label": "DLSS 999", "selectable": True}
        with patch("dlls_manager.dlss_catalog.DLSS_RUNTIME_DIR", tmp_path / "dlss_runtime"):
            result = _with_local_state(entry)
        assert result["downloaded"] is False
        assert result["has_rr_dll"] is False
        assert result["has_fg_dll"] is False

    def test_game_default_never_has_dlls(self, tmp_path):
        entry = {"id": "game_default", "label": "Game Default", "selectable": True}
        with patch("dlls_manager.dlss_catalog.DLSS_RUNTIME_DIR", tmp_path / "dlss_runtime"):
            result = _with_local_state(entry)
        assert result["downloaded"] is False
        assert result["has_rr_dll"] is False
        assert result["has_fg_dll"] is False
```

2. Run: `python3 -m pytest tests/test_dlss_catalog_state.py -v` — expected: 4 passed

**Commit:** `test: add unit tests for catalog RR/FG DLL state`

---

### Task 36: Unit Tests — Proton-Version-Detection

**Objective:** Test dass `proton_db.py` Proton-Verzeichnisse korrekt scannt

**Files:**
- Create: `tests/test_proton_db.py`

**Steps:**

1. Tests:
```python
import pytest
from pathlib import Path
from unittest.mock import patch
from dlls_manager.proton_db import discover_proton_versions, get_install_proton_version


class TestProtonDb:
    def test_discovers_proton_versions_in_steamapps(self, tmp_path):
        steamapps = tmp_path / "steamapps" / "common"
        (steamapps / "Proton Experimental").mkdir(parents=True)
        (steamapps / "Proton 9.0-3").mkdir(parents=True)
        with patch("dlls_manager.proton_db.STEAM_ROOT_DIRS", (tmp_path,)):
            versions = discover_proton_versions()
        names = [v["name"] for v in versions]
        assert "Proton Experimental" in names
        assert "Proton 9.0-3" in names

    def test_discovers_compattools(self, tmp_path):
        compattools = tmp_path / "compatibilitytools.d"
        (compattools / "GE-Proton10-26").mkdir(parents=True)
        (compattools / "Proton-CachyOS").mkdir(parents=True)
        with patch("dlls_manager.proton_db.COMPATTOOLS_DIR", compattools):
            versions = discover_proton_versions()
        names = [v["name"] for v in versions]
        assert "GE-Proton10-26" in names
        assert "Proton-CachyOS" in names

    def test_get_install_proton_version_reads_config_info(self, tmp_path):
        # Simulate compatdata/<appid>/config_info
        compatdata = tmp_path / "compatdata" / "123456"
        compatdata.mkdir(parents=True)
        (compatdata / "config_info").write_text(
            '"compatibilitytools" "GE-Proton10-26"', encoding="utf-8"
        )
        with patch("dlls_manager.proton_db.STEAM_ROOT_DIRS", (tmp_path,)):
            result = get_install_proton_version("123456")
        assert "GE-Proton10-26" in result

    def test_no_proton_versions_returns_empty(self, tmp_path):
        with patch("dlls_manager.proton_db.STEAM_ROOT_DIRS", (tmp_path,)):
            versions = discover_proton_versions()
        assert versions == []
```

2. Run: `python3 -m pytest tests/test_proton_db.py -v` — expected: 4 passed

**Commit:** `test: add unit tests for Proton version detection`

---

### Task 37: Unit Tests — Blacklist Integration

**Objective:** Test dass Blacklist geladen wird und Policy-Evaluation blockiert

**Files:**
- Create: `tests/test_blacklist.py`

**Steps:**

1. Tests:
```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from dlls_manager.blacklist import load_blacklist, is_blacklisted, should_skip_dll_swap


class TestBlacklist:
    def test_load_blacklist_from_csv(self, tmp_path):
        csv_path = tmp_path / "blacklist.csv"
        csv_path.write_text(
            "app_id,game_name,reason\n"
            "123456,Warframe,Replaces DLL on launch\n"
            "789012,3DMark,Uses own DLSS for testing\n",
            encoding="utf-8",
        )
        with patch("dlls_manager.blacklist.BLACKLIST_FILE", csv_path):
            bl = load_blacklist()
        assert "123456" in bl
        assert "789012" in bl
        assert bl["123456"]["game_name"] == "Warframe"

    def test_is_blacklisted_by_app_id(self, tmp_path):
        csv_path = tmp_path / "blacklist.csv"
        csv_path.write_text("app_id,game_name,reason\n123456,Warframe,Replaces DLL\n", encoding="utf-8")
        with patch("dlls_manager.blacklist.BLACKLIST_FILE", csv_path):
            assert is_blacklisted(app_id="123456") is True
            assert is_blacklisted(app_id="999999") is False

    def test_blacklist_blocks_policy(self, tmp_project, tmp_path):
        # Install mit app_id 123456 + blacklist-Eintrag
        csv_path = tmp_path / "blacklist.csv"
        csv_path.write_text("app_id,game_name,reason\n123456,Warframe,Replaces DLL\n", encoding="utf-8")
        (tmp_project / "installs.json").write_text(json.dumps({
            "created_at": "2026-01-01T00:00:00Z",
            "warnings": [],
            "installs": [{
                "id": "steam:warframe", "display_name": "Warframe",
                "source": "steam", "source_id": "warframe",
                "launcher_family": "steam", "store_family": "steam",
                "execution_strategy": "steam_app", "runtime": "proton-dx12",
                "install_root": str(tmp_project / "wf"),
                "prefix_path": None, "runner_name": None, "runner_path": None,
                "exe_path": None, "script_path": None, "desktop_file": None,
                "app_id": "123456",
                "launch_command": ["steam", "-applaunch", "123456"],
                "launch_env": {}, "launch_args": "", "wrapper_chain": [],
                "working_directory": None, "scan_paths": [], "notes": [],
                "validation_errors": [], "validation_warnings": [],
                "discovery_confidence": "high",
                "anti_cheat": "none", "anti_cheat_vendor": None,
                "anti_cheat_policy": "verified_supported",
                "supports_dlss_override": True,
                "supports_dlss_version_selection": True,
                "override_mode": "experimental",
            }],
        }))
        with patch("dlls_manager.blacklist.BLACKLIST_FILE", csv_path):
            from dlls_manager.launch_plan import build_install_launch_plan
            from dlls_manager.profile_db import save_profile
            save_profile("default", {
                "enable_nvapi": False, "enable_smooth_motion": False,
                "use_gamemode": False, "use_mangohud": False,
                "launch_args": "", "custom_env": {},
                "dlss_mode": "game_default", "dlss_version": "3.7.10",
                "allow_unsupported_override": False, "safety_mode": "strict",
            })
            plan = build_install_launch_plan("steam:warframe", "default")
            assert any("blacklist" in r.lower() for r in plan["blocked_reasons"])

    def test_empty_blacklist_does_not_block(self, tmp_path):
        csv_path = tmp_path / "blacklist.csv"
        csv_path.write_text("app_id,game_name,reason\n", encoding="utf-8")
        with patch("dlls_manager.blacklist.BLACKLIST_FILE", csv_path):
            assert is_blacklisted(app_id="123456") is False

    def test_missing_blacklist_file_returns_empty(self, tmp_path):
        with patch("dlls_manager.blacklist.BLACKLIST_FILE", tmp_path / "nonexistent.csv"):
            assert is_blacklisted(app_id="123456") is False
            assert load_blacklist() == {}
```

2. Run: `python3 -m pytest tests/test_blacklist.py -v` — expected: 5 passed

**Commit:** `test: add unit tests for community blacklist integration`

---

### Task 38: Unit Tests — Bestehende Tests migrieren und reparieren

**Objective:** Bestehende unittest-Tests auf pytest umstellen, webUI-bezogene Tests entfernen, kaputte Tests fixen

**Files:**
- Modify: `tests/test_cli_flow.py` — entferne `test_export_mock_ui_data`, `test_discover_and_list_installs` anpassen
- Modify: `tests/test_mock_ui_data.py` — löschen (mock_ui entfernt)
- Modify: `tests/test_apply_and_launch.py` — passe neue Profile-Felder an (Defaults für neue Felder)
- Modify: `tests/test_profile_override_store.py` — teste neue Profile-Felder
- Modify: `tests/test_policy_logic.py` — teste Preset-bezogene Policy-Logik

**Steps:**

1. `test_cli_flow.py`: Entferne `test_export_mock_ui_data` komplett. `test_discover_and_list_installs` bleibt. `test_launch_preview_default_ok` — passe erwartete Command-Preview an (neue Env-Vars falls neue Defaults gesetzt).

2. `test_mock_ui_data.py`: Löschen — Datei referenziert `export_mock_library` das entfernt wird.

3. `test_apply_and_launch.py`: Profile-Save-Calls müssen neue Defaults setzen (`dlss_sr_preset: None`, `dlss_rr_preset: None`, `dlss_fg_override: None`, `enable_ngx_updater: False`, `enable_hags: False`, `enable_vkreflex: False`, `proton_dlss_upgrade: None`). Bei `test_apply_creates_backup_and_rollback_restores_files` muss die Mutation-Step-Count evtl. angepasst werden (wenn RR/FG-DLL-Swap hinzukommt).

4. `test_profile_override_store.py`: Neue Tests hinzufügen:
```python
def test_profile_accepts_new_preset_fields(tmp_project):
    from dlls_manager.profile_db import save_profile, load_profile
    save_profile("test", {
        "enable_nvapi": False, "enable_smooth_motion": False,
        "use_gamemode": False, "use_mangohud": False,
        "launch_args": "", "custom_env": {},
        "dlss_mode": "game_default", "dlss_version": None,
        "allow_unsupported_override": False, "safety_mode": "strict",
        "dlss_sr_preset": "j", "dlss_rr_preset": "latest",
        "dlss_fg_override": "on", "enable_ngx_updater": True,
        "enable_hags": True, "enable_vkreflex": True,
        "proton_dlss_upgrade": "1",
    })
    profile = load_profile("test")
    assert profile["dlss_sr_preset"] == "j"
    assert profile["dlss_rr_preset"] == "latest"
    assert profile["dlss_fg_override"] == "on"
    assert profile["enable_ngx_updater"] is True
    assert profile["enable_hags"] is True
    assert profile["enable_vkreflex"] is True
    assert profile["proton_dlss_upgrade"] == "1"

def test_profile_defaults_new_fields_to_none_or_false(tmp_project):
    from dlls_manager.profile_db import save_profile, load_profile
    save_profile("minimal", {
        "enable_nvapi": False, "enable_smooth_motion": False,
        "use_gamemode": False, "use_mangohud": False,
        "launch_args": "", "custom_env": {},
        "dlss_mode": "game_default", "dlss_version": None,
        "allow_unsupported_override": False, "safety_mode": "strict",
    })
    profile = load_profile("minimal")
    assert profile["dlss_sr_preset"] is None
    assert profile["dlss_rr_preset"] is None
    assert profile["dlss_fg_override"] is None
    assert profile["enable_ngx_updater"] is False
    assert profile["enable_hags"] is False
    assert profile["enable_vkreflex"] is False
    assert profile["proton_dlss_upgrade"] is None
```

5. Run: `python3 -m pytest tests/ -v -m unit` — expected: alle grün (bis auf bewusst entfernte)

**Commit:** `test: migrate existing tests to pytest, fix for new profile fields`

---

### 7.2 Smoke Tests — App startet und funktioniert

---

### Task 39: Smoke Test Suite erstellen

**Objective:** Tests dass die App überhaupt startet und grundlegende Dinge funktionieren

**Files:**
- Create: `tests_smoke/__init__.py`
- Create: `tests_smoke/conftest.py`
- Create: `tests_smoke/test_app_launches.py`
- Create: `tests_smoke/test_cli_commands.py`
- Create: `tests_smoke/test_gui_launches.py`

**Steps:**

1. `tests_smoke/conftest.py`:
```python
import subprocess
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def run_cli():
    def _run(*args, **kwargs):
        return subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "main.py"), *args],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            **kwargs,
        )
    return _run
```

2. `tests_smoke/test_app_launches.py` — Import- und Initialisierung-Tests:
```python
import importlib
import pytest


class TestAppImports:
    def test_import_cli(self):
        importlib.import_module("dlls_manager.cli")

    def test_import_gui_main(self):
        importlib.import_module("dlls_manager.gui.__main__")

    def test_import_gui_main_window(self):
        importlib.import_module("dlls_manager.gui.main_window")

    def test_import_all_pages(self):
        for page in ["library", "catalog", "profiles", "rollbacks", "system"]:
            importlib.import_module(f"dlls_manager.gui.pages.{page}")

    def test_import_workers(self):
        importlib.import_module("dlls_manager.gui.workers")

    def test_no_fastapi_imports_remain(self):
        """Verify FastAPI is not imported anywhere in the codebase."""
        import ast
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent / "dlls_manager"
        for py_file in root.rglob("*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "fastapi" not in alias.name.lower(), \
                            f"FastAPI import found in {py_file}"
                if isinstance(node, ast.ImportFrom):
                    assert "fastapi" not in (node.module or "").lower(), \
                        f"FastAPI import found in {py_file}"
```

3. `tests_smoke/test_cli_commands.py` — CLI smoke:
```python
import json
import pytest


class TestCliSmoke:
    def test_help_exits_zero(self, run_cli):
        result = run_cli("--help")
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()

    def test_detect(self, run_cli):
        result = run_cli("detect")
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert "os" in payload
        assert "python" in payload

    def test_list_profiles(self, run_cli):
        result = run_cli("list-profiles")
        assert result.returncode == 0

    def test_list_dlss_catalog(self, run_cli):
        result = run_cli("list-dlss-catalog")
        assert result.returncode == 0

    def test_list_installs(self, run_cli):
        result = run_cli("list-installs")
        assert result.returncode == 0

    def test_serve_ui_command_removed(self, run_cli):
        """serve-ui should no longer exist as a CLI command."""
        result = run_cli("serve-ui")
        assert result.returncode != 0

    def test_export_mock_ui_command_removed(self, run_cli):
        result = run_cli("export-mock-ui-data")
        assert result.returncode != 0
```

4. `tests_smoke/test_gui_launches.py` — GUI launch smoke:
```python
import subprocess
import sys
import time
import pytest
from pathlib import Path


class TestGuiLaunches:
    def test_gui_window_opens_and_closes(self, qapp):
        """Verify MainWindow constructs without crashing."""
        from dlls_manager.gui.main_window import MainWindow
        window = MainWindow()
        assert window.windowTitle() == "DLSS Manager"
        window.close()

    def test_gui_has_five_sidebar_entries(self, qapp):
        from dlls_manager.gui.main_window import MainWindow
        window = MainWindow()
        sidebar = window.findChild(type(window.sidebar), "sidebar")
        assert sidebar is not None
        assert sidebar.count() == 5
        window.close()

    def test_gui_app_entry_point_import(self):
        """Verify the gui entry point function is importable and callable (without exec)."""
        from dlls_manager.gui.__main__ import main
        assert callable(main)
```

5. `tests_smoke/conftest.py` — erweitere um qapp fixture:
```python
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
```

6. Run: `python3 -m pytest tests_smoke/ -v -m smoke` — expected: alle passed

**Commit:** `test: add smoke test suite for app launch and CLI`

---

### 7.3 Playwright-basierte GUI-Tests (PySide6)

Playwright testet die Qt-GUI per Headless-Browser-Steuerung. Da PySide6 keine Web-GUI ist, nutzen wir `pytest-qt` für GUI-Interaktion-Tests (Klicken, Tippen, Navigation) als "Playwright-äquivalent" für Qt. Zusätzlich nutzen wir `PySide6.QtTest` für Event-Simulation.

---

### Task 40: pytest-qt Fixtures und Test-Harness für GUI-Interaktion

**Objective:** GUI-Test-Infrastruktur die Klicks, Eingaben und Page-Wechsel simuliert

**Files:**
- Create: `tests_e2e/__init__.py` (neu, ersetzt altes Playwright-Browser-Setup)
- Create: `tests_e2e/conftest.py` (neu, pytest-qt-basiert)
- Create: `tests_e2e/support.py` (neu, GUI-Test-Helpers)

**Steps:**

1. `tests_e2e/conftest.py`:
```python
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def qtbot(qapp):
    from pytestqt.qtbot import QtBot
    bot = QtBot(qapp)
    yield bot


@pytest.fixture
def gui_env(tmp_path):
    """Full isolated environment for GUI tests — all paths redirected."""
    root = tmp_path / "gui-test"
    root.mkdir()
    env = {
        "DLLS_MANAGER_PROFILES_DIR": str(root / "profiles"),
        "DLLS_MANAGER_INSTALL_OVERRIDES_DIR": str(root / "overrides"),
        "DLLS_MANAGER_ROLLBACKS_DIR": str(root / "rollbacks"),
        "DLLS_MANAGER_DLSS_RUNTIME_DIR": str(root / "dlss_runtime"),
        "DLLS_MANAGER_DLSS_DOWNLOADS_DIR": str(root / "dlss_downloads"),
        "DLLS_MANAGER_SNAPSHOTS_DIR": str(root / "snapshots"),
        "DLLS_MANAGER_INSTALLS_FILE": str(root / "installs.json"),
        "DLLS_MANAGER_DLSS_VERSIONS_FILE": str(root / "dlss_versions.json"),
        "DLLS_MANAGER_GAMES_FILE": str(root / "games.json"),
        "DLLS_MANAGER_ANTI_CHEAT_RULES_FILE": str(root / "anti_cheat_rules.json"),
    }
    old = dict(os.environ)
    os.environ.update(env)
    (root / "profiles").mkdir()
    yield root
    os.environ.clear()
    os.environ.update(old)


@pytest.fixture
def gui_with_installs(gui_env):
    """GUI env with 3 sample installs (ok, blocked, broken)."""
    from dlls_manager.profile_db import save_profile

    save_profile("default", {
        "enable_nvapi": False, "enable_smooth_motion": False,
        "use_gamemode": False, "use_mangohud": False,
        "launch_args": "", "custom_env": {},
        "dlss_mode": "game_default", "dlss_version": None,
        "allow_unsupported_override": False, "safety_mode": "strict",
        "dlss_sr_preset": None, "dlss_rr_preset": None,
        "dlss_fg_override": None, "enable_ngx_updater": False,
        "enable_hags": False, "enable_vkreflex": False,
        "proton_dlss_upgrade": None,
    })

    installs = {
        "created_at": "2026-01-01T00:00:00Z",
        "warnings": [],
        "installs": [
            {
                "id": "manual:test-game",
                "display_name": "Test Game",
                "source": "manual", "source_id": "test-game",
                "launcher_family": "manual", "store_family": "generic",
                "execution_strategy": "script_exec", "runtime": "wine-script",
                "install_root": str(gui_env / "game"),
                "prefix_path": None, "runner_name": None, "runner_path": None,
                "exe_path": None, "script_path": str(gui_env / "game" / "run.sh"),
                "desktop_file": None, "app_id": None,
                "launch_command": [str(gui_env / "game" / "run.sh")],
                "launch_env": {}, "launch_args": "", "wrapper_chain": [],
                "working_directory": str(gui_env / "game"),
                "scan_paths": [], "notes": [],
                "validation_errors": [], "validation_warnings": [],
                "discovery_confidence": "high",
                "anti_cheat": "none", "anti_cheat_vendor": None,
                "anti_cheat_policy": "verified_supported",
                "supports_dlss_override": True,
                "supports_dlss_version_selection": True,
                "override_mode": "experimental",
            },
            {
                "id": "manual:blocked-game",
                "display_name": "Blocked Game",
                "source": "manual", "source_id": "blocked-game",
                "launcher_family": "manual", "store_family": "generic",
                "execution_strategy": "script_exec", "runtime": "wine-script",
                "install_root": str(gui_env / "blocked"),
                "prefix_path": None, "runner_name": None, "runner_path": None,
                "exe_path": None, "script_path": None,
                "desktop_file": None, "app_id": None,
                "launch_command": [], "launch_env": {},
                "launch_args": "", "wrapper_chain": [],
                "working_directory": None, "scan_paths": [], "notes": [],
                "validation_errors": [], "validation_warnings": [],
                "discovery_confidence": "high",
                "anti_cheat": "high", "anti_cheat_vendor": "EasyAntiCheat",
                "anti_cheat_policy": "blocked",
                "supports_dlss_override": False,
                "supports_dlss_version_selection": False,
                "override_mode": "blocked",
            },
        ],
    }
    (gui_env / "installs.json").write_text(json.dumps(installs))
    (gui_env / "game").mkdir()
    run_script = gui_env / "game" / "run.sh"
    run_script.write_text("#!/usr/bin/env bash\nexit 0\n")
    run_script.chmod(0o755)
    (gui_env / "game" / "nvngx_dlss.dll").write_text("original-dll")

    # DLSS catalog
    dlss_versions = [
        {"id": "game_default", "label": "Game Default", "selectable": True, "source": "built_in"},
        {"id": "3.7.20", "version": "3.7.20", "label": "DLSS 3.7.20", "selectable": True,
         "source": "official_nvidia_github", "browser_download_url": "http://invalid/test.zip",
         "asset_name": "test.zip", "asset_size": 100, "asset_content_type": "application/zip",
         "published_at": "2026-01-01T00:00:00Z", "release_name": "Test", "release_url": "http://invalid"},
    ]
    (gui_env / "dlss_versions.json").write_text(json.dumps(dlss_versions))

    # DLSS runtime for 3.7.20
    runtime_dir = gui_env / "dlss_runtime" / "3.7.20"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "nvngx_dlss.dll").write_text("new-dll")

    return gui_env
```

2. `tests_e2e/support.py`:
```python
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QPushButton, QListWidget, QTableWidget
from PySide6.QtCore import Qt


def click_button(parent: QWidget, object_name: str) -> None:
    """Find and click a button by its objectName."""
    button = parent.findChild(QPushButton, object_name)
    assert button is not None, f"Button '{object_name}' not found"
    button.click()


def get_list_widget_items(parent: QWidget, object_name: str) -> list[str]:
    """Return text of all items in a QListWidget by objectName."""
    widget = parent.findChild(QListWidget, object_name)
    assert widget is not None, f"QListWidget '{object_name}' not found"
    return [widget.item(i).text() for i in range(widget.count())]


def get_table_row_count(parent: QWidget, object_name: str) -> int:
    """Return row count of a QTableWidget by objectName."""
    table = parent.findChild(QTableWidget, object_name)
    assert table is not None, f"QTableWidget '{object_name}' not found"
    return table.rowCount()


def select_sidebar_item(main_window: QWidget, index: int) -> None:
    """Select a sidebar entry by index."""
    sidebar = main_window.findChild(QListWidget, "sidebar")
    assert sidebar is not None
    sidebar.setCurrentRow(index)


def fill_line_edit(parent: QWidget, object_name: str, text: str) -> None:
    """Find a QLineEdit by objectName and set its text."""
    from PySide6.QtWidgets import QLineEdit
    widget = parent.findChild(QLineEdit, object_name)
    assert widget is not None, f"QLineEdit '{object_name}' not found"
    widget.setText(text)


def check_checkbox(parent: QWidget, object_name: str, checked: bool = True) -> None:
    """Find a QCheckBox by objectName and set its state."""
    from PySide6.QtWidgets import QCheckBox
    widget = parent.findChild(QCheckBox, object_name)
    assert widget is not None, f"QCheckBox '{object_name}' not found"
    widget.setChecked(checked)


def select_combobox(parent: QWidget, object_name: str, value: str) -> None:
    """Find a QComboBox by objectName and select a value."""
    from PySide6.QtWidgets import QComboBox
    widget = parent.findChild(QComboBox, object_name)
    assert widget is not None, f"QComboBox '{object_name}' not found"
    idx = widget.findText(value)
    assert idx >= 0, f"Value '{value}' not in combobox '{object_name}'"
    widget.setCurrentIndex(idx)
```

3. Run: `python3 -m pytest tests_e2e/conftest.py --co` — expected: keine Errors

**Commit:** `test: add pytest-qt GUI test harness and conftest`

---

### Task 41: E2E GUI Test — Navigation zwischen Pages

**Objective:** Test dass Sidebar-Navigation zwischen allen 5 Pages funktioniert

**Files:**
- Create: `tests_e2e/test_navigation.py`

**Steps:**

1. Tests:
```python
import pytest
from dlls_manager.gui.main_window import MainWindow
from tests_e2e.support import select_sidebar_item, get_list_widget_items


class TestNavigation:
    def test_sidebar_has_five_entries(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        items = get_list_widget_items(window, "sidebar")
        assert len(items) == 5
        assert "Library" in items[0]
        assert "Catalog" in items[1]
        assert "Profiles" in items[2]
        assert "Rollbacks" in items[3]
        assert "System" in items[4]
        window.close()

    def test_default_page_is_library(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.stacked_widget.currentIndex() == 0  # Library
        window.close()

    def test_click_catalog_navigates_to_catalog(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 1)  # Catalog
        assert window.stacked_widget.currentIndex() == 1
        window.close()

    def test_click_profiles_navigates_to_profiles(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 2)
        assert window.stacked_widget.currentIndex() == 2
        window.close()

    def test_click_rollbacks_navigates_to_rollbacks(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 3)
        assert window.stacked_widget.currentIndex() == 3
        window.close()

    def test_click_system_navigates_to_system(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 4)
        assert window.stacked_widget.currentIndex() == 4
        window.close()

    def test_back_to_library_after_visiting_all(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        for i in range(5):
            select_sidebar_item(window, i)
            assert window.stacked_widget.currentIndex() == i
        select_sidebar_item(window, 0)
        assert window.stacked_widget.currentIndex() == 0
        window.close()
```

2. Run: `python3 -m pytest tests_e2e/test_navigation.py -v -m e2e` — expected: 7 passed

**Commit:** `test: add E2E GUI navigation tests`

---

### Task 42: E2E GUI Test — Library: Install-Auswahl und Detail-Panel

**Objective:** Test dass Install-Cards gerendert werden, Auswahl Detail-Panel füllt, Search filtert

**Files:**
- Create: `tests_e2e/test_library.py`

**Steps:**

1. Tests:
```python
import pytest
from dlls_manager.gui.main_window import MainWindow
from tests_e2e.support import (
    click_button, fill_line_edit, select_sidebar_item,
    get_list_widget_items, check_checkbox, select_combobox
)


class TestLibraryPage:
    def test_install_cards_rendered(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        library_page = window.library_page
        cards = library_page.findChildren(type(library_page), "game_card")
        # oder: Zähle Items in install_list
        assert library_page.install_list.count() >= 2
        window.close()

    def test_select_install_shows_detail(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        library_page = window.library_page
        # Klicke erstes Install
        library_page.install_list.setCurrentRow(0)
        detail = library_page.detail_panel
        assert detail is not None
        # Detail sollte Name zeigen
        name_label = detail.findChild(type(detail), "detail_name")
        assert name_label is not None
        assert "Test Game" in name_label.text()
        window.close()

    def test_search_filters_installs(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        library_page = window.library_page
        initial_count = library_page.install_list.count()
        fill_line_edit(library_page, "search_bar", "Blocked")
        # Nach Filter sollte nur "Blocked Game" sichtbar sein
        visible = [i for i in range(library_page.install_list.count())
                   if not library_page.install_list.item(i).isHidden()]
        assert len(visible) == 1
        assert "Blocked" in library_page.install_list.item(visible[0]).text()
        window.close()

    def test_blocked_install_shows_blocked_badge(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        library_page = window.library_page
        # Wähle "Blocked Game"
        for i in range(library_page.install_list.count()):
            if "Blocked" in library_page.install_list.item(i).text():
                library_page.install_list.setCurrentRow(i)
                break
        detail = library_page.detail_panel
        status_label = detail.findChild(type(detail), "detail_status")
        assert "blocked" in status_label.text().lower() or "blocked" in status_label.styleSheet().lower()
        window.close()

    def test_command_preview_shows_env_vars(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        library_page = window.library_page
        library_page.install_list.setCurrentRow(0)
        detail = library_page.detail_panel
        preview = detail.findChild(type(detail), "command_preview")
        assert preview is not None
        assert preview.toPlainText()  # nicht leer
        window.close()

    def test_refresh_button_triggers_discovery(self, qtbot, gui_with_installs, monkeypatch):
        window = MainWindow()
        qtbot.addWidget(window)
        library_page = window.library_page
        called = [False]
        def fake_discover():
            called[0] = True
            from dlls_manager.install_db import load_installs
            return load_installs()
        monkeypatch.setattr(library_page, "_run_discovery", fake_discover)
        click_button(library_page, "refresh_button")
        qtbot.wait_until(lambda: called[0] is True, timeout=5000)
        window.close()
```

2. Run: `python3 -m pytest tests_e2e/test_library.py -v -m e2e` — expected: 6 passed

**Commit:** `test: add E2E library page tests`

---

### Task 43: E2E GUI Test — Catalog: DLSS-Versionen und Download

**Objective:** Test dass Catalog-Tabelle rendert, Download-Button funktioniert, Refresh funktioniert

**Files:**
- Create: `tests_e2e/test_catalog.py`

**Steps:**

1. Tests:
```python
import pytest
from dlls_manager.gui.main_window import MainWindow
from tests_e2e.support import click_button, select_sidebar_item, get_table_row_count


class TestCatalogPage:
    def test_catalog_table_has_entries(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 1)  # Catalog
        catalog_page = window.catalog_page
        assert catalog_page.catalog_table.rowCount() >= 1
        window.close()

    def test_game_default_row_present(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 1)
        catalog_page = window.catalog_page
        # Erste Zeile sollte "game_default" sein
        version_item = catalog_page.catalog_table.item(0, 0)
        assert version_item is not None
        window.close()

    def test_dlss_version_row_shows_sr_rr_fg_columns(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 1)
        catalog_page = window.catalog_page
        # Spalten: Version, Label, Published, SR, RR, FG, Downloaded, Action
        assert catalog_page.catalog_table.columnCount() >= 7
        window.close()

    def test_downloaded_version_shows_checkmark(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 1)
        catalog_page = window.catalog_page
        # 3.7.20 sollte als downloaded markiert sein (runtime_dir hat nvngx_dlss.dll)
        for row in range(catalog_page.catalog_table.rowCount()):
            version_text = catalog_page.catalog_table.item(row, 0).text()
            if "3.7.20" in version_text:
                downloaded_item = catalog_page.catalog_table.item(row, 6)
                assert downloaded_item is not None
                assert "✓" in downloaded_item.text() or "yes" in downloaded_item.text().lower()
                break
        window.close()

    def test_refresh_button_triggers_catalog_refresh(self, qtbot, gui_with_installs, monkeypatch):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 1)
        catalog_page = window.catalog_page
        called = [False]
        def fake_refresh():
            called[0] = True
            return {"updated": True, "entries": 2}
        monkeypatch.setattr(catalog_page, "_run_refresh", fake_refresh)
        click_button(catalog_page, "refresh_catalog_button")
        qtbot.wait_until(lambda: called[0] is True, timeout=5000)
        window.close()
```

2. Run: `python3 -m pytest tests_e2e/test_catalog.py -v -m e2e` — expected: 5 passed

**Commit:** `test: add E2E catalog page tests`

---

### Task 44: E2E GUI Test — Profiles: Bearbeiten und Speichern

**Objective:** Test dass Profile-Editor Felder zeigt, Änderungen speichert, Preset-Dropdowns funktionieren

**Files:**
- Create: `tests_e2e/test_profiles.py`

**Steps:**

1. Tests:
```python
import json
import pytest
from pathlib import Path
from dlls_manager.gui.main_window import MainWindow
from tests_e2e.support import (
    click_button, fill_line_edit, select_sidebar_item,
    check_checkbox, select_combobox
)


class TestProfilesPage:
    def test_profiles_list_shows_default(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 2)
        profiles_page = window.profiles_page
        assert profiles_page.profile_list.count() >= 1
        assert "default" in profiles_page.profile_list.item(0).text().lower()
        window.close()

    def test_select_profile_shows_form_fields(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 2)
        profiles_page = window.profiles_page
        profiles_page.profile_list.setCurrentRow(0)
        # NVAPI Checkbox sichtbar
        nvapi_cb = profiles_page.findChild(type(profiles_page), "profile_enable_nvapi")
        assert nvapi_cb is not None
        window.close()

    def test_edit_and_save_profile(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 2)
        profiles_page = window.profiles_page
        profiles_page.profile_list.setCurrentRow(0)

        fill_line_edit(profiles_page, "profile_launch_args", "--test-args")
        check_checkbox(profiles_page, "profile_enable_nvapi", True)
        select_combobox(profiles_page, "profile_dlss_sr_preset", "latest")
        click_button(profiles_page, "save_profile_button")

        # Verify persisted
        profiles_dir = Path(__file__).resolve().parent.parent
        # Prüfe über API
        from dlls_manager.profile_db import load_profile
        profile = load_profile("default")
        assert profile["launch_args"] == "--test-args"
        assert profile["enable_nvapi"] is True
        assert profile["dlss_sr_preset"] == "latest"
        window.close()

    def test_preset_dropdown_has_options(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 2)
        profiles_page = window.profiles_page
        profiles_page.profile_list.setCurrentRow(0)
        from PySide6.QtWidgets import QComboBox
        sr_combo = profiles_page.findChild(QComboBox, "profile_dlss_sr_preset")
        assert sr_combo is not None
        items = [sr_combo.itemText(i) for i in range(sr_combo.count())]
        assert "latest" in items
        assert "j" in items
        assert "k" in items
        window.close()

    def test_proton_dlss_upgrade_field(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 2)
        profiles_page = window.profiles_page
        profiles_page.profile_list.setCurrentRow(0)
        fill_line_edit(profiles_page, "profile_proton_dlss_upgrade", "310.7")
        click_button(profiles_page, "save_profile_button")
        from dlls_manager.profile_db import load_profile
        profile = load_profile("default")
        assert profile["proton_dlss_upgrade"] == "310.7"
        window.close()
```

2. Run: `python3 -m pytest tests_e2e/test_profiles.py -v -m e2e` — expected: 5 passed

**Commit:** `test: add E2E profiles page tests`

---

### Task 45: E2E GUI Test — Override Editor, Apply, Launch, Rollback

**Objective:** Full Workflow Test: Override setzen → Apply → DLL gewechselt → Rollback → DLL restored

**Files:**
- Create: `tests_e2e/test_workflow.py`

**Steps:**

1. Tests:
```python
import json
import pytest
from pathlib import Path
from dlls_manager.gui.main_window import MainWindow
from tests_e2e.support import (
    click_button, fill_line_edit, select_sidebar_item,
    check_checkbox, select_combobox
)


class TestFullWorkflow:
    def test_set_override_and_apply_swaps_dll(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        library_page = window.library_page
        library_page.install_list.setCurrentRow(0)  # Test Game

        detail = library_page.detail_panel
        # Set DLSS version to 3.7.20
        select_combobox(detail, "dlss_version_select", "3.7.20")
        # Disable sync_to_launcher (direct swap)
        check_checkbox(detail, "override_sync_launcher", False)
        # Save override
        click_button(detail, "save_override_button")

        # Verify override persisted
        from dlls_manager.override_db import load_install_override
        override = load_install_override("manual:test-game")
        assert override["dlss_version"] == "3.7.20"

        # Apply
        click_button(detail, "apply_button")
        qtbot.wait(500)  # kurze Pause für QThread

        # DLL sollte gewechselt sein
        game_dir = Path(__file__).resolve().parent.parent
        dll_path = Path(gui_with_installs / "game" / "nvngx_dlss.dll")
        assert dll_path.read_text() == "new-dll"
        window.close()

    def test_rollback_restores_dll(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        library_page = window.library_page
        library_page.install_list.setCurrentRow(0)

        detail = library_page.detail_panel
        select_combobox(detail, "dlss_version_select", "3.7.20")
        check_checkbox(detail, "override_sync_launcher", False)
        click_button(detail, "save_override_button")
        click_button(detail, "apply_button")
        qtbot.wait(500)

        # Gehe zu Rollbacks page
        select_sidebar_item(window, 3)
        rollbacks_page = window.rollbacks_page
        assert rollbacks_page.rollback_table.rowCount() >= 1

        # Klicke Restore
        rollbacks_page.rollback_table.setCurrentCell(0, 0)
        click_button(rollbacks_page, "execute_rollback_button")
        qtbot.wait(500)

        # DLL sollte restored sein
        dll_path = Path(gui_with_installs / "game" / "nvngx_dlss.dll")
        assert dll_path.read_text() == "original-dll"
        window.close()

    def test_dry_run_does_not_swap_dll(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        library_page = window.library_page
        library_page.install_list.setCurrentRow(0)

        detail = library_page.detail_panel
        select_combobox(detail, "dlss_version_select", "3.7.20")
        check_checkbox(detail, "override_sync_launcher", False)
        click_button(detail, "save_override_button")
        click_button(detail, "dry_run_button")
        qtbot.wait(500)

        dll_path = Path(gui_with_installs / "game" / "nvngx_dlss.dll")
        assert dll_path.read_text() == "original-dll"
        window.close()

    def test_blocked_install_prevents_apply(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        library_page = window.library_page
        # Wähle Blocked Game
        for i in range(library_page.install_list.count()):
            if "Blocked" in library_page.install_list.item(i).text():
                library_page.install_list.setCurrentRow(i)
                break

        detail = library_page.detail_panel
        # Versuche Apply — sollte blockiert sein
        click_button(detail, "apply_button")
        qtbot.wait(500)

        # Kein DLL-Swap
        blocked_dll = Path(gui_with_installs / "blocked" / "nvngx_dlss.dll")
        if blocked_dll.exists():
            assert blocked_dll.read_text() != "new-dll"
        window.close()

    def test_env_var_preview_updates_live(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        library_page = window.library_page
        library_page.install_list.setCurrentRow(0)
        detail = library_page.detail_panel

        # Prüfe dass Env-Var-Preview nicht leer ist
        preview = detail.findChild(type(detail), "env_var_preview")
        assert preview is not None
        initial_text = preview.toPlainText()
        assert initial_text  # nicht leer

        # Ändere Override → Preview sollte sich aktualisieren
        select_combobox(detail, "dlss_version_select", "3.7.20")
        click_button(detail, "save_override_button")
        qtbot.wait(200)
        updated_text = preview.toPlainText()
        assert "DLLS_MANAGER_DLSS_VERSION" in updated_text or "3.7.20" in updated_text
        window.close()
```

2. Run: `python3 -m pytest tests_e2e/test_workflow.py -v -m e2e` — expected: 5 passed

**Commit:** `test: add E2E full workflow tests (apply, rollback, dry-run, blocked)`

---

### Task 46: E2E GUI Test — System Page und Rollbacks Page

**Objective:** System-Info rendert, Rollback-Liste zeigt Einträge, Execute funktioniert

**Files:**
- Create: `tests_e2e/test_system.py`
- Create: `tests_e2e/test_rollbacks.py`

**Steps:**

1. `tests_e2e/test_system.py`:
```python
import pytest
from dlls_manager.gui.main_window import MainWindow
from tests_e2e.support import click_button, select_sidebar_item


class TestSystemPage:
    def test_system_page_shows_os_info(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 4)
        system_page = window.system_page
        os_label = system_page.findChild(type(system_page), "system_os")
        assert os_label is not None
        assert os_label.text()  # nicht leer
        window.close()

    def test_system_page_shows_gpu_info(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 4)
        system_page = window.system_page
        gpu_label = system_page.findChild(type(system_page), "system_gpu")
        assert gpu_label is not None
        window.close()

    def test_redetect_button_updates_info(self, qtbot, gui_with_installs, monkeypatch):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 4)
        system_page = window.system_page
        called = [False]
        def fake_detect():
            called[0] = True
            return {"os": "TestOS", "python": "3.14", "nvidia_smi": "nvidia-smi",
                    "vulkaninfo": "vulkaninfo", "steam_available": True}
        monkeypatch.setattr(system_page, "_run_detect", fake_detect)
        click_button(system_page, "redetect_button")
        qtbot.wait_until(lambda: called[0] is True, timeout=5000)
        window.close()
```

2. `tests_e2e/test_rollbacks.py`:
```python
import pytest
from dlls_manager.gui.main_window import MainWindow
from tests_e2e.support import click_button, select_sidebar_item


class TestRollbacksPage:
    def test_empty_rollbacks_shows_message(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        select_sidebar_item(window, 3)
        rollbacks_page = window.rollbacks_page
        assert rollbacks_page.rollback_table.rowCount() == 0
        empty_label = rollbacks_page.findChild(type(rollbacks_page), "empty_state_label")
        assert empty_label is not None
        assert empty_label.isVisible()
        window.close()

    def test_rollbacks_appear_after_apply(self, qtbot, gui_with_installs):
        window = MainWindow()
        qtbot.addWidget(window)
        # Erst Apply durchführen (wie in test_workflow)
        library_page = window.library_page
        library_page.install_list.setCurrentRow(0)
        detail = library_page.detail_panel
        from tests_e2e.support import select_combobox, check_checkbox
        select_combobox(detail, "dlss_version_select", "3.7.20")
        check_checkbox(detail, "override_sync_launcher", False)
        click_button(detail, "save_override_button")
        click_button(detail, "apply_button")
        qtbot.wait(500)

        # Zu Rollbacks navigieren
        select_sidebar_item(window, 3)
        rollbacks_page = window.rollbacks_page
        assert rollbacks_page.rollback_table.rowCount() >= 1
        window.close()
```

3. Run: `python3 -m pytest tests_e2e/test_system.py tests_e2e/test_rollbacks.py -v -m e2e` — expected: 5 passed

**Commit:** `test: add E2E system and rollbacks page tests`

---

### Task 47: pytest.ini und Marker konfigurieren

**Objective:** Test-Marker und CI-Runner-Konfiguration

**Files:**
- Create: `pytest.ini` (oder in pyproject.toml)

**Steps:**

1. `pytest.ini`:
```ini
[pytest]
markers =
    unit: Unit tests — domain layer, isolated, fast
    smoke: Smoke tests — app launch, CLI, import checks
    e2e: End-to-end GUI tests — pytest-qt interaction with PySide6 widgets
qt_api = pyside6
log_cli = true
log_cli_level = INFO
testpaths = tests tests_smoke tests_e2e
addopts = --strict-markers
```

2. Run: `python3 -m pytest --markers` — expected: unit, smoke, e2e markers gelistet

3. Run alle Tests: `python3 -m pytest -v` — expected: alle Tests grün (außer bewusst entfernte webUI-Tests)

4. Run nach Kategorie:
```bash
python3 -m pytest -m unit -v       # Domain-Layer Unit Tests
python3 -m pytest -m smoke -v      # Smoke Tests
python3 -m pytest -m e2e -v        # GUI E2E Tests (braucht Display — Xvfb für CI)
```

**Commit:** `test: configure pytest markers and test runner`

---

### Task 48: CI-Integration — GitHub Actions Workflow

**Objective:** CI-Pipeline die Unit, Smoke und E2E Tests ausführt

**Files:**
- Create: `.github/workflows/test.yml`

**Steps:**

1. Workflow:
```yaml
name: Tests
on: [push, pull_request]
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: python -m pytest tests/ -m unit -v --tb=short

  smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: python -m pytest tests_smoke/ -m smoke -v --tb=short

  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: sudo apt-get install -y xvfb
      - run: xvfb-run -a python -m pytest tests_e2e/ -m e2e -v --tb=short
```

2. Verify lokal: `xvfb-run python3 -m pytest tests_e2e/ -m e2e -v` (falls headless)

**Commit:** `ci: add GitHub Actions test workflow (unit, smoke, e2e)`

---

### Task 49: Xvfb-Wrapper-Script für lokale E2E-Tests

**Objective:** Einfaches Script um E2E-Tests lokal ohne Display zu starten

**Files:**
- Create: `scripts/run_tests.sh`

**Steps:**

1. Script:
```bash
#!/usr/bin/env bash
set -eu
VENV="${VENV:-.venv}"
echo "=== Unit Tests ==="
$VENV/bin/python -m pytest tests/ -m unit -v --tb=short
echo ""
echo "=== Smoke Tests ==="
$VENV/bin/python -m pytest tests_smoke/ -m smoke -v --tb=short
echo ""
echo "=== E2E GUI Tests (Xvfb) ==="
if command -v xvfb-run &>/dev/null; then
    xvfb-run -a $VENV/bin/python -m pytest tests_e2e/ -m e2e -v --tb=short
else
    echo "xvfb-run not found — trying direct (needs DISPLAY)"
    $VENV/bin/python -m pytest tests_e2e/ -m e2e -v --tb=short
fi
echo ""
echo "=== All Done ==="
```

2. `chmod +x scripts/run_tests.sh`

3. Run: `./scripts/run_tests.sh`

**Commit:** `test: add unified test runner script`

---

## Test-Matrix Zusammenfassung

| Test-Ebene | Verzeichnis | Framework | Display nötig | Anzahl Tests | CI-Job |
|-----------|------------|-----------|--------------|-------------|--------|
| Unit | `tests/` | pytest + unittest-kompatibel | Nein | ~40 | `unit` |
| Smoke | `tests_smoke/` | pytest + subprocess | Nein (außer GUI-Import) | ~8 | `smoke` |
| E2E GUI | `tests_e2e/` | pytest + pytest-qt | Ja (Xvfb) | ~28 | `e2e` |

**Total: ~76 Tests** decken alle Features ab:

- Domain-Layer: DLSS Multi-DLL-Extraktion, Preset-Env-Vars, Catalog-State, Proton-Detection, Blacklist
- CLI: Help, detect, list-profiles, list-dlss-catalog, list-installs, removed commands
- GUI: Navigation (5 Pages), Library (Cards, Detail, Search, Blocked), Catalog (Tabelle, Download, Refresh), Profiles (Form, Presets, Save), Rollbacks (List, Execute), System (Info, Redetect)
- Workflow: Override → Apply → DLL-Swap → Rollback → DLL-Restore, Dry-Run, Blocked-Install

## Erweiterte Priorisierung (mit Tests)

**Phase 1 (Kern):** Tasks 1-5 (WebUI entfernen) + Tasks 11-13 (GUI-Gerüst)
**Phase 2 (Features):** Tasks 6-10 (DLSS Domain Update) + Tasks 14-20 (GUI-Pages)
**Phase 3 (Polish):** Tasks 21-22 (Theme + Async) + Tasks 27-29 (Domain-Verbesserungen)
**Phase 4 (Distribution):** Tasks 23-26 (Packaging) + Task 31 (Docs)
**Phase 5 (Tests):** Tasks 32-49 (Unit + Smoke + E2E + CI)
  - Task 32-38 parallel zu Phase 2 (sobald Domain-Feature existiert, Test schreiben)
  - Task 39 parallel zu Phase 1 (smoke test import-checks)
  - Task 40-46 parallel zu Phase 2 (sobald GUI-Page existiert, E2E-Test schreiben)
  - Task 47-49 am Ende (nachdem alle anderen Tasks laufen)