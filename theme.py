"""
Thème visuel de l'application — inspiré de l'impression 3D :
fond sombre "atelier", accent orange (buse chauffante / filament PLA),
touches cyan (LED de statut / refroidissement) pour les éléments positifs.
"""

# Palette
BG_DARK = "#15171c"
BG_PANEL = "#1d2027"
BG_PANEL_ALT = "#242832"
BORDER = "#333846"
TEXT = "#e8e9ed"
TEXT_MUTED = "#9096a3"
ACCENT = "#ff6a3d"        # orange filament / buse chaude
ACCENT_HOVER = "#ff7f57"
ACCENT_DARK = "#d6551f"
CYAN = "#3ddad0"          # cyan "LED statut"

MODERN_QSS = f"""
* {{
    font-family: "IBM Plex Sans", "Segoe UI", "Arial", sans-serif;
    font-size: 10.5pt;
    color: {TEXT};
}}

QMainWindow, QWidget {{
    background-color: {BG_DARK};
}}

/* --- Bannière d'en-tête --- */
QLabel#AppBanner {{
    background-color: {BG_PANEL};
    color: {TEXT};
    font-size: 17pt;
    font-weight: 700;
    padding: 14px 20px;
    border-bottom: 3px solid {ACCENT};
}}
QLabel#AppBannerSub {{
    color: {TEXT_MUTED};
    font-size: 9pt;
    padding: 0px 20px 10px 20px;
    background-color: {BG_PANEL};
    border-bottom: 3px solid {ACCENT};
}}

/* --- Onglets --- */
QTabWidget::pane {{
    border: none;
    background-color: {BG_DARK};
}}
QTabBar::tab {{
    background-color: {BG_PANEL};
    color: {TEXT_MUTED};
    padding: 10px 22px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background-color: {ACCENT};
    color: #1a1a1a;
}}
QTabBar::tab:hover:!selected {{
    background-color: {BG_PANEL_ALT};
    color: {TEXT};
}}

/* --- Groupes --- */
QGroupBox {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
    margin-top: 14px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    top: 2px;
    padding: 0 6px;
    color: {ACCENT};
    font-weight: 700;
    letter-spacing: 0.5px;
}}

/* --- Champs de saisie --- */
QLineEdit, QComboBox {{
    background-color: {BG_PANEL_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_PANEL_ALT};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
    selection-color: #1a1a1a;
    outline: none;
}}

/* --- Boutons --- */
QPushButton {{
    background-color: {ACCENT};
    color: #1a1a1a;
    border: none;
    border-radius: 7px;
    padding: 9px 16px;
    font-weight: 700;
}}
QPushButton:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton:pressed {{
    background-color: {ACCENT_DARK};
}}
QPushButton:disabled {{
    background-color: {BORDER};
    color: {TEXT_MUTED};
}}

/* Boutons secondaires (ex: sauvegarder les taux) qui n'ont pas besoin d'être criards */
QPushButton#Secondary {{
    background-color: {BG_PANEL_ALT};
    color: {TEXT};
    border: 1px solid {BORDER};
}}
QPushButton#Secondary:hover {{
    background-color: {BORDER};
}}

/* Bouton destructif (suppression) */
QPushButton#Danger {{
    background-color: transparent;
    color: #ff6b6b;
    border: 1px solid #5a3030;
}}
QPushButton#Danger:hover {{
    background-color: #3a1f1f;
}}

/* --- Résultats --- */
QLabel#ResultValue {{
    color: {TEXT};
    font-weight: 600;
}}
QLabel#PriceMain {{
    color: {CYAN};
    font-size: 14pt;
    font-weight: 800;
}}
QGroupBox#PriceCard {{
    background-color: #182a2a;
    border: 1px solid #28736f;
    border-radius: 10px;
}}
QGroupBox#PriceCard::title {{
    color: {CYAN};
}}
QLabel#PriceHero {{
    color: {CYAN};
    font-size: 22pt;
    font-weight: 900;
    font-family: "IBM Plex Mono", "Consolas", monospace;
    background-color: #102020;
    border: 1px solid #28736f;
    border-left: 5px solid {CYAN};
    border-radius: 7px;
    padding: 10px 14px;
}}
QLabel#PriceLow {{
    color: {TEXT};
    font-size: 19pt;
    font-weight: 800;
    font-family: "IBM Plex Mono", "Consolas", monospace;
    background-color: {BG_PANEL_ALT};
    border: 1px solid {BORDER};
    border-left: 4px solid {CYAN};
    border-radius: 6px;
    padding: 10px 16px;
    letter-spacing: 1px;
}}
QLabel#PriceHigh {{
    color: {ACCENT};
    font-size: 19pt;
    font-weight: 800;
    font-family: "IBM Plex Mono", "Consolas", monospace;
    background-color: #2a1c14;
    border: 1px solid {ACCENT_DARK};
    border-left: 4px solid {ACCENT};
    border-radius: 6px;
    padding: 10px 16px;
    letter-spacing: 1px;
}}

/* --- Tableau filaments --- */
QTableWidget {{
    background-color: {BG_PANEL};
    alternate-background-color: {BG_PANEL_ALT};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 8px;
    selection-background-color: {ACCENT};
    selection-color: #1a1a1a;
}}
QHeaderView::section {{
    background-color: {BG_PANEL_ALT};
    color: {TEXT_MUTED};
    padding: 8px;
    border: none;
    border-bottom: 2px solid {ACCENT};
    font-weight: 700;
    text-transform: uppercase;
    font-size: 8.5pt;
}}
QTableWidget::item {{
    padding: 4px;
}}

/* --- Scrollbars discrètes --- */
QScrollBar:vertical {{
    background: {BG_DARK};
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 5px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0px;
}}
"""
