# settings.py
import copy
import os
import webbrowser
import importlib
from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget, QFormLayout,
    QColorDialog, QColor, QSlider, QSpinBox, Qt, QPixmap, QScrollArea,
    QFrame, QButtonGroup, QAbstractButton, QApplication, QTimer
)
try:
    from PyQt6.QtCore import pyqtProperty, QPropertyAnimation, QEasingCurve, QRectF, QParallelAnimationGroup, QPointF, QSize
    from PyQt6.QtGui import QPainter, QPen, QColor as QColor2, QPainterPath, QFont
    from PyQt6.QtWidgets import QStyleOption, QStyle, QSizePolicy
except ImportError:
    from PyQt5.QtCore import pyqtProperty, QPropertyAnimation, QEasingCurve, QRectF, QParallelAnimationGroup, QPointF, QSize
    from PyQt5.QtGui import QPainter, QPen, QColor as QColor2, QPainterPath, QFont
    from PyQt5.QtWidgets import QStyleOption, QStyle, QSizePolicy
from aqt.utils import showInfo
from aqt.theme import theme_manager
from aqt.webview import AnkiWebView
from . import bento_integration

# --- Shared UI Components (from Berry design) ---
class AnimatedToggleButton(QAbstractButton):
    def __init__(self, parent=None, accent_color="#BD87FA"):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.accent_color = QColor(accent_color)
        self.track_color_off = QColor("#cccccc") if not theme_manager.night_mode else QColor("#555555")
        self.thumb_color = QColor("#ffffff")
        self.setFixedSize(38, 20)
        self._thumb_x_pos = 3.0
        self.animation = QPropertyAnimation(self, b"thumb_x_pos", self)
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.toggled.connect(self._start_animation)

    @pyqtProperty(float)
    def thumb_x_pos(self):
        return self._thumb_x_pos

    @thumb_x_pos.setter
    def thumb_x_pos(self, value):
        self._thumb_x_pos = value
        self.update()

    def _start_animation(self, checked):
        end_pos = self.width() - self.height() + 3 if checked else 3
        self.animation.setStartValue(self.thumb_x_pos)
        self.animation.setEndValue(end_pos)
        self.animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        height = self.height()
        radius = height / 2.0
        painter.setPen(Qt.PenStyle.NoPen)
        track_color = self.accent_color if self.isChecked() else self.track_color_off
        painter.setBrush(track_color)
        painter.drawRoundedRect(self.rect(), radius, radius)
        thumb_radius = radius - 3
        painter.setBrush(self.thumb_color)
        thumb_y = radius
        painter.drawEllipse(QPointF(self._thumb_x_pos + thumb_radius, thumb_y), thumb_radius, thumb_radius)

    def showEvent(self, event):
        super().showEvent(event)
        self._thumb_x_pos = self.width() - self.height() + 3 if self.isChecked() else 3
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._thumb_x_pos = self.width() - self.height() + 3 if self.isChecked() else 3
        self.update()

class GooeySegmentedControl(QWidget):
    def __init__(self, accent_color="#38DC75", parent=None, bg_color="#f2f2f2", border_color="#dcdde1"):
        super().__init__(parent)
        self.setObjectName("themeToggleContainer")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(0)
        self._accent_color = QColor(accent_color)
        self._bg_color = QColor(bg_color)
        self._border_color = QColor(border_color)
        self._indicator_rect = QRectF(4, 4, 0, 0)
        self.anim_group = QParallelAnimationGroup(self)
        self.anim_x = QPropertyAnimation(self, b"indicator_x")
        self.anim_width = QPropertyAnimation(self, b"indicator_width")
        self.anim_group.addAnimation(self.anim_x)
        self.anim_group.addAnimation(self.anim_width)
        self.anim_x.setEasingCurve(QEasingCurve.Type.InOutBack)
        self.anim_width.setEasingCurve(QEasingCurve.Type.InOutBack)
        self.anim_x.setDuration(400)
        self.anim_width.setDuration(400)
        self.button_group = QButtonGroup(self)
        self.button_group.buttonClicked.connect(self.animate_to)

    @pyqtProperty(float)
    def indicator_x(self):
        return self._indicator_rect.x()

    @indicator_x.setter
    def indicator_x(self, value):
        self._indicator_rect.setX(value)
        self.update()

    @pyqtProperty(float)
    def indicator_width(self):
        return self._indicator_rect.width()

    @indicator_width.setter
    def indicator_width(self, value):
        self._indicator_rect.setWidth(value)
        self.update()

    def add_button(self, btn):
        self._layout.addWidget(btn)
        self.button_group.addButton(btn)

    def animate_to(self, btn):
        if not btn: return
        target_rect = btn.geometry()
        if target_rect.width() == 0: return
        self.anim_x.setStartValue(self.indicator_x)
        self.anim_x.setEndValue(float(target_rect.x()))
        self.anim_width.setStartValue(self.indicator_width)
        self.anim_width.setEndValue(float(target_rect.width()))
        self.anim_group.start()

    def update_indicator_no_animation(self):
        checked_btn = self.button_group.checkedButton()
        if checked_btn and checked_btn.geometry().width() > 0:
            r = checked_btn.geometry()
            self._indicator_rect.setX(r.x())
            self._indicator_rect.setWidth(r.width())
            self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_indicator_no_animation()

    def showEvent(self, event):
        super().showEvent(event)
        try:
            from PyQt6.QtCore import QTimer
        except ImportError:
            from PyQt5.QtCore import QTimer
        QTimer.singleShot(50, self.update_indicator_no_animation)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the pill track ourselves (radius = actual height / 2) instead
        # of relying on QSS border-radius, which doesn't clamp large values
        # the way CSS does and can render as a barely-rounded rectangle.
        track_radius = self.height() / 2.0
        track_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, track_radius, track_radius)
        p.setPen(QPen(self._border_color, 1))
        p.setBrush(self._bg_color)
        p.drawPath(track_path)

        if self._indicator_rect.width() > 0:
            # The InOutBack easing on the slide animation overshoots past its
            # target (that's what gives it the "gooey" bounce), which can push
            # the indicator's rounded corner past x=0 mid-animation. Clipping
            # to the track's own rounded path (rather than the widget's plain
            # rectangular bounds) means any overshoot gets bounded by the
            # pill's curve instead of being sliced off into a flat edge.
            p.setClipPath(track_path)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._accent_color)
            checked_btn = self.button_group.checkedButton()
            h = checked_btn.geometry().height() if checked_btn else 28
            y = checked_btn.geometry().y() if checked_btn else 4
            rect = QRectF(self._indicator_rect.x(), float(y), self._indicator_rect.width(), float(h))
            radius = h / 2.0
            p.drawRoundedRect(rect, radius, radius)

