# reTerminal Dashboard Designer

A fully integrated Home Assistant custom integration and ESPHome helper
for building multi-page 800x480 dashboards on the Seeed Studio
reTerminal E1001 (ESP32-S3 E-Ink variant).

This project provides:
- A visual layout editor (web UI) running inside Home Assistant.
- Real-time entity picker with live entity state preview.
- A YAML snippet generator running on your Home Assistant instance.
- A safe, additive workflow:
  - You maintain your own base ESPHome config (WiFi, API, etc).
  - The designer adds display, pages, widgets, and device exposure on top.

## Features

Core behavior:

- Home Assistant custom integration (`reterminal_dashboard`) with:
  - Storage for a layout configuration (pages and widgets) in JSON.
  - Integrated visual editor panel accessible at `/reterminal-dashboard`.
  - Real-time entity picker with search and filtering.
  - Live entity state preview in the visual editor canvas.
  - HTTP API endpoints (all local to Home Assistant) for:
    - `GET /api/reterminal_dashboard/layout`
      - Get the current layout JSON.
    - `POST /api/reterminal_dashboard/layout`
      - Update the layout JSON.
    - `GET /api/reterminal_dashboard/entities`
      - Get available Home Assistant entities for the picker.
    - `GET /api/reterminal_dashboard/snippet`
      - Generate an ESPHome YAML snippet from the stored layout.
    - `POST /api/reterminal_dashboard/import_snippet`
      - Import a compatible ESPHome YAML snippet and reconstruct the layout.
- YAML snippet generator:
  - Implemented in [`custom_components/reterminal_dashboard/yaml_generator.py`](custom_components/reterminal_dashboard/yaml_generator.py:1)
  - Produces additive YAML only:
    - Does NOT emit:
      - `esphome:`
      - `esp32:`
      - `wifi:`
      - `api:`
      - `ota:`
      - `logger:`
    - Emits:
      - `globals:` for:
        - `display_page` (current page index).
        - `page_refresh_default_s` (base refresh interval).
      - `font:` definitions for display text.
      - `output:` and `rtttl:` for battery power enable and buzzer.
      - Example `sensor:` and `text_sensor:` entries (battery, wifi, etc).
      - `button:` entities for:
        - Next page, previous page.
        - Manual refresh trigger.
      - `time:` + `script:`:
        - A `manage_run_and_sleep`-style loop that refreshes the display.
        - Designed so per-page refresh overrides can be generated from layout metadata.
      - `display:` block with:
        - `id: epaper_display`
        - Proper driver/model configuration for the reTerminal E-Ink.
        - `rotation:` honoring the selected orientation.
        - `lambda:` that:
          - Reads `display_page`.
          - Renders each configured page and its widgets using native ESPHome primitives.
- Safety and design:
  - Safe: no secrets, no overlapping base keys.
  - Deterministic: same layout results in stable YAML.
  - Extensible: widget model and generator are structured for more devices/features.

## Repository Structure

- `custom_components/reterminal_dashboard/`
  - `__init__.py`:
    - Bootstraps the integration, initializes storage, registers HTTP API, services, and panel view.
  - `manifest.json`:
    - Integration metadata (HACS-compatible).
  - `const.py`:
    - Constants (domain, canvas size, API paths).
  - `models.py`:
    - `WidgetConfig`, `PageConfig`, `DeviceConfig`, `DashboardState`.
    - Internal representation of pages and widgets.
  - `storage.py`:
    - `DashboardStorage` wrapping Home Assistant Store.
  - `services.py`:
    - Services for navigation / helpers (optional with snippet flow).
  - `renderer.py`:
    - Legacy PNG renderer (kept for reference; not required for YAML snippet workflow).
  - `http_api.py`:
    - HTTP views for:
      - `GET/POST /api/reterminal_dashboard/layout` (layout CRUD for the editor).
      - `GET /api/reterminal_dashboard/entities` (entity list for picker).
      - `GET /api/reterminal_dashboard/snippet` (YAML snippet export).
      - `POST /api/reterminal_dashboard/import_snippet` (YAML snippet import → layout).
  - `panel.py`:
    - Panel view serving the visual editor at `/reterminal-dashboard`.
    - Automatically loaded by Home Assistant when integration is installed.
  - `config_flow.py`:
    - Single-instance config flow / setup.
  - `yaml_generator.py`:
    - YAML snippet generator for the reTerminal E1001, based on the internal layout.
  - `yaml_parser.py`:
    - Server-side snippet-to-layout parser used by `/import_snippet`.
  - `frontend/`:
    - `editor.html`:
      - Complete visual layout editor UI bundled with the integration.
      - Features entity picker, live state preview, drag-drop canvas, and property editor.
    - `materialdesignicons-webfont.ttf`:
      - MDI icon font for widget previews.

