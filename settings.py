# settings.py
# This file contains the code for the add-on's settings dialog.

import os
import webbrowser
from aqt import mw
from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QGroupBox,
    QRadioButton,
    QLabel,
    QWidget,
    QFormLayout,
    QDialogButtonBox,
    QColorDialog,
    QColor,
    QSlider,
    QSpinBox,
    Qt,
    QPixmap,
    QScrollArea,
    QLineEdit,
    pyqtSignal,
)
from aqt.utils import showInfo
from aqt.theme import theme_manager

# A custom QLabel that emits a 'clicked' signal on mouse press.
class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

# Helper function to set the style on the color swatch label.
# This ensures the border-radius and color are applied reliably.
def set_label_style(label, color_str):
    """Sets the label's stylesheet directly, making it circular and colored."""
    label.setStyleSheet(f"""
        QLabel {{
            background-color: {color_str};
            border: 1px solid #ccc;
            border-radius: 12px;
        }}
    """)

# Function to create a new color picker widget using the ClickableLabel
def create_color_picker(initial_color, parent):
    """Creates a widget with a text field for hex code and a clickable color swatch."""
    # Container widget
    widget = QWidget(parent)
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    # Line edit for hex code
    line_edit = QLineEdit(initial_color)
    line_edit.setObjectName("ColorLineEdit")
    line_edit.setFixedWidth(90)

    # Use the custom ClickableLabel for the color swatch
    color_swatch = ClickableLabel()
    color_swatch.setObjectName("ColorPickerSwatch")
    color_swatch.setFixedSize(24, 24)
    color_swatch.setCursor(Qt.CursorShape.PointingHandCursor)
    
    # Use the helper function to set the initial style
    set_label_style(color_swatch, initial_color)

    layout.addWidget(line_edit)
    layout.addWidget(color_swatch)

    widget.setLayout(layout)

    return widget, line_edit, color_swatch