class ModernSlider(QSlider):
    def __init__(self, accent_color="#38DC75", parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.accent_color = QColor(accent_color)
        self.setMinimumHeight(24)

    def _theme_tokens(self):
        curr = self.parent()
        while curr:
            if hasattr(curr, "_theme_tokens"):
                return curr._theme_tokens()
            curr = curr.parent()
        return {
            "border": "#d1d5db" if not theme_manager.night_mode else "#444444",
            "surface": "#eaeaea" if not theme_manager.night_mode else "#2d2d2d",
        }

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        enabled = self.isEnabled()
        w = self.width()
        h = self.height()

        # Track parameters
        track_h = 18
        track_y = (h - track_h) // 2
        track_rx = track_h // 2

        min_val = self.minimum()
        max_val = self.maximum()
        val = self.value()

        range_val = max_val - min_val
        if range_val <= 0:
            range_val = 1

        handle_d = 12
        padding_x = 9

        x_min = padding_x
        x_max = w - padding_x
        pct = (val - min_val) / range_val
        handle_cx = x_min + pct * (x_max - x_min)

        # Get background color from tokens
        tokens = self._theme_tokens()
        bg_color_hex = tokens.get("surface", "#eaeaea")
        bg_color = QColor(bg_color_hex)

        if enabled:
            active_color = self.accent_color
        else:
            active_color = QColor(self.accent_color.red(), self.accent_color.green(), self.accent_color.blue(), 76)
            bg_color.setAlpha(76)

        # Draw background track
        track_rect = QRectF(0, track_y, w, track_h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(track_rect, track_rx, track_rx)

        # Draw active track
        active_right = handle_cx + 10
        if active_right > w:
            active_right = w
        if active_right < track_rx * 2:
            active_right = track_rx * 2

        active_rect = QRectF(0, track_y, active_right, track_h)
        painter.setBrush(active_color)
        painter.drawRoundedRect(active_rect, track_rx, track_rx)

        # Draw handle (white circle centered at handle_cx)
        handle_cy = track_y + track_h / 2
        handle_color = QColor("#ffffff") if enabled else QColor(255, 255, 255, 120)
        painter.setBrush(handle_color)
        painter.drawEllipse(QPointF(handle_cx, handle_cy), 6, 6)

class SectionGroup(QWidget):
    def __init__(self, title="", parent=None, description=""):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(0, 5, 0, 0)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 17px; margin-bottom: 2px;")
        main_layout.addWidget(title_label)
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet("font-size: 11px; color: #888; margin-bottom: 5px;")
            desc_label.setWordWrap(True)
            main_layout.addWidget(desc_label)
        self.content_area = QWidget()
        self.content_area.setObjectName("innerGroup")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        self.content_layout.setSpacing(10)
        main_layout.addWidget(self.content_area)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)

def _contrast_text_color(hex_color: str) -> str:
    c = hex_color.lstrip('#')
    r, g, b = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) if len(c) in (6, 8) else (255, 255, 255)
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    return "#111111" if luminance > 0.56 else "#ffffff"