- `esphome/`
  - `reterminal_e1001_generic.yaml`:
    - Example base ESPHome firmware for reTerminal E1001 (you own WiFi/api/etc).

- `resources/ESPHome Reterminal/`
  - `reterminalE-1001-esphome.txt`:
    - Reference ESPHome configuration used as inspiration/baseline.

- `hacs.json`:
  - HACS repository metadata.

## Recommended Workflow

### 1. Flash a Basic ESPHome Config (User Responsibility)

You manage the initial provisioning yourself. Example:

1. In ESPHome, create a new device for your reTerminal E1001.
2. Use `esphome/reterminal_e1001_generic.yaml` as a starting point, or your own:
   - Define:
     - `esphome:`
     - `esp32:` (correct board)
     - `wifi:`
     - `api:`
     - `ota:`
     - `logger:`
3. Flash this base config to the device.
4. Confirm:
   - It is online in ESPHome / Home Assistant.
   - Basic connectivity works.

This base config is where your secrets (WiFi, API key) live. The designer does not
touch or generate those pieces.

### 2. Install Integration via HACS

1. In Home Assistant:
   - `HACS` → `Integrations`.
2. Add this repository as custom:
   - Category: `Integration`.
3. Install `reTerminal Dashboard Designer`.
4. Restart Home Assistant.
5. Add the integration via:
   - `Settings` → `Devices & services` → `+ Add Integration` → `reTerminal Dashboard Designer`.

At this point:

- The backend is ready.
- Layout storage and HTTP APIs are available.

### 3. Design Your Layout

MVP options:

- Option A: Home Assistant / HACS (recommended)

  - Use `www/reterminal_dashboard_panel/editor.html` as a panel within Home Assistant
    (via this integration or `panel_iframe`).
  - In this mode the editor:
    - Loads current layout via:
      - `GET /api/reterminal_dashboard/layout`
    - Saves updates via:
      - `POST /api/reterminal_dashboard/layout`
    - Generates ESPHome snippets via:
      - `GET /api/reterminal_dashboard/snippet`
    - Can import snippets (round-trip) via:
      - `POST /api/reterminal_dashboard/import_snippet`
        - Uses the full server-side `yaml_parser` for robust parsing.

- Option B: Standalone / offline usage

  - Open `www/reterminal_dashboard_panel/editor.html` directly (e.g. `file:///...`).
  - In this mode:
    - No Home Assistant backend is required.
    - Layout is kept in-memory in the browser (no HA storage).
    - The "Import" action:
      - Uses a small client-side parser to read an ESPHome `display` `lambda:` block.
      - Recognizes basic drawing primitives:
        - `it.rectangle(...)`
        - `it.filled_rectangle(...)`
        - `it.circle(...)`
        - `it.filled_circle(...)`
        - `it.line(...)`
        - Including forms that use `COLOR_OFF` as last parameter.
      - Reconstructs corresponding shape widgets and populates the canvas as a local preview.
      - Is tolerant of the project’s own “Local preview snippet (fallback)” wrapper comments.
    - The "Generate ESPHome snippet" action:
      - Produces a local preview snippet suitable for pasting below your base ESPHome config.
      - When no backend is reachable, includes comments indicating that it is a fallback/local preview.
    - This gives you an entirely offline, file-based way to iterate on layouts.

