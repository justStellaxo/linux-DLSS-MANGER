# Phase 2 Launcher Research

Stand: 2026-04-17

## Ziel

Phase 2 soll den Prototypen von einem reinen Steam-/Mock-Planer zu einem launcher-agnostischen Manager ausbauen, der reale lokale Installationen erkennen, klassifizieren und mit Policy-/DLSS-Logik verknuepfen kann.

Die Recherche hier deckt ab:

- deine lokalen Faelle: Faugus/Battle.net/WoW und RSI Launcher/Star Citizen
- Linux-relevante Launcher- und Installationsmethoden
- welche Adapterfamilien wir technisch brauchen
- welche Launcher zuerst eingebaut werden sollten

## Kurzfazit

Es ist weder sinnvoll noch stabil, fuer jeden Launcher eine komplett eigene Speziallogik tief im Kern zu verdrahten.

Die richtige Architektur ist:

1. ein gemeinsames `GameInstallRecord`/`LauncherInstallRecord` Modell
2. Discovery-Adapter pro Oekosystem
3. Execution-Adapter pro Startmethode
4. eine zentrale Policy-Engine, die launcher-unabhaengig arbeitet

So decken wir nicht nur Steam ab, sondern auch:

- Faugus / UMU
- Star Citizen LUG / RSI Script-Launch
- Heroic
- Lutris
- Bottles
- native Linux launcher/scripts/.desktop
- Windows-Launcher in Wine/Proton Prefixen wie Battle.net, EA App, Ubisoft Connect, Rockstar

## Lokale Befunde auf deinem System

### Faugus / Battle.net

Deine lokale Desktop-Datei:

- `~/.local/share/applications/battlenet-no-vpn.desktop`
- `Exec=/usr/bin/mullvad-exclude /usr/bin/faugus-run --game battlenet`

Deine Faugus-Konfiguration:

- `~/.config/faugus-launcher/config.ini`
- Default Prefix: `/home/stella/Faugus`
- Runner Default: `Proton-GE Latest`
- global aktiv: `mangohud=True`, `gamemode=True`

Dein Battle.net-Eintrag in Faugus:

- `~/.config/faugus-launcher/games.json`
- `gameid`: `battlenet`
- `path`: `/mnt/nvme0/faugus-battlenet/drive_c/Program Files (x86)/Battle.net/Battle.net.exe`
- `prefix`: `/mnt/nvme0/faugus-battlenet`
- `launch_arguments`: `WINE_SIMULATE_WRITECOPY=1 PROTON_ENABLE_WAYLAND=0`
- `runner`: `Proton-GE Latest`
- `lossless_enabled`: `true`

Verifizierter Dateistatus im Prefix:

- `Battle.net.exe` existiert
- `Battle.net Launcher.exe` existiert
- ein referenzierter `addapp_bat` Pfad ist in `games.json` eingetragen, war aber nicht vorhanden

Wichtige Schlussfolgerung:

- Faugus ist fuer uns eine prima Discovery-Quelle
- Faugus-Daten duerfen aber nicht blind als gueltig angenommen werden
- jeder importierte Pfad muss vor Nutzung validiert werden
- Launcher-Exec-Ketten koennen Wrapper enthalten, z. B. `mullvad-exclude`

### RSI / Star Citizen

Gefundene lokale Dateien:

- `~/.config/starcitizen-lug/gamedir.conf`
- `~/.config/starcitizen-lug/winedir.conf`
- `~/.local/share/applications/rsi launcher.exe.desktop`
- `~/.local/share/applications/starcitizen.exe.desktop`
- `/mnt/nvme1/GAMES/StarCitizen/star-citizen/sc-launch.sh`

Dein lokaler RSI-Launcher-Desktop-Entry:

- `Exec=/usr/bin/mullvad-exclude "/mnt/nvme1/GAMES/StarCitizen/star-citizen/sc-launch.sh"`

