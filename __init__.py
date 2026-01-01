import sys
import os


# Define the addon's root folder
ADDON_FOLDER = os.path.dirname(__file__)

# Determine platform-specific lib folder
base_lib_folder = os.path.join(ADDON_FOLDER, "lib")
plat_folder = None
target_lib = None

if sys.platform.startswith("win32"):
    if sys.maxsize > 2**32:
        plat_folder = "win64"
    else:
        plat_folder = "win32"
elif sys.platform.startswith("darwin"):
    plat_folder = "macos"
elif sys.platform.startswith("linux"):
    plat_folder = "linux"

# Add platform-specific lib folder to sys.path FIRST (before addon folder)
# This ensures external dependencies like psutil are found before any local modules
if plat_folder:
    target_lib = os.path.join(base_lib_folder, plat_folder)
    if target_lib not in sys.path:
        sys.path.insert(0, target_lib)

# Fallback: add base lib folder
if base_lib_folder not in sys.path:
    sys.path.insert(0, base_lib_folder)


# Import Anki's modules first to ensure gui_hooks is defined if an error occurs later
from aqt import mw, gui_hooks
from aqt.theme import theme_manager
from aqt.qt import QAction
from .settings import SettingsDialog
from aqt.utils import showWarning, tooltip # Import tooltip for more subtle feedback

# Now attempt to import psutil
psutil_available = False
try:
    import psutil
    psutil_available = True
except ImportError as e:
    # If psutil fails to import, disable the add-on's core functionality
    # and inform the user.
    showWarning(f"The 'Power - Check your battery' add-on requires the 'psutil' library.\n"
                f"Please ensure it is installed correctly in the add-on's 'lib' folder "
                f"(e.g., using 'pip install psutil -t {target_lib}').\n"
                f"Error: {e}\n\n"
                f"This add-on's battery display functionality will be disabled.")
    
    # Define a dummy function to replace add_battery_widget
    def dummy_add_battery_widget(*args, **kwargs):
        pass # Do nothing
    
    # Append the dummy function instead of the original
    gui_hooks.deck_browser_will_render_content.append(dummy_add_battery_widget)

    # Also disable the settings menu item
    def dummy_open_settings():
        showWarning("Power Settings are unavailable because 'psutil' failed to load.")
    
    action = QAction("Power Settings (Unavailable)", mw)
    action.triggered.connect(dummy_open_settings)
    mw.form.menuTools.addAction(action)

    # The psutil import failed, so we've set up fallback dummies.
    # We allow the rest of the script to execute (defining functions), but we will skip
    # the final registration of the "real" features based on the psutil_available flag.

# --- If psutil import was successful, continue with normal add-on setup ---