class SettingsDialog(QDialog):
    def __init__(self, parent=None, addon_package=""):
        super().__init__(parent)
        self.setWindowTitle("Power Settings")
        self.setFixedWidth(450)
        self.resize(450, 650) # Set a default size

        # Load current config, providing a default if it's missing
        self.addon_package = addon_package
        self.config = mw.addonManager.getConfig(self.addon_package) or {}

        # --- Scroll Area Setup ---
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("ScrollArea")
        dialog_layout.addWidget(scroll_area)

        scroll_content_widget = QWidget()
        scroll_area.setWidget(scroll_content_widget)

        # Main layout for all content, placed inside the scroll area
        main_layout = QVBoxLayout(scroll_content_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # --- Header Image ---
        header_label = QLabel()
        header_label.setObjectName("HeaderImage")
        addon_dir = os.path.dirname(__file__)
        image_path = os.path.join(addon_dir, "Power.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # Scale pixmap to a suitable width while keeping aspect ratio
            scaled_pixmap = pixmap.scaledToWidth(250, Qt.TransformationMode.SmoothTransformation)
            header_label.setPixmap(scaled_pixmap)
            header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(header_label)

        # --- Action Buttons ---
        button_layout = QHBoxLayout()
        donate_button = QPushButton("Donate")
        report_button = QPushButton("Report Bug")
        donate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        report_button.setCursor(Qt.CursorShape.PointingHandCursor)
        donate_button.setObjectName("DonateButton")
        report_button.setObjectName("ReportButton")

        button_layout.addStretch()
        button_layout.addWidget(donate_button)
        button_layout.addWidget(report_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # Add a little space
        main_layout.addSpacing(15)

        # Connect buttons to open URLs
        donate_button.clicked.connect(lambda: webbrowser.open("https://buymeacoffee.com/peacemonk"))
        report_button.clicked.connect(lambda: webbrowser.open("https://github.com/thepeacemonk/Power"))

        # --- Layout Selection ---
        layout_group = QGroupBox("Widget Layout")
        layout_vbox = QVBoxLayout()
        self.layout1_radio = QRadioButton("Layout 1 (Green Slider)")
        self.layout2_radio = QRadioButton("Layout 2 (Segmented Bar)")
        self.layout3_radio = QRadioButton("Layout 3 (Radial Bar)")
        
        current_layout = self.config.get("layout", "layout1")
        if current_layout == "layout2":
            self.layout2_radio.setChecked(True)
        elif current_layout == "layout3":
            self.layout3_radio.setChecked(True)
        else:
            self.layout1_radio.setChecked(True)

        layout_vbox.addWidget(self.layout1_radio)
        layout_vbox.addWidget(self.layout2_radio)
        layout_vbox.addWidget(self.layout3_radio)
        layout_group.setLayout(layout_vbox)
        main_layout.addWidget(layout_group)

        # --- Theme Selection ---
        theme_group = QGroupBox("Appearance Theme")
        theme_vbox = QVBoxLayout()
        self.auto_theme_radio = QRadioButton("Automatic (follows Anki's theme)")
        self.light_theme_radio = QRadioButton("Force Light Mode")
        self.dark_theme_radio = QRadioButton("Force Dark Mode")
        theme_map = {
            "auto": self.auto_theme_radio,
            "light": self.light_theme_radio,
            "dark": self.dark_theme_radio,
        }
        current_theme = self.config.get("theme", "auto")
        theme_map.get(current_theme, self.auto_theme_radio).setChecked(True)
        theme_vbox.addWidget(self.auto_theme_radio)
        theme_vbox.addWidget(self.light_theme_radio)
        theme_vbox.addWidget(self.dark_theme_radio)
        theme_group.setLayout(theme_vbox)
        main_layout.addWidget(theme_group)

        # --- Color Configuration ---
        colors_group = QGroupBox("Color Customization")
        colors_form_layout = QFormLayout()
        colors_form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        colors_form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        colors_form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)


        # Layout 1 Colors
        (
            self.l1_light_fg_widget, self.l1_light_fg_edit, self.l1_light_fg_swatch
        ) = create_color_picker(self.config.get("layout1_light_fg", "#02FF68"), self)
        (
            self.l1_dark_fg_widget, self.l1_dark_fg_edit, self.l1_dark_fg_swatch
        ) = create_color_picker(self.config.get("layout1_dark_fg", "#02FF68"), self)
        colors_form_layout.addRow("<b>Layout 1 - Slider Color</b>", None)
        colors_form_layout.addRow("Light Mode:", self.l1_light_fg_widget)
        colors_form_layout.addRow("Dark Mode:", self.l1_dark_fg_widget)
        
        colors_form_layout.addRow(QWidget(), None) # Spacer

        # Layout 2 Colors
        (
            self.l2_light_fg_widget, self.l2_light_fg_edit, self.l2_light_fg_swatch
        ) = create_color_picker(self.config.get("layout2_light_fg", "#9ca3af"), self)
        (
            self.l2_dark_fg_widget, self.l2_dark_fg_edit, self.l2_dark_fg_swatch
        ) = create_color_picker(self.config.get("layout2_dark_fg", "#6b7280"), self)
        colors_form_layout.addRow("<b>Layout 2 - Bar Color</b>", None)
        colors_form_layout.addRow("Light Mode:", self.l2_light_fg_widget)
        colors_form_layout.addRow("Dark Mode:", self.l2_dark_fg_widget)
        
        colors_form_layout.addRow(QWidget(), None) # Spacer

        # Layout 3 Colors
        (
            self.l3_light_fg_widget, self.l3_light_fg_edit, self.l3_light_fg_swatch
        ) = create_color_picker(self.config.get("layout3_light_fg", "#22c55e"), self)
        (
            self.l3_dark_fg_widget, self.l3_dark_fg_edit, self.l3_dark_fg_swatch
        ) = create_color_picker(self.config.get("layout3_dark_fg", "#4ade80"), self)
        colors_form_layout.addRow("<b>Layout 3 - Radial Bar Color</b>", None)
        colors_form_layout.addRow("Light Mode:", self.l3_light_fg_widget)
        colors_form_layout.addRow("Dark Mode:", self.l3_dark_fg_widget)

        colors_form_layout.addRow(QWidget(), None) # Spacer

        # Widget Background
        colors_form_layout.addRow("<b>Widget Background</b>", None)
        (
            self.bg_light_widget, self.bg_light_edit, self.bg_light_swatch
        ) = create_color_picker(self.config.get("bg_light_color", "#ffffff"), self)
        (
            self.bg_dark_widget, self.bg_dark_edit, self.bg_dark_swatch
        ) = create_color_picker(self.config.get("bg_dark_color", "#000000"), self)
        colors_form_layout.addRow("Light Mode Color:", self.bg_light_widget)
        colors_form_layout.addRow("Dark Mode Color:", self.bg_dark_widget)

        # Opacity Slider
        opacity_layout = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_spinbox = QSpinBox()
        self.opacity_spinbox.setRange(0, 100)
        self.opacity_spinbox.setSuffix("%")
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_spinbox)
        self.opacity_slider.valueChanged.connect(self.opacity_spinbox.setValue)
        self.opacity_spinbox.valueChanged.connect(self.opacity_slider.setValue)
        initial_opacity = self.config.get("bg_opacity", 100)
        self.opacity_slider.setValue(initial_opacity)
        colors_form_layout.addRow("Background Opacity:", opacity_layout)

        colors_group.setLayout(colors_form_layout)
        main_layout.addWidget(colors_group)

        # --- Dialog Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        
        # Get buttons and assign object names for styling
        save_button = button_box.button(QDialogButtonBox.StandardButton.Save)
        save_button.setObjectName("SaveButton")
        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setObjectName("CancelButton")

        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        # --- Connect Signals ---
        # Connect swatch clicks to open the color dialog
        self.l1_light_fg_swatch.clicked.connect(lambda: self.pick_color(self.l1_light_fg_edit, self.l1_light_fg_swatch, "layout1_light_fg"))
        self.l1_dark_fg_swatch.clicked.connect(lambda: self.pick_color(self.l1_dark_fg_edit, self.l1_dark_fg_swatch, "layout1_dark_fg"))
        self.l2_light_fg_swatch.clicked.connect(lambda: self.pick_color(self.l2_light_fg_edit, self.l2_light_fg_swatch, "layout2_light_fg"))
        self.l2_dark_fg_swatch.clicked.connect(lambda: self.pick_color(self.l2_dark_fg_edit, self.l2_dark_fg_swatch, "layout2_dark_fg"))
        self.l3_light_fg_swatch.clicked.connect(lambda: self.pick_color(self.l3_light_fg_edit, self.l3_light_fg_swatch, "layout3_light_fg"))
        self.l3_dark_fg_swatch.clicked.connect(lambda: self.pick_color(self.l3_dark_fg_edit, self.l3_dark_fg_swatch, "layout3_dark_fg"))
        self.bg_light_swatch.clicked.connect(lambda: self.pick_color(self.bg_light_edit, self.bg_light_swatch, "bg_light_color"))
        self.bg_dark_swatch.clicked.connect(lambda: self.pick_color(self.bg_dark_edit, self.bg_dark_swatch, "bg_dark_color"))
        
        # Connect text edits to update the color swatch
        self.l1_light_fg_edit.editingFinished.connect(lambda: self.update_color_from_text(self.l1_light_fg_edit, self.l1_light_fg_swatch, "layout1_light_fg"))
        self.l1_dark_fg_edit.editingFinished.connect(lambda: self.update_color_from_text(self.l1_dark_fg_edit, self.l1_dark_fg_swatch, "layout1_dark_fg"))
        self.l2_light_fg_edit.editingFinished.connect(lambda: self.update_color_from_text(self.l2_light_fg_edit, self.l2_light_fg_swatch, "layout2_light_fg"))
        self.l2_dark_fg_edit.editingFinished.connect(lambda: self.update_color_from_text(self.l2_dark_fg_edit, self.l2_dark_fg_swatch, "layout2_dark_fg"))
        self.l3_light_fg_edit.editingFinished.connect(lambda: self.update_color_from_text(self.l3_light_fg_edit, self.l3_light_fg_swatch, "layout3_light_fg"))
        self.l3_dark_fg_edit.editingFinished.connect(lambda: self.update_color_from_text(self.l3_dark_fg_edit, self.l3_dark_fg_swatch, "layout3_dark_fg"))
        self.bg_light_edit.editingFinished.connect(lambda: self.update_color_from_text(self.bg_light_edit, self.bg_light_swatch, "bg_light_color"))
        self.bg_dark_edit.editingFinished.connect(lambda: self.update_color_from_text(self.bg_dark_edit, self.bg_dark_swatch, "bg_dark_color"))

        # --- Modern Stylesheet ---
        self.apply_stylesheet()


    def apply_stylesheet(self):
        # This method now applies a different stylesheet based on Anki's theme.
        
        # Base stylesheet for elements common to both themes
        base_stylesheet = """
            #ScrollArea { border: none; }
            #HeaderImage { margin-top: 10px; margin-bottom: 10px; }
            QPushButton {
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 14px;
            }
            QLineEdit#ColorLineEdit {
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 14px;
            }
            #DonateButton, #ReportButton, #SaveButton {
                font-weight: bold;
                border: none;
                color: white;
            }
            QGroupBox {
                border-radius: 8px;
                margin-top: 1em;
                padding: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QRadioButton, QLabel, QSpinBox {
                font-size: 14px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QDialogButtonBox QPushButton {
                min-width: 90px;
                font-weight: bold;
            }
            QScrollBar:vertical {
                border: none;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """

        light_theme_overrides = """
            QDialog { background-color: #f7f7f7; }
            QPushButton { border: 1px solid #dcdcdc; background-color: #fff; }
            QPushButton:hover { background-color: #f0f0f0; }
            QLineEdit#ColorLineEdit { border: 1px solid #dcdcdc; }
            QLineEdit#ColorLineEdit:focus { border-color: #a0a0a0; }
            #DonateButton, #ReportButton, #SaveButton { background-color: #6b7280; }
            #DonateButton:hover, #ReportButton:hover, #SaveButton:hover { background-color: #4b5563; }
            QGroupBox { border: 1px solid #e5e5e5; }
            QSlider::groove:horizontal { border: 1px solid #ccc; background: #f0f0f0; }
            QSlider::handle:horizontal { background: #9ca3af; border: 1px solid #9ca3af; }
            QScrollBar:vertical { background: #f7f7f7; }
            QScrollBar::handle:vertical { background: #dcdcdc; }
            QScrollBar::handle:vertical:hover { background: #c0c0c0; }
        """

        dark_theme_overrides = """
            QDialog { background-color: #2e2e2e; color: #e0e0e0; }
            QPushButton { border: 1px solid #4a4a4a; background-color: #3a3a3a; color: #e0e0e0; }
            QPushButton:hover { background-color: #4a4a4a; }
            QLineEdit#ColorLineEdit { border: 1px solid #4a4a4a; background-color: #3a3a3a; color: #e0e0e0; }
            QLineEdit#ColorLineEdit:focus { border-color: #777; }
            #DonateButton, #ReportButton, #SaveButton { background-color: #555; }
            #DonateButton:hover, #ReportButton:hover, #SaveButton:hover { background-color: #666; }
            QGroupBox { border: 1px solid #4a4a4a; color: #e0e0e0; }
            QGroupBox::title { color: #e0e0e0; }
            QRadioButton, QLabel, QSpinBox { color: #e0e0e0; }
            QSlider::groove:horizontal { border: 1px solid #4a4a4a; background: #2e2e2e; }
            QSlider::handle:horizontal { background: #6b7280; border: 1px solid #6b7280; }
            QScrollBar:vertical { background: #2e2e2e; }
            QScrollBar::handle:vertical { background: #4a4a4a; }
            QScrollBar::handle:vertical:hover { background: #5a5a5a; }
        """
        
        if theme_manager.night_mode:
            self.setStyleSheet(base_stylesheet + dark_theme_overrides)
        else:
            self.setStyleSheet(base_stylesheet + light_theme_overrides)

    def update_color_from_text(self, line_edit, label, config_key):
        """Updates the color swatch and config from the QLineEdit's text."""
        hex_color = line_edit.text()
        q_color = QColor(hex_color)

        if q_color.isValid():
            set_label_style(label, hex_color)
            self.config[config_key] = hex_color
        else:
            # Revert to the last valid color if input is invalid
            old_color = self.config.get(config_key, "#ffffff")
            line_edit.setText(old_color)
            set_label_style(label, old_color)

    def pick_color(self, line_edit, label, config_key):
        """Opens a color dialog and updates the line edit, swatch, and config."""
        current_hex = line_edit.text()
        initial_qcolor = QColor(current_hex)
        
        color = QColorDialog.getColor(initial_qcolor, self, "Choose a color")

        if color.isValid():
            hex_color = color.name()
            self.config[config_key] = hex_color
            set_label_style(label, hex_color)
            line_edit.setText(hex_color)

    def save_settings(self):
        """Saves the current settings to the config file."""
        if self.layout2_radio.isChecked():
            self.config["layout"] = "layout2"
        elif self.layout3_radio.isChecked():
            self.config["layout"] = "layout3"
        else:
            self.config["layout"] = "layout1"

        if self.auto_theme_radio.isChecked():
            self.config["theme"] = "auto"
        elif self.light_theme_radio.isChecked():
            self.config["theme"] = "light"
        else:
            self.config["theme"] = "dark"
        
        self.config["bg_opacity"] = self.opacity_slider.value()
        
        mw.addonManager.writeConfig(self.addon_package, self.config)
        showInfo("Power settings saved. Please restart Anki to see all changes.", parent=self)
        self.accept()