Dein LUG-Setup:

- `WINEPREFIX="/mnt/nvme1/GAMES/StarCitizen/star-citizen"`
- eigener Wine-Runner:
  `/mnt/nvme1/GAMES/StarCitizen/star-citizen/runners/lug-wine-tkg-git-11.5-1/bin`
- Launchziel im Script:
  `C:\Program Files\Roberts Space Industries\RSI Launcher\RSI Launcher.exe`

Wichtige Schlussfolgerung:

- Star Citizen ist bei dir kein normaler "launcher exe in generic prefix", sondern ein script-gesteuerter Wine-Stack
- wir brauchen dafuer einen `script_exec` Adapter, nicht nur `wine_exe`
- auch hier existiert eine Wrapper-Kette mit `mullvad-exclude`

## Online-Recherche

### 1. UMU / Faugus

Faugus beschreibt sich auf Flathub als "simple and lightweight app for running games using UMU-Launcher" und nennt als Hauptfunktionen:

- Windows-Spiele mit Proton starten
- Linux-native Spiele starten
- Windows-Spiele direkt aus `.exe` starten
- Prefix-Management
- Shortcut- und Steam-Shortcut-Management

Quelle:

- https://flathub.org/apps/io.github.Faugus.faugus-launcher

UMU selbst beschreibt sich als "Unified launcher for Windows games on Linux" und erklaert explizit, dass andere Launcher wie Lutris, Bottles, Heroic und Legendary denselben Unterbau benutzen koennen.

Wichtige Punkte aus dem UMU-README:

- Launcher koennen `WINEPREFIX`, `GAMEID`, `STORE`, `PROTONPATH` und Ziel-Executable an `umu-run` uebergeben
- Ziel ist ein gemeinsamer Proton-/Fixup-Unterbau fuer mehrere Launcher
- keine Steam-Binaries sind dafuer zwingend noetig

Quelle:

- https://github.com/Open-Wine-Components/umu-launcher

Praktische Bedeutung fuer unser Projekt:

- Faugus ist kein exotischer Sonderfall, sondern eine konkrete Auspraegung einer allgemeinen UMU/Proton-Launch-Methode
- wenn wir einen soliden `umu_exec` oder `generic_prefix_exec` Adapter bauen, profitieren mehrere Oekosysteme

### 2. Star Citizen / RSI

RSI selbst dokumentiert den Windows-Launcher als offiziellen Einstiegspunkt fuer Star Citizen.

Quelle:

- https://support.robertsspaceindustries.com/hc/en-us/articles/115013373508-Install-the-RSI-Star-Citizen-Launcher

Linux wird dort nicht als offizieller eigener Client beschrieben. Fuer Linux existiert aber mit der Star Citizen Linux Users Group eine etablierte Community-Loesung:

- Installation per Wine
- Pflege der Launch-Skripte
- Re-Install des RSI Launchers
- Wine Prefix Tools
- Custom Runner / DXVK Management

Quellen:

- https://github.com/starcitizen-lug/lug-helper
- https://github.com/starcitizen-lug/knowledge-base

Praktische Bedeutung:

- Star Citizen sollte nicht in die gleiche Schublade wie Battle.net/EA/Ubisoft gesteckt werden
- es braucht einen eigenen Adapterpfad fuer LUG-/Script-basierte Installationen

### 3. Heroic

Heroic dokumentiert offiziell:

- Login fuer Epic, GOG und Amazon
- Installieren, Deinstallieren, Updaten, Reparieren und Verschieben
- Import bereits installierter Spiele
- Wine-/Proton-Start auf Linux
- benutzerdefinierte Wine-/Proton-Versionen
- Hinzufuegen externer Spiele und Anwendungen

Heroic nennt als Backend:

- Epic via Legendary
- GOG via gogdl
- Amazon via Nile

Quelle:

- https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher

Praktische Bedeutung:

- Heroic ist kein Launcher fuer nur einen Store, sondern ein Meta-Launcher
- fuer uns ist Heroic daher einer der wichtigsten Adapter nach Steam
- wenn wir Heroic importieren, decken wir mit einem Schlag Epic, GOG und Amazon-Faelle ab

### 4. Legendary / GOG Download Backends

Legendary dokumentiert:

- `legendary install`
- `legendary launch`
- `legendary import`
- `legendary launch <App Name> --offline --dry-run` fuer die exakte Launch-Command-Ermittlung

Quelle:

- https://github.com/legendary-gl/legendary

Praktische Bedeutung:

- selbst ohne Heroic-UI koennen Epic-Installationen technisch importiert und gestartet werden
- `--dry-run` ist besonders wertvoll fuer unsere Launch-Preview- und Snapshot-Logik

### 5. Lutris

Lutris beschreibt offiziell:

- Integration mit Battle.net, Epic Games Store, EA App und Ubisoft Connect
- CLI-Optionen zum Auflisten installierter Spiele
- `lutris:` Protokoll-Links zum Installieren oder Starten
- Export als Bash-Script

Quellen:

- https://lutris.net/about
- https://github.com/lutris/lutris
- Battle.net Seite auf Lutris: https://lutris.net/games/battlenet/

Praktische Bedeutung:

- Lutris ist fuer Wine-Launcher-Faelle ein zentrales Discovery-Ziel
- die Bash-Script-Ausgabe und CLI sind fuer unseren Adapter besonders interessant
- der `lutris:` URI/CLI-Pfad erlaubt eine launcher-eigene Startmethode ohne unseren Kern zu verkomplizieren

### 6. Bottles

Bottles dokumentiert:

- `bottles-cli`
- `run` zum Starten eines Programms oder einer Executable in einer Bottle
- `new`, `edit`, `programs`, `tools`
- eigenes URL-Schema: `bottles:run/<bottle>/<program>`

Quellen:

- https://docs.usebottles.com/advanced/cli
- https://docs.usebottles.com/advanced/xdg-open

Praktische Bedeutung:

- Bottles ist fuer uns sauber ueber CLI oder URL-Schema integrierbar
- kein vendor-spezifisches Reverse Engineering noetig
- Bottles ist deshalb ein sehr guter Adapterkandidat fuer Phase 2

### 7. Vendor-Launcher: Battle.net, EA App, Ubisoft Connect, Rockstar, GOG Galaxy

#### Battle.net

Blizzard dokumentiert die Battle.net Desktop App als zentrale Install-/Patch-/Launch-Anwendung.

Quelle:

- https://us.support.blizzard.com/en/help/article/000025949

Blizzard sagt fuer Linux laut Supportartikel sinngemaess:

- keine native Linux-Unterstuetzung
- keine Plaene fuer Linux-Kompatibilitaet der Spiele oder der Battle.net Desktop App

Quelle:

- https://us.support.blizzard.com/en/article/11571

Der Battle.net-Launcher selbst ist also offiziell kein Linux-Produkt. Auf Linux laeuft er praktisch ueber Wine/Proton/Faugus/Lutris/Bottles.

#### EA App

EA dokumentiert:

- EA App fuer Windows
- EA App fuer Mac
- bei EA-Spielen auf Steam/Epic wird auf dem PC die EA App benoetigt

Quellen:

- https://www.ea.com/ea-app
- https://help.ea.com/en/articles/platforms/ea-app-download-install-update/

Praktische Bedeutung:

- auf Linux ist EA App ebenfalls ein Wine-/Proton-Fall
- wir sollten EA nicht als nativen Linux-Adapter planen, sondern als `vendor_launcher_in_prefix`

#### Ubisoft Connect

Ubisoft dokumentiert Ubisoft Connect als Desktop-App fuer PC und Konsole.

Quellen:

- https://www.ubisoft.com/en-us/ubisoft-connect/
- https://www.ubisoft.com/en-us/ubisoft-connect/download

Praktische Bedeutung:

- auf Linux ebenfalls ein Prefix-/Wine-/Proton-Fall
- ueber Lutris/Bottles/Faugus oder generischen Prefix-Adapter abbildbar

#### Rockstar Games Launcher

Rockstar dokumentiert den Launcher als Download und als Trager fuer Download, Installation, Updates und Start aus dem Dashboard.

Quellen:

- https://support.rockstargames.com/articles/4extB4aITvMKdDEZzsFAwE/rockstar-games-launcher-download
- https://support.rockstargames.com/articles/7jx7g9dNttPjsQAeDDPv1F/feature-support-for-rockstar-games-launcher-titles

Praktische Bedeutung:

- auch hier kein Linux-Nativpfad
- Integration als Prefix-/Wine-Launcher mit Discovery ueber Lutris/Bottles/generische Prefix-Erkennung

#### GOG Galaxy

GOG Galaxy ist offiziell Windows/macOS-orientiert und beschreibt sich als Bibliotheksaggregator mit Integrationen.
Wichtig fuer uns: GOG sagt selbst, dass fuer Plattformfunktionen wie Installation, Updates und Cloud oft die jeweiligen anderen Clients noetig sind.

Quelle:

- https://www.gog.com/galaxy

Praktische Bedeutung:

- auf Linux ist Heroic oder Minigalaxy meist die bessere Integrationsbasis
- GOG Galaxy selbst sollte spaeter als Sonderfall behandelt werden, nicht als fruehe Prioritaet

### 8. Native Linux Launcher

#### itch.io

itch.io bietet die App offiziell fuer Linux an.

Quelle:

- https://itch.io/app

Praktische Bedeutung:

- itch ist ein echter nativer Linux-Launcher-Fall
- dafuer brauchen wir eher einen `desktop_exec`/`native_exec` Adapter als Wine-Logik

#### Minigalaxy

Minigalaxy beschreibt sich als einfacher GOG-Client fuer Linux und unterstuetzt:

- Login mit GOG
- Linux-Spiele herunterladen und starten
- Windows-Spiele via Wine installieren

Quelle:

- https://github.com/sharkwouter/minigalaxy

Praktische Bedeutung:

- Minigalaxy ist fuer Linux/GOG ebenfalls ein valider Discovery- und Startpfad
- es sollte in dieselbe Adapterfamilie wie Heroic/Bottles/Lutris eingeordnet werden: importierbare lokale Metadaten plus standardisierte Startpunkte

## Was das fuer DLLS-Manager bedeutet

## Nicht nach "Launcher-Name", sondern nach "Startmethode" modellieren

Der Kernfehler waere, nur Felder wie `launcher = steam|heroic|lutris|faugus|rsi` einzubauen.

Wir brauchen stattdessen zwei Ebenen:

### A. Discovery Source

Woher stammt die Installation?

- `steam`
- `faugus`
- `starcitizen_lug`
- `heroic`
- `lutris`
- `bottles`
- `desktop_entry`
- `manual`

### B. Execution Strategy

Wie wird wirklich gestartet?

- `steam_app`
- `steam_shortcut`
- `umu_game`
- `lutris_game`
- `bottles_program`
- `heroic_game`
- `legendary_game`
- `script_exec`
- `desktop_exec`
- `wine_exe`
- `native_exe`

Damit koennen zwei verschiedene Discovery-Wege auf dieselbe Startmethode zeigen.

Beispiel:

- Battle.net in Faugus: Discovery `faugus`, Execution `umu_game`
- Battle.net in Lutris: Discovery `lutris`, Execution `lutris_game`
- Star Citizen LUG: Discovery `starcitizen_lug`, Execution `script_exec`

## Konkreter Ausbauplan fuer Phase 2

### 1. Datenmodell erweitern