def create_color_button(initial_color, parent):
    button = QPushButton(parent)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setObjectName("colorSwatchButton")
    _apply_swatch_style(button, initial_color)
    return button

def _apply_swatch_style(button, color_str):
    text_color = _contrast_text_color(color_str)
    button.setText(color_str.upper())
    button.setStyleSheet(
        f"QPushButton#colorSwatchButton {{"
        f"  background-color: {color_str};"
        f"  color: {text_color};"
        f"  font-weight: bold;"
        f"  font-size: 13px;"
        f"  border: 1px solid rgba(0,0,0,0.15);"
        f"  border-radius: 12px;"
        f"  padding: 6px 16px;"
        f"}}"
        f"QPushButton#colorSwatchButton:hover {{"
        f"  border: 1px solid rgba(0,0,0,0.35);"
        f"}}"
    )

# ─── Live Preview ────────────────────────────────────────────────────────────

# Power's .b-widget-container is a fixed 200x200 square (all three layouts)
# with `margin: 20px auto` baked into generate_battery_html()'s shared_styles,
# so — like Hours — there's a single fixed natural footprint, not a
# per-view-mode dict.
_NATURAL_W, _NATURAL_H = 200, 240


class PowerPreviewWidget(QWidget):
    """Renders a live HTML preview of the Power battery widget using sample
    (non-hardware) battery data, so it never depends on psutil/real state."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._charging = False

        self.preview_layout = QVBoxLayout(self)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)

        self.webview = None

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.refresh)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(120)

    def cleanup(self):
        """Release the embedded AnkiWebView before this widget is destroyed.

        AnkiWebView wraps a QWebEngineView; if it is left to be torn down
        implicitly during Python interpreter finalization (Anki quitting),
        Qt dereferences already-freed child widgets and segfaults. Cleaning
        it up explicitly on dialog close avoids that.
        """
        if getattr(self, "_resize_timer", None) is not None:
            self._resize_timer.stop()
        if getattr(self, "webview", None) is not None:
            if getattr(self, "webview", None):
                self.webview.cleanup()
            self.webview = None

    def set_charging(self, charging):
        if charging == self._charging:
            return
        self._charging = charging
        self.refresh()


    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "webview", None) is None:
            self.webview = AnkiWebView(title="power_preview", parent=self)
            self.webview.setMinimumSize(260, 300)
            self.webview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.webview.disable_zoom()
            page = self.webview.page()
            page.setBackgroundColor(QColor(0, 0, 0, 0))
            self.preview_layout.addWidget(self.webview)
            self.refresh()

    def refresh(self):
        if not getattr(self, "webview", None):
            return
        addon_module = importlib.import_module(__package__)
        # The surrounding dialog/wallpaper follows the real Anki theme; only
        # the widget's own rendering respects its "theme" override (Auto/
        # Light/Dark), mirroring add_battery_widget()'s resolution.
        system_is_dark = theme_manager.night_mode
        widget_is_dark = system_is_dark
        if self.config.get("theme") == "light":
            widget_is_dark = False
        elif self.config.get("theme") == "dark":
            widget_is_dark = True

        battery_info = addon_module.get_preview_battery_info(charging=self._charging)
        html_content = addon_module.generate_battery_html(self.config, battery_info, widget_is_dark)

        # Behind the widget: Onigiri's actual deck-browser wallpaper when the
        # integration is active, otherwise the same flat color as this dialog.
        settings_bg = "#181818" if system_is_dark else "#f7f7f7"
        wallpaper = None
        if bento_integration.is_onigiri_detected():
            wallpaper = bento_integration.main_menu_wallpaper(system_is_dark)
        if not wallpaper:
            wallpaper = {"kind": "color", "color": settings_bg}

        if wallpaper["kind"] == "image":
            bg_layer_css = f"""
                background-color: {wallpaper['color']};
                background-image: url('{wallpaper['url']}');
                background-size: cover; background-position: center; background-repeat: no-repeat;
                filter: blur({wallpaper['blur_px']}px);
                opacity: {wallpaper['opacity']};
            """
        else:
            bg_layer_css = f"background-color: {wallpaper['color']}; opacity: 1;"

        panel_w = self.webview.width()
        panel_h = self.webview.height()
        if panel_w < 100 or panel_h < 100:
            panel_w, panel_h = 320, 400

        avail_w = panel_w - 40
        avail_h = panel_h - 40
        factor = min(1.0, avail_w / _NATURAL_W, avail_h / _NATURAL_H) * 0.94
        final_w = _NATURAL_W * factor + 2
        final_h = _NATURAL_H * factor + 2

        full_html = f"""
        <html><head><style>
            html, body {{ margin: 0; padding: 0; height: 100%; overflow: hidden; background: transparent; }}
            body {{
                position: relative;
                display: flex; align-items: center; justify-content: center;
                background: transparent;
            }}
            #onigiri-bg-container {{
                position: absolute; inset: 10px; z-index: 0;
                border-radius: 20px; overflow: hidden;
                transform: translateZ(0);
            }}
            #onigiri-bg-layer {{
                position: absolute; inset: -50px;
                {bg_layer_css}
            }}
            #scale-wrapper {{
                position: relative; z-index: 1;
                width: {final_w}px; height: {final_h}px;
                flex-shrink: 0;
            }}
            #power-preview-inner {{
                position: absolute; top: 0; left: 0;
                transform: scale({factor}); transform-origin: top left;
            }}
        </style></head>
        <body>
            <div id="onigiri-bg-container">
                <div id="onigiri-bg-layer"></div>
            </div>
            <div id="scale-wrapper">
                <div id="power-preview-inner">{html_content}</div>
            </div>
        </body></html>
        """
        self.webview.setHtml(full_html)


class SettingsDialog(QDialog):
    def __init__(self, parent=None, addon_package=""):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle("Power Settings")
        
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            self.resize(int(avail.width() * 0.5), int(avail.height() * 0.55))
        else:
            self.resize(820, 600)
        self.setMinimumSize(800, 500)

        self.addon_package = addon_package
        self.config = mw.addonManager.getConfig(self.addon_package) or {}

        self.setup_ui()
        self.load_settings()
        self._refresh_preview()

        # Tear down the embedded AnkiWebView and schedule the dialog for
        # deletion when it closes, so it does not linger as a child of the
        # main window with a live QWebEngineView (which segfaults during
        # interpreter shutdown). deleteLater() is used instead of
        # WA_DeleteOnClose because this dialog is shown with exec(): a
        # WA_DeleteOnClose delete happens inside the modal loop and frees the
        # dialog while exec() is still unwinding, which itself crashes.
        self.finished.connect(self._cleanup_on_close)

    def _cleanup_on_close(self, *args):
        preview = getattr(self, "preview_widget", None)
        if preview is not None:
            preview.cleanup()
        self.deleteLater()

    def _theme_tokens(self):
        is_dark = theme_manager.night_mode
        accent = "#38DC75" # Power accent
        if is_dark:
            return {"bg": "#181818", "panel": "#242424", "surface": "#303030", "fg": "#f4f4f5", "muted": "#c4c4c4", "border": "#454545", "accent": accent}
        return {"bg": "#f7f7f7", "panel": "#ffffff", "surface": "#f2f2f2", "fg": "#202124", "muted": "#6f7177", "border": "#dcdde1", "accent": accent}

    def setup_ui(self):
        tokens = self._theme_tokens()
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Main controls container
        controls_outer = QWidget()
        controls_outer.setObjectName("controlsOuter")
        controls_outer.setMinimumWidth(500)
        controls_outer_layout = QVBoxLayout(controls_outer)
        controls_outer_layout.setContentsMargins(0, 10, 0, 0)
        controls_outer_layout.setSpacing(0)

        controls_container = QFrame()
        controls_container.setObjectName("controlsContainer")
        controls_container.setFrameShape(QFrame.Shape.NoFrame)
        controls_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        controls_container_layout = QVBoxLayout(controls_container)
        controls_container_layout.setContentsMargins(0, 0, 0, 0)
        controls_container_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("controlsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(16, 24, 16, 20)
        scroll_layout.setSpacing(20)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Layout Selection
        layout_group = SectionGroup("Widget Layout", self)
        self.layout_toggle = GooeySegmentedControl(tokens["accent"], self, bg_color=tokens["surface"], border_color=tokens["border"])
        self.radio_layout1 = QPushButton("Slider")
        self.radio_layout2 = QPushButton("Bar")
        self.radio_layout3 = QPushButton("Radial")
        for btn in [self.radio_layout1, self.radio_layout2, self.radio_layout3]:
            btn.setCheckable(True)
            btn.setObjectName("themeToggleButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            self.layout_toggle.add_button(btn)
        self.layout_toggle.button_group.buttonClicked.connect(self._refresh_preview)
        layout_group.add_widget(self.layout_toggle)
        scroll_layout.addWidget(layout_group)

        # Theme Selection
        theme_group = SectionGroup("Appearance Theme", self)
        self.theme_toggle = GooeySegmentedControl(tokens["accent"], self, bg_color=tokens["surface"], border_color=tokens["border"])
        self.radio_auto = QPushButton("Auto")
        self.radio_light = QPushButton("Light")
        self.radio_dark = QPushButton("Dark")
        for btn in [self.radio_auto, self.radio_light, self.radio_dark]:
            btn.setCheckable(True)
            btn.setObjectName("themeToggleButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            self.theme_toggle.add_button(btn)
        self.theme_toggle.button_group.buttonClicked.connect(self._refresh_preview)
        theme_group.add_widget(self.theme_toggle)
        scroll_layout.addWidget(theme_group)

        # Colors configuration
        colors_group = SectionGroup("Color Customization", self)

        self.color_buttons = {}
        color_specs = [
            ("Slider — Light", "layout1_light_fg", "#02FF68", "layout1"),
            ("Slider — Dark", "layout1_dark_fg", "#02FF68", "layout1"),
            ("Bar — Light", "layout2_light_fg", "#9ca3af", "layout2"),
            ("Bar — Dark", "layout2_dark_fg", "#6b7280", "layout2"),
            ("Radial — Light", "layout3_light_fg", "#22c55e", "layout3"),
            ("Radial — Dark", "layout3_dark_fg", "#4ade80", "layout3"),
            ("Widget Background — Light", "bg_light_color", "#ffffff", None),
            ("Widget Background — Dark", "bg_dark_color", "#000000", None),
        ]
        self._color_rows = []
        for label_text, config_key, default_val, layout_key in color_specs:
            row = self._create_color_row(label_text, self.config.get(config_key, default_val), config_key)
            colors_group.add_widget(row)
            self._color_rows.append((row, layout_key))
        self.layout_toggle.button_group.buttonClicked.connect(self._update_color_rows_visibility)

        opacity_row = QWidget()
        opacity_layout = QHBoxLayout(opacity_row)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        opacity_layout.addWidget(QLabel("Background Opacity"))
        self.opacity_slider = ModernSlider(tokens["accent"], self)
        self.opacity_slider.setObjectName("berrySlider")
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.opacity_value_label = QLabel("100%")
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_value_label.setText(f"{v}%"))
        self.opacity_slider.valueChanged.connect(self._refresh_preview)
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_value_label)
        colors_group.add_widget(opacity_row)

        scroll_layout.addWidget(colors_group)

        integration_group, self.bento_width_spin, self.bento_height_spin = bento_integration.create_settings_group(self.config)
        self.bento_width_spin.valueChanged.connect(self._refresh_preview)
        self.bento_height_spin.valueChanged.connect(self._refresh_preview)
        scroll_layout.addWidget(integration_group)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        scroll.viewport().setAutoFillBackground(False)
        scroll_content.setAutoFillBackground(False)
        controls_container.setAutoFillBackground(False)
        controls_container_layout.addWidget(scroll)
        controls_outer_layout.addWidget(controls_container)

        # ── Right: Preview panel ─────────────────────────────────────────
        preview_wrapper = QWidget()
        preview_wrapper.setObjectName("previewWrapper")
        preview_wrapper_layout = QVBoxLayout(preview_wrapper)
        preview_wrapper_layout.setContentsMargins(10, 24, 20, 20)
        preview_wrapper_layout.setSpacing(12)

        preview_header_row = QWidget()
        preview_header_layout = QHBoxLayout(preview_header_row)
        preview_header_layout.setContentsMargins(0, 0, 0, 0)

        preview_title = QLabel("Preview")
        preview_title.setStyleSheet(f"font-size: 12px; font-weight: 700; letter-spacing: 0.6px; color: {tokens['muted']};")
        preview_header_layout.addWidget(preview_title)
        preview_header_layout.addStretch()

        self.preview_variant_toggle = GooeySegmentedControl(tokens["accent"], self, bg_color=tokens["surface"], border_color=tokens["border"])
        self.radio_preview_battery = QPushButton("On Battery")
        self.radio_preview_charging = QPushButton("Charging")
        for btn in [self.radio_preview_battery, self.radio_preview_charging]:
            btn.setCheckable(True)
            btn.setObjectName("themeToggleButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(22)
            self.preview_variant_toggle.add_button(btn)
        self.radio_preview_battery.setChecked(True)
        self.preview_variant_toggle.button_group.buttonClicked.connect(self._on_preview_variant_changed)
        preview_header_layout.addWidget(self.preview_variant_toggle)

        preview_wrapper_layout.addWidget(preview_header_row)

        self.preview_widget = PowerPreviewWidget(self._collect_config(), self)
        preview_wrapper_layout.addWidget(self.preview_widget, 1)

        content_h_layout = QHBoxLayout()
        content_h_layout.setSpacing(0)
        content_h_layout.setContentsMargins(0, 0, 0, 0)
        content_h_layout.addWidget(controls_outer, 1)
        content_h_layout.addWidget(preview_wrapper, 1)
        root_layout.addLayout(content_h_layout, 1)

        # Bottom Pill Bar
        bottom_container = QWidget()
        bottom_container.setObjectName("bottomContainer")
        bottom_container_layout = QVBoxLayout(bottom_container)
        bottom_container_layout.setContentsMargins(20, 8, 20, 20)
        
        bottom_bar = QWidget()
        bottom_bar.setObjectName("bottomPillBar")
        bottom_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bottom_bar_layout = QHBoxLayout(bottom_bar)
        bottom_bar_layout.setContentsMargins(10, 10, 10, 10)
        bottom_bar_layout.setSpacing(8)

        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "power_logo.svg")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(200, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setFixedSize(scaled_pixmap.size())
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bottom_bar_layout.addWidget(logo_label)

        bottom_bar_layout.addSpacing(8)
        self.donate_button = QPushButton("Donate")
        self.donate_button.setObjectName("cancelButton")
        self.donate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.report_button = QPushButton("Report Bug")
        self.report_button.setObjectName("cancelButton")
        self.report_button.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom_bar_layout.addWidget(self.donate_button)
        bottom_bar_layout.addWidget(self.report_button)
        
        self.donate_button.clicked.connect(lambda: webbrowser.open("https://buymeacoffee.com/peacemonk"))
        self.report_button.clicked.connect(lambda: webbrowser.open("https://github.com/thepeacemonk/Power"))

        bottom_bar_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("saveButton")
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self.save_settings)
        
        bottom_bar_layout.addWidget(self.cancel_button)
        bottom_bar_layout.addWidget(self.save_button)

        bottom_container_layout.addWidget(bottom_bar)
        root_layout.addWidget(bottom_container)

        self._apply_stylesheet()

    def load_settings(self):
        current_layout = self.config.get("layout", "layout1")
        if current_layout == "layout2": self.radio_layout2.setChecked(True)
        elif current_layout == "layout3": self.radio_layout3.setChecked(True)
        else: self.radio_layout1.setChecked(True)

        current_theme = self.config.get("theme", "auto")
        if current_theme == "light": self.radio_light.setChecked(True)
        elif current_theme == "dark": self.radio_dark.setChecked(True)
        else: self.radio_auto.setChecked(True)

        initial_opacity = self.config.get("bg_opacity", 100)
        self.opacity_slider.setValue(initial_opacity)
        self.opacity_value_label.setText(f"{initial_opacity}%")

        self._update_color_rows_visibility()

    def _current_layout_key(self):
        if hasattr(self, "radio_layout2") and self.radio_layout2.isChecked():
            return "layout2"
        if hasattr(self, "radio_layout3") and self.radio_layout3.isChecked():
            return "layout3"
        return "layout1"

    def _update_color_rows_visibility(self, *_args):
        if not hasattr(self, "_color_rows"):
            return
        current = self._current_layout_key()
        for row, layout_key in self._color_rows:
            row.setVisible(layout_key is None or layout_key == current)

    def _create_color_row(self, label_text, initial_color, config_key):
        row = QFrame()
        row.setObjectName("colorRow")

        is_dark = theme_manager.night_mode
        bg_color = "#242424" if is_dark else "#FFFFFF"
        border_color = "#454545" if is_dark else "#DCDDE1"
        text_color = "#f4f4f5" if is_dark else "#1d1d1f"

        row.setStyleSheet(f"""
            QFrame#colorRow {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)

        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 10, 16, 10)

        label = QLabel(label_text)
        label.setStyleSheet(
            f"font-weight: 700; font-size: 14px; border: none; "
            f"background: transparent; color: {text_color};"
        )
        layout.addWidget(label)
        layout.addStretch()

        btn = create_color_button(initial_color, self)
        btn.clicked.connect(lambda: self.pick_color(btn, config_key))
        self.color_buttons[config_key] = btn
        layout.addWidget(btn)

        return row

    def pick_color(self, button, config_key):
        current_hex = self.config.get(config_key, button.text())

        try:
            onigiri_color_picker = importlib.import_module("1011095603.onigiri_color_picker")
            OnigiriColorDialog = onigiri_color_picker.OnigiriColorDialog
            new_color_hex, ok = OnigiriColorDialog.getColor(current_hex, self, anchor=button)
            if ok:
                self.config[config_key] = new_color_hex
                _apply_swatch_style(button, new_color_hex)
                self._refresh_preview()
            return
        except Exception as e:
            print(f"[Power] Failed to load OnigiriColorDialog: {e}")

        initial_qcolor = QColor(current_hex)
        color = QColorDialog.getColor(initial_qcolor, self, "Choose a color")
        if color.isValid():
            hex_color = color.name()
            self.config[config_key] = hex_color
            _apply_swatch_style(button, hex_color)
            self._refresh_preview()

    def _collect_config(self):
        """Assembles the in-progress config for the live preview. Color
        picker edits already write straight into self.config; layout/theme/
        opacity are collected here from their controls (mirroring
        save_settings() below) since those are only committed to self.config
        on Save."""
        cfg = dict(self.config)
        if hasattr(self, "radio_layout2") and self.radio_layout2.isChecked():
            cfg["layout"] = "layout2"
        elif hasattr(self, "radio_layout3") and self.radio_layout3.isChecked():
            cfg["layout"] = "layout3"
        elif hasattr(self, "radio_layout1"):
            cfg["layout"] = "layout1"
        if hasattr(self, "radio_light") and self.radio_light.isChecked():
            cfg["theme"] = "light"
        elif hasattr(self, "radio_dark") and self.radio_dark.isChecked():
            cfg["theme"] = "dark"
        elif hasattr(self, "radio_auto"):
            cfg["theme"] = "auto"
        if hasattr(self, "opacity_slider"):
            cfg["bg_opacity"] = self.opacity_slider.value()
        if hasattr(self, "bento_width_spin"):
            cfg[bento_integration.WIDTH_KEY] = int(self.bento_width_spin.value())
        if hasattr(self, "bento_height_spin"):
            cfg[bento_integration.HEIGHT_KEY] = int(self.bento_height_spin.value())
        return cfg

    def _refresh_preview(self, *_args):
        if not hasattr(self, "preview_widget"):
            return
        self.preview_widget.config = self._collect_config()
        self.preview_widget.refresh()

    def _on_preview_variant_changed(self, btn):
        self.preview_widget.set_charging(btn is self.radio_preview_charging)

    def save_settings(self):
        if self.radio_layout2.isChecked(): self.config["layout"] = "layout2"
        elif self.radio_layout3.isChecked(): self.config["layout"] = "layout3"
        else: self.config["layout"] = "layout1"

        if self.radio_light.isChecked(): self.config["theme"] = "light"
        elif self.radio_dark.isChecked(): self.config["theme"] = "dark"
        else: self.config["theme"] = "auto"
        
        self.config["bg_opacity"] = self.opacity_slider.value()
        bento_integration.save_settings_group(self.config, self.bento_width_spin, self.bento_height_spin)
        
        mw.addonManager.writeConfig(self.addon_package, self.config)
        showInfo("Power settings saved. Please restart Anki to see all changes.", parent=self)
        self.accept()

    def _apply_stylesheet(self):
        t = self._theme_tokens()
        bg, panel, fg, muted, surface, border, accent = t["bg"], t["panel"], t["fg"], t["muted"], t["surface"], t["border"], t["accent"]
        accent_hex = accent.lstrip("#")
        accent_rgb = tuple(int(accent_hex[i:i+2], 16) for i in (0, 2, 4))
        scrollbar_thumb = f"rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 0.45)"
        scrollbar_thumb_hover = f"rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 0.75)"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg}; color: {fg}; }}
            QFrame#controlsContainer {{
                background-color: transparent; border: none;
                border-top-left-radius: 28px; border-top-right-radius: 28px;
            }}
            QWidget#controlsOuter {{ background-color: transparent; }}
            QWidget#previewWrapper {{ background-color: transparent; border: none; }}
            QScrollArea#controlsScroll, QScrollArea#controlsScroll > QWidget {{
                background: transparent; border: none;
            }}
            QWidget#innerGroup {{
                background-color: transparent; border: none; border-radius: 12px;
            }}
            QLabel {{ color: {fg}; font-size: 13px; }}
            #themeToggleButton {{
                background-color: transparent; border: none; border-radius: 14px;
                padding: 4px 16px; font-size: 13px; font-weight: 600; color: {muted};
            }}
            #themeToggleButton:checked {{ color: #ffffff; }}
            #themeToggleButton:hover:!checked {{ color: {fg}; }}
            QSlider#berrySlider::groove:horizontal {{
                height: 18px;
                border-radius: 9px;
                background-color: {surface};
            }}
            QSlider#berrySlider::sub-page:horizontal {{
                background-color: {accent};
                border-radius: 9px;
            }}
            QSlider#berrySlider::handle:horizontal {{
                background-color: #ffffff;
                width: 12px;
                height: 12px;
                margin: 3px 3px;
                border-radius: 6px;
            }}
            QPushButton {{
                background-color: {surface}; color: {fg}; border: 1px solid {border};
                padding: 6px 12px; border-radius: 14px;
            }}
            QPushButton:hover {{ background-color: {border}; }}
            QPushButton#saveButton {{
                background-color: {accent}; color: #ffffff; border: none;
                border-radius: 18px; min-height: 36px; max-height: 36px;
                padding: 0px 14px; font-size: 13px; font-weight: bold;
            }}
            QPushButton#saveButton:hover {{ background-color: {accent}; opacity: 0.9; }}
            QPushButton#cancelButton {{
                background-color: {surface}; color: {fg}; border: 1px solid {border};
                border-radius: 18px; min-height: 36px; max-height: 36px;
                padding: 0px 14px; font-size: 13px; font-weight: bold;
            }}
            QPushButton#cancelButton:hover {{ background-color: {border}; }}
            QWidget#bottomContainer {{ background-color: transparent; }}
            QWidget#bottomPillBar {{
                background-color: {panel}; border-radius: 28px; border: 1px solid {border};
            }}
            QSpinBox {{
                background-color: {panel}; color: {fg}; border: 1px solid {border};
                border-radius: 4px; padding: 5px;
            }}
            QScrollArea#controlsScroll QScrollBar:vertical {{
                background: {surface};
                width: 8px;
                margin: 0px;
                border: none;
            }}
            QScrollArea#controlsScroll QScrollBar::handle:vertical {{
                background: {scrollbar_thumb};
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollArea#controlsScroll QScrollBar::handle:vertical:hover {{
                background: {scrollbar_thumb_hover};
            }}
            QScrollArea#controlsScroll QScrollBar::add-line:vertical,
            QScrollArea#controlsScroll QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollArea#controlsScroll QScrollBar::add-page:vertical,
            QScrollArea#controlsScroll QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