def hex_to_rgba(hex_color, opacity_percent):
    """Converts a hex color string to an rgba string."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = hex_color[0]*2 + hex_color[1]*2 + hex_color[2]*2
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    alpha = opacity_percent / 100.0
    return f"rgba({r}, {g}, {b}, {alpha})"

def load_icon(name: str) -> str:
    """Loads an SVG icon from the 'icons' folder, trying underscore and hyphen variants."""
    # Define paths for both common naming conventions
    path_underscore = os.path.join(ADDON_FOLDER, "icons", f"{name}.svg")
    path_hyphen = os.path.join(ADDON_FOLDER, "icons", f"{name.replace('_', '-')}.svg")

    # Determine which file actually exists
    final_path = ""
    if os.path.exists(path_underscore):
        final_path = path_underscore
    elif os.path.exists(path_hyphen):
        final_path = path_hyphen

    # If a valid file was found, read and return its content
    if final_path:
        try:
            with open(final_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "" # Return empty on read error

    return "" # Return empty if no file was found

def get_battery_info():
    """Fetches battery percentage and charging status using psutil."""
    battery = psutil.sensors_battery()
    if not battery:
        return None
    
    secs_left = battery.secsleft
    time_left_long = ""
    time_left_charging = "" # An empty string is cleaner; CSS will handle the layout.
    is_fully_charged = battery.percent == 100 and battery.power_plugged

    if battery.power_plugged:
        icon_name = "battery_bolt"
        status_text = "Charging" # Always show "Charging..." when plugged in
        if secs_left is not None and secs_left > 0 and not is_fully_charged:
            mins_left = secs_left // 60
            hours = secs_left / 3600
            time_left_long = f"{hours:.1f} hours for full charge"
            time_left_charging = f"• {mins_left} min left"
        else:
            time_left_long = "Ready to go"
    else:
        icon_name = "battery_alert" if battery.percent <= 20 else "battery"
        status_text = "On Battery"
        if secs_left is not None and secs_left > 0:
            hours = secs_left / 3600
            time_left_long = f"~{hours:.1f} hours left"
        else:
            time_left_long = "No estimate"

    return {
        "percent": int(battery.percent),
        "charging": battery.power_plugged,
        "status_text": status_text,
        "time_left_long": time_left_long,
        "time_left_charging": time_left_charging,
        "is_fully_charged": is_fully_charged,
        "icon_name": icon_name
    }

def add_battery_widget(deck_browser, content):
    """Adds the battery widget HTML to the bottom of the deck browser."""
    config = mw.addonManager.getConfig(__name__) or {}
    battery_info = get_battery_info()

    if not battery_info:
        return

    icon_svg = load_icon(battery_info["icon_name"])

    is_dark_mode = theme_manager.night_mode
    if config.get("theme") == "light": is_dark_mode = False
    elif config.get("theme") == "dark": is_dark_mode = True

    # Get background settings
    opacity = config.get("bg_opacity", 100)
    light_bg_hex = config.get("bg_light_color", "#ffffff")
    dark_bg_hex = config.get("bg_dark_color", "#000000")

    # Determine background color
    base_bg_hex = dark_bg_hex if is_dark_mode else light_bg_hex
    bg_color_rgba = hex_to_rgba(base_bg_hex, opacity)

    widget_html = ""
    layout = config.get("layout", "layout1")
    
    shared_styles = f"""
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        .b-widget-container {{
            width: 200px;
            height: 200px;
            background-color: {bg_color_rgba};
            color: {'#ffffff' if is_dark_mode else '#111827'};
            border-radius: 24px;
            padding: 20px;
            font-family: 'Inter', sans-serif;
            margin: 20px auto;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            text-align: center;
        }}
        .b-widget-icon svg {{
            width: 24px;
            height: 24px;
            vertical-align: middle;
        }}
    """
    
    if layout == "layout1":
        bar_color = config.get("layout1_dark_fg", "#02FF68") if is_dark_mode else config.get("layout1_light_fg", "#02FF68")
        text_color = "#FFFFFF" if is_dark_mode else "#000000"
        subtle_text_color = "#a0aec0" if is_dark_mode else "#718096"
        bar_bg_color = "rgba(128, 128, 128, 0.3)"

        widget_html = f"""
        <style>
            {shared_styles}
            #bw-l1 {{
                color: {text_color};
                justify-content: space-between;
                align-items: flex-start;
            }}
            .bw-l1-header {{
                font-size: 18px;
                font-weight: 600;
                color: {subtle_text_color};
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .bw-l1-header .b-widget-icon svg {{
                fill: {subtle_text_color};
            }}
            .bw-l1-main-info {{
                font-size: 22px;
                font-weight: 700;
                text-align: left
            }}
            .bw-l1-bar-area {{ width: 100%; }}
            .bw-l1-bar-container {{
                width: 100%; height: 50px; background-color: {bar_bg_color};
                border-radius: 14px; position: relative;
            }}
            .bw-l1-bar-fill {{
                height: 100%; width: {battery_info['percent']}%;
                background-color: {bar_color}; border-radius: 14px;
                box-shadow: 0 0 12px {bar_color}; transition: width 0.5s ease-in-out;
                display: flex; align-items: center; justify-content: flex-end;
                padding-right: 8px; box-sizing: border-box;
            }}
            .bw-l1-bar-tick {{
                width: 2px; height: 50%; background-color: rgba(0, 0, 0, 0.25);
                border-radius: 1px;
            }}
            .bw-l1-bar-labels {{
                display: flex; justify-content: space-between; font-size: 12px;
                color: {subtle_text_color}; padding: 4px 2px 0 2px;
            }}
        </style>
        <div id="bw-l1" class="b-widget-container">
            <div> <!-- Grouping div for top content -->
                <div class="bw-l1-header">
                    <span class="b-widget-icon">{icon_svg}</span>
                    <span>{battery_info['status_text']}</span>
                </div>
                <div class="bw-l1-main-info">
                    <span>{battery_info['percent']}%</span>
                    <span>{battery_info['time_left_charging']}</span>
                </div>
            </div>
            <div class="bw-l1-bar-area">
                <div class="bw-l1-bar-container">
                    <div class="bw-l1-bar-fill">
                        <div class="bw-l1-bar-tick"></div>
                    </div>
                </div>
                <div class="bw-l1-bar-labels">
                    <span>0</span><span>50</span><span>100</span>
                </div>
            </div>
        </div>
        """

    elif layout == "layout2":
        bar_color = config.get("layout2_dark_fg", "#c084fc") if is_dark_mode else config.get("layout2_light_fg", "#a855f7")
        bar_bg_color = "rgba(255, 255, 255, 0.1)" if is_dark_mode else "rgba(0, 0, 0, 0.1)"
        
        percent = battery_info['percent']
        segments_html = ""
        for i in range(5):
            lower_bound, upper_bound = i * 20, (i + 1) * 20
            fill = f'<div class="fill" style="background-color: {bar_color}; width: 100%;"></div>' if percent >= upper_bound else \
                   f'<div class="fill" style="background-color: {bar_color}; width: {((percent - lower_bound) / 20) * 100}%;"></div>' if percent > lower_bound else ""
            segments_html += f'<div class="segment">{fill}</div>'

        widget_html = f"""
        <style>
            {shared_styles}
            .bw-l2-main-info {{ font-size: 32px; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
            .bw-l2-main-info .percent-text {{ color: {'#ffffff' if is_dark_mode else '#111827'}; }}
            .bw-l2-main-info .b-widget-icon svg {{ fill: {bar_color}; }}
            .bw-l2-bar-container {{ display: flex; gap: 4px; width: 100%; height: 24px; border: 2px solid {bar_bg_color}; border-radius: 8px; padding: 3px; }}
            .bw-l2-bar-container .segment {{ flex: 1; background-color: {bar_bg_color}; border-radius: 4px; overflow: hidden; }}
            .bw-l2-bar-container .segment .fill {{ height: 100%; border-radius: 4px; }}
            .bw-l2-time-left {{ font-size: 14px; color: {'#9ca3af' if is_dark_mode else '#6b7280'}; }}
        </style>
        <div id="bw-l2" class="b-widget-container">
            <div class="bw-l2-main-info">
                <span class="b-widget-icon">{icon_svg}</span>
                <span class="percent-text">{battery_info['percent']}%</span>
            </div>
            <div class="bw-l2-bar-container">{segments_html}</div>
            <div class="bw-l2-time-left">{battery_info['time_left_long']}</div>
        </div>
        """

    elif layout == "layout3":
        bar_color = config.get("layout3_dark_fg", "#4ade80") if is_dark_mode else config.get("layout3_light_fg", "#22c55e")
        bar_bg_color = "rgba(255, 255, 255, 0.1)" if is_dark_mode else "rgba(0, 0, 0, 0.1)"
        subtle_text_color = '#9ca3af' if is_dark_mode else '#6b7280'
        
        widget_html = f"""
        <style>
            {shared_styles}
            #bw-l3 {{ 
                justify-content: space-around; 
            }}
            .bw-l3-header {{
                font-size: 16px; font-weight: 600; color: {subtle_text_color};
                display: flex; align-items: center; gap: 8px;
                height: 24px; /* Reserve space */
            }}
            .bw-l3-header .b-widget-icon svg {{ fill: {subtle_text_color}; }}
            @property --p{{ syntax: '<number>'; inherits: true; initial-value: 0; }}
            .bw-l3-radial-bar {{
                --p: {battery_info['percent']}; --w: 100px; --b: 12px;
                width: var(--w); aspect-ratio: 1; position: relative;
                display: inline-grid; place-content: center; font-size: 24px;
                font-weight: 700;
            }}
            .bw-l3-radial-bar::before {{
                content: ""; position: absolute; border-radius: 50%; inset: 0;
                background: conic-gradient({bar_color} calc(var(--p) * 1%), {bar_bg_color} 0);
                -webkit-mask: radial-gradient(farthest-side, #0000 calc(99% - var(--b)), #000 calc(100% - var(--b)));
                mask: radial-gradient(farthest-side, #0000 calc(99% - var(--b)), #000 calc(100% - var(--b)));
                transition: --p 1s;
            }}
            .bw-l3-time-left {{ font-size: 14px; color: {subtle_text_color}; }}
        </style>
        <div id="bw-l3" class="b-widget-container">
            <div class="bw-l3-header">
                <span class="b-widget-icon">{icon_svg}</span>
                <span>{battery_info['status_text']}</span>
            </div>
            <div class="bw-l3-radial-bar">{battery_info['percent']}%</div>
            <div class="bw-l3-time-left">{battery_info['time_left_long']}</div>
        </div>
        """

    content.stats += widget_html

def open_settings():
    """Opens the settings dialog."""
    dialog = SettingsDialog(mw, addon_package=__name__)
    dialog.exec()

# Ensure these are only created if psutil successfully loaded
# If psutil failed, dummy functions and action were already set up.
if psutil_available:
    action = QAction("Power Settings", mw)
    action.triggered.connect(open_settings)
    mw.form.menuTools.addAction(action)

    gui_hooks.deck_browser_will_render_content.append(add_battery_widget)