Neue Felder fuer `GameRecord` oder ein neues `LauncherInstallRecord`:

- `source`
- `source_id`
- `launcher_family`
- `store_family`
- `execution_strategy`
- `display_name`
- `install_root`
- `prefix_path`
- `runner_name`
- `runner_path`
- `exe_path`
- `script_path`
- `launch_command`
- `launch_env`
- `wrapper_chain`
- `working_directory`
- `discovery_confidence`
- `metadata_file`
- `last_validated_at`
- `validation_errors`
- `anti_cheat_vendor`
- `anti_cheat_policy`
- `supports_dlss_override`
- `supports_dlss_version_selection`

### 2. Discovery-Adapter bauen

Empfohlene Reihenfolge:

1. `steam_discovery.py`
2. `faugus_discovery.py`
3. `starcitizen_lug_discovery.py`
4. `heroic_discovery.py`
5. `lutris_discovery.py`
6. `bottles_discovery.py`
7. `desktop_entry_discovery.py`

### 3. Execution-Adapter bauen

Empfohlene Reihenfolge:

1. `steam_adapter.py`
2. `script_exec_adapter.py`
3. `desktop_exec_adapter.py`
4. `umu_exec_adapter.py`
5. `lutris_exec_adapter.py`
6. `bottles_exec_adapter.py`
7. `heroic_exec_adapter.py`
8. `wine_exe_adapter.py`

### 4. Import-/Validierungslogik

Jeder Import muss pruefen:

- existiert die referenzierte Executable noch?
- existiert das Script noch?
- existiert der Prefix noch?
- stimmen Runner- und Prefix-Pfade?
- ist ein Wrapper wie `mullvad-exclude` oder `gamescope` Teil der echten Launch-Kette?

### 5. Policy-/DLSS-Schicht nicht aufbrechen

Die existierende Policy-Engine bleibt zentral.
Sie bekommt nur mehr Fakten aus den Discovery-Adaptern:

- launcher family
- runtime family
- native vs Wine/Proton
- Anti-Cheat Marker im Prefix oder Install Root
- bekannte Launcher-spezifische Risiken

## Prioritaeten fuer dein System

Die naechsten Adapter sollten nicht abstrakt gewaehlt werden, sondern nach deinem echten Bestand:

1. Faugus / Battle.net / WoW
2. Star Citizen LUG / RSI Script-Launch
3. generischer Desktop-/Script-Launch mit Wrapper-Ketten
4. Heroic
5. Lutris
6. Bottles

Warum diese Reihenfolge?

- Battle.net und RSI sind bereits real auf deinem System vorhanden
- beide zeigen wichtige Architekturfaelle:
  - Wrapper-Kette
  - eigener Prefix
  - eigener Runner
  - Script statt direkter `.exe`
- wenn diese beiden funktionieren, ist der Rest des Launcher-Ausbaus deutlich sauberer

## Konkrete Implementierung fuer den aktuellen Codebestand

### Neue Python-Module

Empfohlen:

- `dlls_manager/discovery/base.py`
- `dlls_manager/discovery/steam.py`
- `dlls_manager/discovery/faugus.py`
- `dlls_manager/discovery/starcitizen_lug.py`
- `dlls_manager/discovery/heroic.py`
- `dlls_manager/discovery/lutris.py`
- `dlls_manager/discovery/bottles.py`
- `dlls_manager/discovery/desktop_entries.py`
- `dlls_manager/execution/base.py`
- `dlls_manager/execution/script_exec.py`
- `dlls_manager/execution/desktop_exec.py`
- `dlls_manager/execution/umu_exec.py`

### Bestehende Dateien, die erweitert werden sollten

- `dlls_manager/models.py`
  - neues Installations-/Launcher-Modell
- `dlls_manager/launch_plan.py`
  - launcher-agnostische Command-Assembly
- `dlls_manager/detector.py`
  - Launcher-/Store-Availability Flags