# ── Bento WebUI settings -----------------------------------------------------
try:
    if getattr(mw, "onigiri_api", {}).get("id") != "1011095603":
        raise ImportError("Onigiri Bento API is not active")
    _bws = importlib.import_module("1011095603.api.widget_settings")
except Exception:
    _bws = None

if _bws is not None:
    class SettingsDialog(_bws.BentoSettingsDialog):
        def __init__(self, parent=None, addon_package=""):
            package = mw.addonManager.addonFromModule(addon_package or __name__)
            source = mw.addonManager.getConfig(package) or {}
            defaults = {
                "layout": "layout1", "theme": "auto", "bg_opacity": 100,
                "layout1_light_fg": "#02FF68", "layout1_dark_fg": "#02FF68",
                "layout2_light_fg": "#a855f7", "layout2_dark_fg": "#c084fc",
                "layout3_light_fg": "#22c55e", "layout3_dark_fg": "#4ade80",
                "bg_light_color": "#ffffff", "bg_dark_color": "#000000",
                "manual_widget_width": 200, "manual_widget_height": 200,
            }

            def save(updated):
                source.clear(); source.update(copy.deepcopy(updated))
                mw.addonManager.writeConfig(package, source)
                if getattr(mw, "state", "") == "deckBrowser":
                    mw.deckBrowser.refresh()

            def preview(updated, variant, theme):
                addon = importlib.import_module(__package__)
                # ``theme`` is the preview environment (the Light/Dark
                # control above the stage).  Power's setting determines the
                # widget itself: forced Light/Dark always wins; Auto follows
                # that environment, just as it follows Anki in production.
                preview_is_dark = theme == "dark"
                configured_theme = str(updated.get("theme", "auto")).lower()
                if configured_theme == "light":
                    widget_is_dark = False
                elif configured_theme == "dark":
                    widget_is_dark = True
                else:
                    widget_is_dark = preview_is_dark
                info = addon.get_preview_battery_info(charging=variant == "charging")
                body = addon.generate_battery_html(updated, info, widget_is_dark)
                # The wallpaper is the surrounding Anki environment, not
                # Power's forced widget theme.  This makes forced themes
                # visibly distinct while preserving Auto's system behavior.
                return _bws.preview_document(
                    body,
                    dark=preview_is_dark,
                    wallpaper=bento_integration.main_menu_wallpaper(preview_is_dark),
                )

            color_fields = []
            for layout, label in (("layout1", "Slider"), ("layout2", "Bar"), ("layout3", "Radial")):
                color_fields.extend([
                    _bws.field(f"{layout}_light_fg", f"{label} · Light", "color", default=defaults[f"{layout}_light_fg"], show_if={"layout": layout}),
                    _bws.field(f"{layout}_dark_fg", f"{label} · Dark", "color", default=defaults[f"{layout}_dark_fg"], show_if={"layout": layout}),
                ])
            color_fields.extend([
                _bws.field("bg_light_color", "Background · Light", "color", default="#ffffff"),
                _bws.field("bg_dark_color", "Background · Dark", "color", default="#000000"),
                _bws.field("bg_opacity", "Background opacity", "range", default=100, minimum=0, maximum=100, unit="%"),
            ])
            pages = [
                _bws.page("appearance", "Appearance", [
                    _bws.section("Widget style", [
                        _bws.field("layout", "Layout", "select", default="layout1", options=[
                            {"value": "layout1", "label": "Slider"}, {"value": "layout2", "label": "Bar"}, {"value": "layout3", "label": "Radial"},
                        ]),
                        _bws.field("theme", "Theme", "select", default="auto", options=[
                            {"value": "auto", "label": "Auto"},
                            {"value": "light", "label": "Light"},
                            {"value": "dark", "label": "Dark"},
                        ]),
                    ]),
                    _bws.section("Colors", color_fields),
                ], "Battery layout, theme, and colors.", "P"),
            ]
            super().__init__(
                parent, title="Power", subtitle="Battery status on your Anki menu", accent="#38DC75",
                pages=pages, config=source, defaults=defaults, save_callback=save,
                logo_path=os.path.join(os.path.dirname(__file__), "power_logo.svg"),
                mini_logo_path=os.path.join(os.path.dirname(__file__), "power_mini_logo.svg"),
                preview_callback=preview, preview_variants=[
                    {"value": "battery", "label": "On battery"}, {"value": "charging", "label": "Charging"},
                ], bugs_url="https://github.com/thepeacemonk/Power",
            )