The layout (in HA-backed mode) is stored as:

- Device/pages/widgets in the structures defined in
  [`custom_components/reterminal_dashboard/models.py`](custom_components/reterminal_dashboard/models.py:1).

### 4. Generate the ESPHome YAML Snippet

When running inside Home Assistant with the integration:

- Endpoint:
  - `GET /api/reterminal_dashboard/snippet`

Behavior:

- Uses [`yaml_generator.py`](custom_components/reterminal_dashboard/yaml_generator.py:1)
  to convert the stored layout into a snippet.

Conceptually, the snippet includes:

- `globals` for `display_page` and related control values.
- `font` definitions.
- `output` and `rtttl` for buzzer/battery.
- Example `sensor` and `text_sensor` entries.
- `button` entities for:
  - Next page
  - Previous page
  - Refresh display
- `time` and `script` for periodic or managed refresh.
- `display` block with:
  - `id: epaper_display`
  - A `lambda:` that:
    - Reads `display_page`.
    - Renders each configured page and its widgets.

At the top of the snippet you will see comments like:

- `# Generated by reTerminal Dashboard Designer`
- `# Paste below your existing base ESPHome config`
- `# Do not duplicate esphome:, wifi:, api:, ota:, logger: sections`

### 5. Paste Snippet into Your ESPHome YAML

1. Open your existing ESPHome YAML for the reTerminal.
2. Scroll to the end of your base config.
3. Paste the generated snippet below it.
4. Ensure there are no conflicting IDs or duplicate sections.
5. Recompile and flash via ESPHome.

Your device will now:

- Use your base WiFi/API/OTA configuration.
- Use the layout, buttons, buzzer and scripts from the generated snippet.
- Expose additional entities in Home Assistant (buttons, sensors, etc) for automations.

## Exposure of reTerminal Hardware

The snippet is designed (and will be refined) so that:

- Buttons:
  - Exposed as `button` entities for:
    - Page navigation.
    - Manual refresh.
  - Usable in Home Assistant automations.
- Buzzer:
  - Exposed via `rtttl` and template buttons/services.
- Sensors:
  - Battery voltage / battery level.
  - WiFi RSSI.
  - Onboard environmental sensors (where supported).

These entities let you:

- Trigger page changes from HA automations.
- Use reTerminal as both a display and an input device.

## Features

- **Integrated Visual Editor**: No manual file copying required - everything is bundled with HACS installation
- **Real Entity Picker**: Browse, search, and select from your actual Home Assistant entities
- **Live State Preview**: See entity values update in real-time on the canvas (every 30 seconds)
- **Multi-Page Layouts**: Create multiple pages with configurable refresh rates
- **Drag-and-Drop**: Intuitive canvas-based layout design with snap-to-grid
- **Comprehensive Widget Set**: Text, sensor values, MDI icons, shapes (rectangles, circles, lines)
- **ESPHome Integration**: Generates clean, additive YAML snippets for your reTerminal
- **Persistent Storage**: Layouts saved in Home Assistant's storage system
- **Round-Trip Support**: Import existing ESPHome configs back into the editor

## Important Notes and Limitations

- The generator currently:
  - Uses a conservative widget set and a fixed display driver config tailored for the reTerminal E1001.
  - Emits comments where manual adjustment may be needed.
  - Focuses on sensor/binary_sensor/weather entity types.
- The PNG rendering path in `renderer.py` is kept for reference but not required for normal operation.
- You should always:
  - Review the generated YAML before flashing.
  - Keep your ESPHome configs in version control.
  - Verify YAML against ESPHome validation before deploying to hardware.