- `dlls_manager/mock_data.py`
  - Anzeige realer lokaler Installationen statt nur statischer Beispielspiele
- `mock_ui/`
  - Filter nach Quelle, Launcher, Store, Runtime, Policy

### Neue CLI-Kommandos

Empfohlen:

- `python3 main.py discover-launchers`
- `python3 main.py list-installs`
- `python3 main.py validate-install <id>`
- `python3 main.py launch-preview <install_id> --profile <profile>`
- spaeter:
  `python3 main.py launch <install_id> --profile <profile>`

## Risiken und Grenzen

- "Alles abdecken" heisst realistisch: alle relevanten Startmethoden abdecken, nicht jedes einzelne Launcher-Branding hart einkodieren.
- Vendor-Launcher wie Battle.net, EA App, Ubisoft Connect und Rockstar sind auf Linux offiziell keine First-Class-Produkte; ihre Stabilitaet unter Wine/Proton kann sich jederzeit durch Updates aendern.
- Anti-Cheat-Sicherheit bleibt titel- und launcher-spezifisch.
- Wrapper wie `mullvad-exclude`, `gamescope`, `gamemoderun`, `mangohud` und eigene Scripts muessen als Teil der Launch-Kette modelliert werden.

## Empfehlung fuer den naechsten Umsetzungsschritt

Phase 2 sollte jetzt nicht mit "noch mehr Mock-UI" beginnen, sondern mit echter lokaler Discovery.

Die naechste sinnvolle Implementierung ist:

1. neues Install-/Launcher-Datenmodell
2. `discover-launchers` CLI
3. Faugus-Discovery
4. Star-Citizen-LUG-Discovery
5. Anzeige dieser echten Installationen in der UI

Danach erst:

6. Heroic/Lutris/Bottles Import
7. echte launcher-agnostische Launch-Preview
8. spaetere Ausfuehrungsadapter

## Quellen

- Faugus Launcher auf Flathub:
  https://flathub.org/apps/io.github.Faugus.faugus-launcher
- Faugus GitHub:
  https://github.com/Faugus
- UMU Launcher:
  https://github.com/Open-Wine-Components/umu-launcher
- RSI Launcher Install Guide:
  https://support.robertsspaceindustries.com/hc/en-us/articles/115013373508-Install-the-RSI-Star-Citizen-Launcher
- Star Citizen LUG Helper:
  https://github.com/starcitizen-lug/lug-helper
- Star Citizen LUG Knowledge Base:
  https://github.com/starcitizen-lug/knowledge-base
- Heroic Games Launcher:
  https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher
- Legendary:
  https://github.com/legendary-gl/legendary
- Bottles CLI:
  https://docs.usebottles.com/advanced/cli
- Bottles xdg-open links:
  https://docs.usebottles.com/advanced/xdg-open
- Lutris About:
  https://lutris.net/about
- Lutris GitHub:
  https://github.com/lutris/lutris
- Lutris Battle.net page:
  https://lutris.net/games/battlenet/
- EA App:
  https://www.ea.com/ea-app
- EA Help:
  https://help.ea.com/en/articles/platforms/ea-app-download-install-update/
- Ubisoft Connect:
  https://www.ubisoft.com/en-us/ubisoft-connect/
- Ubisoft Connect Download:
  https://www.ubisoft.com/en-us/ubisoft-connect/download
- Rockstar Launcher Download:
  https://support.rockstargames.com/articles/4extB4aITvMKdDEZzsFAwE/rockstar-games-launcher-download
- Rockstar Launcher Features:
  https://support.rockstargames.com/articles/7jx7g9dNttPjsQAeDDPv1F/feature-support-for-rockstar-games-launcher-titles
- GOG Galaxy:
  https://www.gog.com/galaxy
- itch.io App:
  https://itch.io/app
- Minigalaxy:
  https://github.com/sharkwouter/minigalaxy
