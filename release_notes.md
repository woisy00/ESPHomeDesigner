# Release Notes

## v0.4.6.1
- **Critical Bug Fix**: Fixed JavaScript error `ReferenceError: isTextSensor is not defined` in snippet generator that prevented YAML generation and caused compilation errors.


## v0.4.6
- **Number Sensor Fix**: Fixed a bug where number sensors were interpreted as text sensors, causing them to show gibberish or fail to compile.
- **Graph Improvements**: X and Y information are now automatically added if the user adds min/max information or time information in the widget settings.
- **Graph Persistence**: Fixed a bug where graph minimum/maximum values and duration were not saving to YAML. These values would reset when "Update Layout from YAML" was pressed.
- **Known Bugs**:
    - Puppet widget is still unstable.
    - Straight lines are not perfectly straight.
    - Visible conditions are not fully tested and might fail to compile.


## v0.4.5
- **Min/Max Visibility**: Added support for numeric range conditions (Min/Max) with AND/OR logic for widget visibility. Perfect for progress bars (e.g., `0 < value < 100`).
- **Boot Stability**: Updated the default hardware template (`reterminal_e1001_lambda.yaml`) to remove the immediate display update from `on_boot`, preventing boot loops on heavy layouts.
- **WiFi Sensor**: Added `wifi_signal_db` to the default hardware template (diagnostic entity).
- **GUI Updates**: Added "Update Layout from YAML" button to the editor for easier round-trip editing.
- **Graph Widget Fixes**: Fixed persistence of `min_value`, `max_value`, `min_range`, and `max_range` properties.
- **Editor Fixes**: Fixed CSS regression and ensured fullscreen editing works correctly.
- **Text Sensor Persistence**: Fixed "Is Text Sensor?" checkbox state not saving to backend.
- **Puppet Widget Fixes**: Fixed Puppet/Online Image widgets not saving to backend, added automatic `http_request` dependency, and fixed URL corruption in parser.
- **Puppet Stability**: Added `on_error` handler and conditional page updates to prevent crashes and unnecessary refreshes.
- **Conditional Visibility**: Fixed C++ compilation error when using conditional visibility with numeric sensors (removed invalid `atof` check).

## v0.4.4
- **Text Sensor Support**: Added "Is Text Sensor?" checkbox to `sensor_text` widget to correctly format string states (fixes `NaN` issue).
- **Entity Picker Limit**: Increased the entity fetch limit from 1000 to 5000 to support larger Home Assistant installations.
- **Default Template Fixes**: Updated `reterminal_e1001_lambda.yaml` to match default dashboard entity IDs (`sensor_reterminal_e1001_...`) and device name.
- **Canvas Responsiveness**: Improved canvas scaling and centering on smaller screens.

## v0.4.3
### New Features
-   **Copy/Paste**: Added support for copying and pasting widgets using `Ctrl+C` and `Ctrl+V`. Pasted widgets are automatically offset for visibility.
-   **Undo/Redo**: Implemented Undo (`Ctrl+Z`) and Redo (`Ctrl+Y` or `Ctrl+Shift+Z`) functionality for widget operations (move, resize, add, delete, property changes).
-   **Fullscreen YAML Editing**: The fullscreen YAML view is now editable and includes an "Update Layout from YAML" button to apply changes directly.
-   **Sidebar Visibility Control**: Added a configuration option to show or hide the integration in the Home Assistant sidebar.
-   **Canvas Responsiveness**: The editor canvas now dynamically scales and centers to fit smaller screens, ensuring the entire layout is visible without scrolling.

### Bug Fixes
-   **Ghost Pages**: Fixed an issue where deleted pages would persist in the generated YAML snippet.
-   **Undo/Redo Stability**: Fixed issues where Undo would jump back multiple steps or become unresponsive due to duplicate history states or missing drag state capture.
-   **Graph Persistence**: Fixed `Continuous: true` setting not saving correctly.
-   **Page Jump**: Fixed editor jumping to the first page after layout updates.
-   **Weather Text Color**: Fixed weather widget text color reverting to black.

## v0.4.2
-   **Graph Widget**: Added automated sensor info (min/max) based on Home Assistant entity attributes.
-   **Circle Widget**: Enforced 1:1 aspect ratio during resize to prevent distortion.
-   **Manifest**: Version bump.
