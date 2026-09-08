"""
Calculateur de prix pour impression 3D — interface graphique principale.
Lancement : python appV1.py
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton, QGroupBox,
    QTabWidget, QMessageBox, QDialog, QDialogButtonBox, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QCheckBox, QStackedWidget, QTextEdit, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QFontDatabase

import database as db
import theme
import lang
from pricing import PricingInputs, calculer


def load_application_fonts() -> None:
    """Charge les fontes IBM Plex embarquées avant l'application du thème."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    font_directories = (root / "fonts", root / "assets" / "fonts")
    for font_name in (
        "IBMPlexSans-Regular.ttf",
        "IBMPlexSans-Medium.ttf",
        "IBMPlexSans-SemiBold.ttf",
        "IBMPlexSans-Bold.ttf",
        "IBMPlexMono-Regular.ttf",
        "IBMPlexMono-SemiBold.ttf",
        "IBMPlexMono-Bold.ttf",
    ):
        for font_directory in font_directories:
            font_path = font_directory / font_name
            if font_path.exists():
                QFontDatabase.addApplicationFont(str(font_path))
                break


def to_float(text: str, default: float = 0.0) -> float:
    """Conversion tolérante virgule/point, jamais de plantage sur une saisie invalide."""
    if not text:
        return default
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return default


class ParamField(QLineEdit):
    """Champ numérique qui se comporte bien avec la virgule (habitude FR) et le point."""
    def value(self, default: float = 0.0) -> float:
        return to_float(self.text(), default)

    def set_value(self, v) -> None:
        self.setText(str(v))


class DurationField(QWidget):
    """Sélecteur de durée Jours / Heures / Minutes, converti en heures pour le moteur."""

    durationChanged = Signal()

    def __init__(self, max_days: int = 99, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.days = self._create_combo(range(max_days + 1), lang.tr("calc.duration_days"))
        self.hours = self._create_combo(range(24), lang.tr("calc.duration_hours"))
        self.minutes = self._create_combo(range(60), lang.tr("calc.duration_minutes"))
        for combo in (self.days, self.hours, self.minutes):
            layout.addWidget(combo)
            combo.currentIndexChanged.connect(lambda _index: self.durationChanged.emit())

    def _create_combo(self, values, suffix: str) -> QComboBox:
        combo = QComboBox()
        for value in values:
            combo.addItem(f"{value} {suffix}", value)
        return combo

    def hours_value(self) -> float:
        """Retourne la durée totale en heures, unité attendue par pricing.calculer."""
        return (
            self.days.currentData() * 24
            + self.hours.currentData()
            + self.minutes.currentData() / 60
        )


class FilamentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(lang.tr("dialog.filament.title"))
        layout = QFormLayout(self)
        self.matiere = QLineEdit()
        self.couleur = QLineEdit()
        self.fournisseur = QLineEdit()
        self.prix_bobine = ParamField()
        self.prix_bobine_catalogue = ParamField()
        self.prix_bobine_catalogue.setPlaceholderText(lang.tr("dialog.filament.placeholder_catalogue"))
        self.poids_bobine = ParamField()
        self.poids_bobine.setText("1000")
        layout.addRow(lang.tr("dialog.filament.label_matiere"), self.matiere)
        layout.addRow(lang.tr("dialog.filament.label_couleur"), self.couleur)
        layout.addRow(lang.tr("dialog.filament.label_fournisseur"), self.fournisseur)
        layout.addRow(lang.tr("dialog.filament.label_prix_reel"), self.prix_bobine)
        layout.addRow(lang.tr("dialog.filament.label_prix_catalogue"), self.prix_bobine_catalogue)
        layout.addRow(lang.tr("dialog.filament.label_poids_bobine"), self.poids_bobine)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class PrinterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(lang.tr("dialog.printer.title"))
        layout = QFormLayout(self)
        self.nom = QLineEdit()
        self.nom.setPlaceholderText(lang.tr("dialog.printer.placeholder_nom"))
        layout.addRow(lang.tr("dialog.printer.label_nom"), self.nom)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class ConsumptionDialog(QDialog):
    def __init__(self, material: str = "", consumption_kw: float = 0.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle(lang.tr("dialog.conso.title"))
        layout = QFormLayout(self)
        self.matiere = QLineEdit(material)
        self.matiere.setPlaceholderText(lang.tr("dialog.conso.placeholder_matiere"))
        self.conso_kw = ParamField()
        self.conso_kw.set_value(consumption_kw)
        layout.addRow(lang.tr("dialog.conso.label_matiere"), self.matiere)
        layout.addRow(lang.tr("dialog.conso.label_puissance"), self.conso_kw)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class FilamentModuleDialog(QDialog):
    def __init__(self, name: str = "", consumption_kw: float = 0.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle(lang.tr("dialog.module.title"))
        layout = QFormLayout(self)
        self.nom = QLineEdit(name)
        self.nom.setPlaceholderText(lang.tr("dialog.module.placeholder_nom"))
        self.conso_kw = ParamField()
        self.conso_kw.set_value(consumption_kw)
        layout.addRow(lang.tr("dialog.module.label_nom"), self.nom)
        layout.addRow(lang.tr("dialog.module.label_puissance"), self.conso_kw)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class PrintedObjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(lang.tr("dialog.object.title"))
        layout = QFormLayout(self)
        self.name = QLineEdit()
        self.name.setPlaceholderText(lang.tr("dialog.object.placeholder_name"))
        self.notes = QTextEdit()
        self.notes.setPlaceholderText(lang.tr("dialog.object.placeholder_notes"))
        self.notes.setMinimumHeight(120)
        layout.addRow(lang.tr("dialog.object.label_name"), self.name)
        layout.addRow(lang.tr("dialog.object.label_notes"), self.notes)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class CalculatorTab(QWidget):
    def __init__(self, parameters_host=None, on_object_saved=None):
        super().__init__()
        print(">>> CalculatorTab V3 avec multicouleur et QStackedWidget")
        self.parameters_host = parameters_host
        self.on_object_saved = on_object_saved
        self.params = db.get_parametres()
        self._filaments: list[db.Filament] = []
        self._composition: list[dict] = []  # {matiere, couleur, poids_g, cout_g, cout_total}
        # APPEL DIFFÉRÉ → évite la destruction des widgets
        self._ready = False
        self._build_ui()


    def _post_init(self):
        self._refresh_data()
        self._recalculer()
        self._ready = True
    def _build_ui(self):
        root = QHBoxLayout(self)

        left = QVBoxLayout()
        grp_objet = QGroupBox(lang.tr("calc.group_object"))
        main_layout = QVBoxLayout(grp_objet)
        left.addWidget(grp_objet)
        self.btn_save_object = QPushButton(lang.tr("calc.btn_save_object"))
        self.btn_save_object.clicked.connect(self._save_object)
        main_layout.addWidget(self.btn_save_object)
        # Toggle multicouleur
        self.cb_multicolor = QCheckBox(lang.tr("calc.multicolor_checkbox"))
        self.cb_multicolor.stateChanged.connect(self._on_multicolor_toggled)
        main_layout.addWidget(self.cb_multicolor)

        # Stack pour basculer entre mono et multi
        self.filament_input_stack = QStackedWidget()

        # ─── MODE SINGLE FILAMENT ───
        w_single = QWidget(self.filament_input_stack)  # Parent explicite
        f_single = QFormLayout(w_single)

        # Création des widgets (sans point-virgule superflu)
        self.matiere_combo = QComboBox()
        self.matiere_combo.currentIndexChanged.connect(self._on_matiere_changed)

        self.couleur_combo = QComboBox()
        self.couleur_combo.currentIndexChanged.connect(self._recalculer)

        self.imprimante_combo = QComboBox()
        self.imprimante_combo.currentIndexChanged.connect(self._on_printer_changed)

        self.module_filament_combo = QComboBox()
        self.module_filament_combo.currentIndexChanged.connect(self._on_module_filament_changed)

        self.poids = ParamField()
        self.poids.setPlaceholderText(lang.tr("calc.placeholder_poids"))
        self.poids.textChanged.connect(self._recalculer)
        self.temps_impression = DurationField()
        self.temps_finition = DurationField()

        f_single.addRow(lang.tr("calc.label_matiere"), self.matiere_combo)
        f_single.addRow(lang.tr("calc.label_couleur"), self.couleur_combo)
        f_single.addRow(lang.tr("calc.label_imprimante"), self.imprimante_combo)
        f_single.addRow(lang.tr("calc.label_module_filament"), self.module_filament_combo)
        f_single.addRow(lang.tr("calc.label_poids"), self.poids)

        # Ajout de w_single au stack (c'est le "gardien" de la mémoire des widgets ici)
        self.filament_input_stack.addWidget(w_single)

        # ─── MODE MULTICOLOR ───
        w_multi = QWidget(self.filament_input_stack)  # Parent explicite
        lay_multi = QVBoxLayout(w_multi)

        self.tbl_composition = QTableWidget(0, 4)
        self.tbl_composition.setHorizontalHeaderLabels([
            lang.tr("calc.table_mat"), lang.tr("calc.table_couleur"),
            lang.tr("calc.table_poids"), lang.tr("calc.table_cout")
        ])
        self.tbl_composition.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_composition.setSelectionMode(QAbstractItemView.SingleSelection)
        lay_multi.addWidget(self.tbl_composition)

        btn_remove = QPushButton(lang.tr("calc.btn_remove_composition"))
        btn_remove.setObjectName("Secondary")
        btn_remove.clicked.connect(self._remove_selected_composition)
        lay_multi.addWidget(btn_remove)

        sel_lay = QHBoxLayout()
        self.matiere_combo_multi = QComboBox()
        self.matiere_combo_multi.currentIndexChanged.connect(self._on_matiere_multi_changed)

        self.couleur_combo_multi = QComboBox()
        self.poids_multi = ParamField()
        self.poids_multi.setPlaceholderText("g")

        btn_add = QPushButton(lang.tr("calc.btn_add_composition"))
        btn_add.clicked.connect(self._add_to_composition)

        sel_lay.addWidget(self.matiere_combo_multi, stretch=2)
        sel_lay.addWidget(self.couleur_combo_multi, stretch=2)
        sel_lay.addWidget(QLabel("g"))
        sel_lay.addWidget(self.poids_multi)
        sel_lay.addStretch()
        sel_lay.addWidget(btn_add)
        lay_multi.addLayout(sel_lay)

        self.filament_input_stack.addWidget(w_multi)
        main_layout.addWidget(self.filament_input_stack)

        duration_layout = QFormLayout()
        duration_layout.addRow(lang.tr("calc.label_temps_impression"), self.temps_impression)
        duration_layout.addRow(lang.tr("calc.label_temps_finition"), self.temps_finition)
        main_layout.addLayout(duration_layout)

        # ... (GROUPE COUTS / MARGE - TA CODE ORIGINAL EST BON, JE LE SAUTE POUR CONCISSE) ...
        grp_couts = QGroupBox(lang.tr("calc.group_couts"))
        f_couts = QFormLayout()
        self.taux_machine = ParamField()
        self.taux_machine.set_value(self.params.get("taux_machine_h", 0))
        self.conso_kw = ParamField()
        self.conso_kw.set_value(self.params.get("conso_kw", 0))
        self.conso_source = QLabel(lang.tr("calc.conso_default"))
        self.prix_kwh = ParamField()
        self.prix_kwh.set_value(self.params.get("prix_kwh", 0))
        self.taux_main_oeuvre = ParamField()
        self.taux_main_oeuvre.set_value(self.params.get("taux_main_oeuvre_h", 0))
        self.emballage = ParamField()
        self.emballage.set_value(self.params.get("emballage", 0))
        self.divers = ParamField()
        self.divers.set_value(self.params.get("divers", 0))
        f_couts.addRow(lang.tr("calc.label_taux_machine"), self.taux_machine)
        f_couts.addRow(lang.tr("calc.label_conso_imprimante"), self.conso_kw)
        f_couts.addRow("", self.conso_source)
        f_couts.addRow(lang.tr("calc.label_prix_kwh"), self.prix_kwh)
        f_couts.addRow(lang.tr("calc.label_taux_main_oeuvre"), self.taux_main_oeuvre)
        f_couts.addRow(lang.tr("calc.label_emballage"), self.emballage)
        f_couts.addRow(lang.tr("calc.label_divers"), self.divers)
        grp_couts.setLayout(f_couts)


        grp_marge = QGroupBox(lang.tr("calc.group_charges"))
        f_marge = QFormLayout()
        self.charges_pct = ParamField()
        self.charges_pct.set_value(self.params.get("taux_charges_pct", 0))
        self.marge_pct = ParamField()
        self.marge_pct.set_value(self.params.get("marge_cible_pct", 0))
        self.tva_pct = ParamField()
        self.tva_pct.set_value(self.params.get("tva_pct", 0))
        f_marge.addRow(lang.tr("calc.label_charges_pct"), self.charges_pct)
        f_marge.addRow(lang.tr("calc.label_marge_pct"), self.marge_pct)
        f_marge.addRow(lang.tr("calc.label_tva_pct"), self.tva_pct)
        grp_marge.setLayout(f_marge)
        if self.parameters_host is None:
            left.addWidget(grp_couts)
            left.addWidget(grp_marge)
        else:
            parameters_layout = QVBoxLayout(self.parameters_host)
            parameters_layout.addWidget(grp_couts)
            parameters_layout.addWidget(grp_marge)

        btn_row = QHBoxLayout()
        btn_save_params = QPushButton(lang.tr("calc.btn_save_params"))
        btn_save_params.setObjectName("Secondary")
        btn_save_params.clicked.connect(self._save_params)
        btn_row.addWidget(btn_save_params)
        if self.parameters_host is None:
            left.addLayout(btn_row)
        else:
            parameters_layout.addLayout(btn_row)
            parameters_layout.addStretch()
        left.addStretch()

        # ... (ZONE DROITE - TA CODE ORIGINAL EST BON, JE LE SAUTE POUR CONCISSE) ...
        right = QVBoxLayout()
        grp_res = QGroupBox(lang.tr("calc.group_detail"))
        grp_res.setObjectName("CostBreakdown")
        grid = QGridLayout()
        self.result_labels = {}
        rows = [
            ("cout_matiere", lang.tr("calc.row_matiere")),
            ("cout_machine", lang.tr("calc.row_machine")),
            ("cout_electrique", lang.tr("calc.row_electrique")),
            ("cout_module_filament", lang.tr("calc.row_module_filament")),
            ("montant_main_oeuvre", lang.tr("calc.row_finition")),
            ("cout_emballage", lang.tr("calc.row_emballage")),
            ("cout_divers", lang.tr("calc.row_divers")),
            ("cout_base", lang.tr("calc.row_total")),
            ("montant_charges", lang.tr("calc.row_charges")),
            ("prix_ht_plancher", lang.tr("calc.row_prix_plancher")),
        ]
        big_font = QFont()
        big_font.setPointSize(13)
        big_font.setBold(True)
        for row_i, (key, label) in enumerate(rows):
            lbl = QLabel(label)
            val = QLabel("0.00")
            val.setAlignment(Qt.AlignRight)
            val.setObjectName("ResultValue")
            grid.addWidget(lbl, row_i, 0)
            grid.addWidget(val, row_i, 1)
            self.result_labels[key] = val
        grp_res.setLayout(grid)
        right.addWidget(grp_res)

        grp_price = QGroupBox(lang.tr("calc.group_prix"))
        grp_price.setObjectName("PriceCard")
        price_grid = QGridLayout()
        price_grid.addWidget(QLabel(lang.tr("calc.label_prix_ht")), 0, 0)
        self.result_labels["prix_conseille_ht"] = QLabel("0.00")
        self.result_labels["prix_conseille_ht"].setObjectName("PriceMain")
        self.result_labels["prix_conseille_ht"].setAlignment(Qt.AlignRight)
        price_grid.addWidget(self.result_labels["prix_conseille_ht"], 0, 1)
        price_grid.addWidget(QLabel(lang.tr("calc.label_prix_ttc")), 1, 0)
        self.result_labels["prix_conseille_ttc"] = QLabel("0.00")
        self.result_labels["prix_conseille_ttc"].setObjectName("PriceHero")
        self.result_labels["prix_conseille_ttc"].setAlignment(Qt.AlignRight)
        price_grid.addWidget(self.result_labels["prix_conseille_ttc"], 1, 1)
        grp_price.setLayout(price_grid)
        right.addWidget(grp_price)

        grp_fourchette = QGroupBox(lang.tr("calc.group_fourchette"))
        f_grid = QGridLayout()
        f_grid.addWidget(QLabel(lang.tr("calc.label_prix_bas")), 0, 0)
        f_grid.addWidget(QLabel(lang.tr("calc.label_prix_haut")), 1, 0)
        self.prix_bas_lbl = QLabel("0.00")
        self.prix_haut_lbl = QLabel("0.00")
        self.prix_bas_lbl.setObjectName("PriceLow")
        self.prix_haut_lbl.setObjectName("PriceHigh")
        self.prix_bas_lbl.setAlignment(Qt.AlignRight)
        self.prix_haut_lbl.setAlignment(Qt.AlignRight)
        f_grid.addWidget(self.prix_bas_lbl, 0, 1)
        f_grid.addWidget(self.prix_haut_lbl, 1, 1)
        grp_fourchette.setLayout(f_grid)
        right.addWidget(grp_fourchette)

        right.addStretch()
        root.addLayout(left, 2)
        root.addLayout(right, 1)

        # Signaux globaux
        for w in (self.taux_machine, self.conso_kw, self.prix_kwh,
                  self.taux_main_oeuvre, self.emballage, self.divers,
                  self.charges_pct, self.marge_pct, self.tva_pct):
            w.textChanged.connect(self._recalculer)
        self.temps_impression.durationChanged.connect(self._recalculer)
        self.temps_finition.durationChanged.connect(self._recalculer)

    # ... (Méthodes utilitaires _on_module_filament_changed, etc. inchangées) ...

    def _refresh_data(self):
        """Charge les données DB et rafraichit les combos sans crash."""
        self._filaments = db.get_filaments()

        # Single mode
        matieres = sorted({f.matiere for f in self._filaments if f.matiere})
        self.matiere_combo.blockSignals(True)
        self.matiere_combo.clear()
        self.matiere_combo.addItem(lang.tr("calc.no_filament"))
        self.matiere_combo.addItems(matieres)
        self.matiere_combo.setCurrentIndex(0)
        self.matiere_combo.blockSignals(False)

        # Multi mode
        matieres_multi = sorted({f.matiere for f in self._filaments if f.matiere})
        self.matiere_combo_multi.blockSignals(True)
        self.matiere_combo_multi.clear()
        self.matiere_combo_multi.addItem("-- Matière --")
        self.matiere_combo_multi.addItems(matieres_multi)
        self.matiere_combo_multi.setCurrentIndex(0)
        self.matiere_combo_multi.blockSignals(False)

        # Mono-couleur : reset normal
        self.couleur_combo.clear()

        # Multi-couleur : NE PAS effacer la composition
        if not self.cb_multicolor.isChecked():
            self.couleur_combo_multi.clear()
            self._composition = []
            self.tbl_composition.setRowCount(0)

        # Appel sécurisé des handlers (qui redemandent blockSignals)
        self._on_matiere_changed()
        self._refresh_printers()
        self._refresh_filament_modules()

    def _refresh_filaments(self):
        if not self._ready:
            return  # Ignore les appels avant stabilisation

        self._refresh_data()
        self._recalculer()

    def _refresh_multi_combos(self):
        matiere = self.matiere_combo_multi.currentText()
        if not matiere or matiere == "-- Matière --":
            self.couleur_combo_multi.clear()
            return

        couleurs = sorted({f.couleur for f in self._filaments
                           if f.matiere == matiere and f.couleur})
        self.couleur_combo_multi.blockSignals(True)
        self.couleur_combo_multi.clear()
        self.couleur_combo_multi.addItem("-- Couleur --")
        self.couleur_combo_multi.addItems(couleurs)
        self.couleur_combo_multi.setCurrentIndex(0)
        self.couleur_combo_multi.blockSignals(False)



    def _on_multicolor_toggled(self, state):
        is_multi = self.cb_multicolor.isChecked()
        self.filament_input_stack.setCurrentIndex(1 if is_multi else 0)
        self._recalculer()

    def _on_matiere_changed(self):
        matiere = self.matiere_combo.currentText()
        self.couleur_combo.blockSignals(True)
        self.couleur_combo.clear()
        couleurs = sorted({f.couleur for f in self._filaments if f.matiere == matiere and f.couleur})
        if couleurs: self.couleur_combo.addItems(couleurs)
        self.couleur_combo.blockSignals(False)

        # En mode multicouleur : NE PAS recalculer ici
        if not self.cb_multicolor.isChecked():
            self._on_printer_changed()
            self._recalculer()

    def _on_matiere_multi_changed(self):
        self._refresh_multi_combos()

    # ─── Composition Multicolor ───
    def _add_to_composition(self):
        matiere = self.matiere_combo_multi.currentText()
        couleur = self.couleur_combo_multi.currentText()
        poids_g = self.poids_multi.value(0)

        if not couleur or couleur == "-- Couleur --":
            return QMessageBox.warning(self, "⚠️", "Sélectionnez une couleur valide.")
        if poids_g <= 0:
            return QMessageBox.warning(self, "⚠️", "Veuillez saisir un poids strictement positif.")

        f = next((f for f in self._filaments if f.matiere == matiere and f.couleur == couleur), None)
        cout_g = f.cout_par_g if f else 0.0
        row_data = {
            "matiere": matiere,
            "couleur": couleur,
            "poids_g": poids_g,
            "cout_g": cout_g,
            "cout_g_catalogue": f.cout_par_g_catalogue if f else 0.0,
            "has_catalogue": bool(f and f.prix_bobine_catalogue),
        }

        self._composition.append(row_data)
        self.tbl_composition.setRowCount(len(self._composition))
        for i, r in enumerate(self._composition):
            items = [r["matiere"], r["couleur"], str(r["poids_g"]), f"{r['cout_g'] * r['poids_g']:.2f}"]
            for c, txt in enumerate(items):
                itm = QTableWidgetItem(txt)
                itm.setData(Qt.UserRole, r)
                self.tbl_composition.setItem(i, c, itm)

        self.poids_multi.clear()
        self._recalculer()

    def _remove_selected_composition(self):
        row = self.tbl_composition.currentRow()
        if row < 0: return
        self._composition.pop(row)
        self.tbl_composition.removeRow(row)
        self._recalculer()

    def _save_object(self):
        dialog = PrintedObjectDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        name = dialog.name.text().strip()
        if not name:
            QMessageBox.warning(self, lang.tr("dialog.object.missing_name_title"),
                                lang.tr("dialog.object.missing_name_text"))
            return

        result = self._last_result
        composition = list(self._composition)
        poids_total = sum(item["poids_g"] for item in composition)
        if not self.cb_multicolor.isChecked():
            filament = self._current_filament()
            if filament:
                composition = [{
                    "matiere": filament.matiere,
                    "couleur": filament.couleur,
                    "poids_g": self.poids.value(),
                    "cout_g": filament.cout_par_g,
                }]
                poids_total = self.poids.value()
        data = {
            "mode_multicouleur": self.cb_multicolor.isChecked(),
            "matiere": self.matiere_combo.currentText(),
            "couleur": self.couleur_combo.currentText(),
            "poids_g": self.poids.value(),
            "poids_total_g": poids_total,
            "temps_impression_h": self.temps_impression.hours_value(),
            "temps_finition_h": self.temps_finition.hours_value(),
            "imprimante_id": self.imprimante_combo.currentData(),
            "module_filament_id": self.module_filament_combo.currentData(),
            "taux_machine_h": self.taux_machine.value(),
            "conso_kw": self.conso_kw.value(),
            "prix_kwh": self.prix_kwh.value(),
            "taux_main_oeuvre_h": self.taux_main_oeuvre.value(),
            "taux_charges_pct": self.charges_pct.value(),
            "marge_cible_pct": self.marge_pct.value(),
            "tva_pct": self.tva_pct.value(),
            "emballage": self.emballage.value(),
            "divers": self.divers.value(),
            "composition": composition,
            **{key: getattr(result, key) for key in (
                "cout_matiere", "cout_machine", "cout_electrique", "cout_emballage",
                "cout_divers", "montant_main_oeuvre", "cout_base", "prix_ht_plancher",
                "prix_conseille_ht", "prix_conseille_ttc",
            )},
        }
        db.add_printed_object(name, dialog.notes.toPlainText(), data)
        if self.on_object_saved:
            self.on_object_saved()
        QMessageBox.information(self, lang.tr("dialog.object.saved_title"),
                                lang.tr("dialog.object.saved_text", name=name))

    # ─── Moteur de calcul unifié ───
    def _recalculer(self):
        is_multi = self.cb_multicolor.isChecked()

        if is_multi:
            poids_total = sum(r["poids_g"] for r in self._composition)
            cout_filament_total = sum(r["cout_g"] * r["poids_g"] for r in self._composition)
            avg_cout_g = cout_filament_total / max(poids_total, 0.001) if poids_total > 0 else 0.0
            cout_filament_catalogue_total = sum(
                r.get("cout_g_catalogue", r["cout_g"]) * r["poids_g"]
                for r in self._composition
            )
            has_catalogue = any(r.get("has_catalogue", False) for r in self._composition)

            inputs = PricingInputs(
                poids_g=poids_total, temps_impression_h=self.temps_impression.hours_value(),
                temps_finition_h=self.temps_finition.hours_value(), cout_filament_par_g=avg_cout_g,
                cout_filament_total=cout_filament_total,
                taux_machine_h=self.taux_machine.value(), conso_kw=self.conso_kw.value(),
                conso_module_filament_kw=self._current_module_consumption(), prix_kwh=self.prix_kwh.value(),
                taux_main_oeuvre_h=self.taux_main_oeuvre.value(), taux_charges_pct=self.charges_pct.value(),
                emballage=self.emballage.value(), divers=self.divers.value(), marge_cible_pct=self.marge_pct.value(),
                tva_pct=self.tva_pct.value(),
            )
            self.prix_haut_lbl.setVisible(has_catalogue)
        else:
            f = self._current_filament()
            inputs = PricingInputs(
                poids_g=self.poids.value(), temps_impression_h=self.temps_impression.hours_value(),
                temps_finition_h=self.temps_finition.hours_value(),
                cout_filament_par_g=f.cout_par_g if f else 0.0, cout_filament_total=0.0,
                taux_machine_h=self.taux_machine.value(), conso_kw=self.conso_kw.value(),
                conso_module_filament_kw=self._current_module_consumption(), prix_kwh=self.prix_kwh.value(),
                taux_main_oeuvre_h=self.taux_main_oeuvre.value(), taux_charges_pct=self.charges_pct.value(),
                emballage=self.emballage.value(), divers=self.divers.value(), marge_cible_pct=self.marge_pct.value(),
                tva_pct=self.tva_pct.value(),
            )
            self.prix_haut_lbl.setVisible(f is not None and f.prix_bobine_catalogue is not None)

        r = calculer(inputs)
        self._last_result = r
        devise = self.params.get("devise", "EUR")
        for key, lbl in self.result_labels.items():
            lbl.setText(f"{getattr(r, key):.2f} {devise}")

        self.prix_bas_lbl.setText(f"{r.prix_conseille_ttc:.2f} {devise}")
        if is_multi and has_catalogue:
            inputs_haut = PricingInputs(**{
                **inputs.__dict__,
                "cout_filament_par_g": cout_filament_catalogue_total / max(poids_total, 0.001),
                "cout_filament_total": cout_filament_catalogue_total,
            })
            r_haut = calculer(inputs_haut)
            self.prix_haut_lbl.setText(f"{r_haut.prix_conseille_ttc:.2f} {devise}")
        elif not is_multi and f is not None and f.prix_bobine_catalogue:
            inputs_haut = PricingInputs(**{**inputs.__dict__, "cout_filament_par_g": f.cout_par_g_catalogue})
            r_haut = calculer(inputs_haut)
            self.prix_haut_lbl.setText(f"{r_haut.prix_conseille_ttc:.2f} {devise}")
        elif not is_multi:
            self.prix_haut_lbl.setVisible(False) if f is None else self.prix_haut_lbl.setVisible(True)

    # ─── Méthodes utilitaires obligatoires (compatibilité onglets) ───
    def _refresh_printers(self):
        selected_id = self.imprimante_combo.currentData()
        saved_id = self.params.get("imprimante_id")
        self.imprimante_combo.blockSignals(True)
        self.imprimante_combo.clear()
        for printer in db.get_printers():
            self.imprimante_combo.addItem(printer.nom, printer.id)
        self.imprimante_combo.blockSignals(False)
        target_id = selected_id if selected_id is not None else saved_id
        index = self.imprimante_combo.findData(int(target_id)) if target_id else 0
        self.imprimante_combo.setCurrentIndex(index if index >= 0 else 0)
        self._on_printer_changed()

    def _on_printer_changed(self):
        printer_id = self.imprimante_combo.currentData()
        if printer_id is not None:
            db.set_parametre("imprimante_id", str(printer_id))
        else:
            db.set_parametre("imprimante_id", "")

        self._apply_printer_consumption()
        self._recalculer()

    def _apply_printer_consumption(self):
        printer_id = self.imprimante_combo.currentData()
        matiere = self.matiere_combo.currentText() if not self.cb_multicolor.isChecked() else ""
        # En multi, on ne met pas à jour la consommation auto (l'utilisateur gère ses composants)
        if not matiere: return

        consumption_kw = db.get_printer_consumption(printer_id, matiere)
        printer_name = self.imprimante_combo.currentText()
        if consumption_kw is None:
            self.conso_source.setText(lang.tr("calc.conso_default_no_profile"))
            return
        self.conso_kw.set_value(consumption_kw)
        self.conso_source.setText(
            lang.tr("calc.conso_profile", printer=printer_name, material=matiere, watts=f"{consumption_kw * 1000:.0f}")
        )

    def _refresh_filament_modules(self):
        selected_id = self.module_filament_combo.currentData()
        saved_id = self.params.get("module_filament_id")
        self._filament_modules = {module.id: module for module in db.get_filament_modules()}
        self.module_filament_combo.blockSignals(True)
        self.module_filament_combo.clear()
        self.module_filament_combo.addItem(lang.tr("calc.no_filament_module"), None)
        for module in self._filament_modules.values():
            self.module_filament_combo.addItem(module.nom, module.id)
        self.module_filament_combo.blockSignals(False)
        target_id = selected_id if selected_id is not None else saved_id
        index = self.module_filament_combo.findData(int(target_id)) if target_id else 0
        self.module_filament_combo.setCurrentIndex(index if index >= 0 else 0)
        self._on_module_filament_changed()

    def _on_module_filament_changed(self):
        module_id = self.module_filament_combo.currentData()
        db.set_parametre("module_filament_id", str(module_id) if module_id is not None else "")
        self._recalculer()

    def _current_module_consumption(self):
        module = getattr(self, '_filament_modules', {}).get(self.module_filament_combo.currentData())
        return module.conso_kw if module else 0.0

    def _current_filament(self):
        matiere = self.matiere_combo.currentText()
        couleur = self.couleur_combo.currentText()
        for f in self._filaments:
            if f.matiere == matiere and f.couleur == couleur: return f
        return None

    def _current_cout_par_g(self):
        f = self._current_filament()
        return f.cout_par_g if f else 0.0

    def _save_params(self):
        db.set_parametre("taux_machine_h", str(self.taux_machine.value()))
        db.set_parametre("conso_kw", str(self.conso_kw.value()))
        db.set_parametre("prix_kwh", str(self.prix_kwh.value()))
        db.set_parametre("taux_main_oeuvre_h", str(self.taux_main_oeuvre.value()))
        db.set_parametre("emballage", str(self.emballage.value()))
        db.set_parametre("divers", str(self.divers.value()))
        db.set_parametre("taux_charges_pct", str(self.charges_pct.value()))
        db.set_parametre("marge_cible_pct", str(self.marge_pct.value()))
        db.set_parametre("tva_pct", str(self.tva_pct.value()))
        QMessageBox.information(self, lang.tr("calc.msg_saved_title"), lang.tr("calc.msg_saved_text"))



class FilamentsTab(QWidget):
    def __init__(self, on_change_callback):
        super().__init__()
        self.on_change_callback = on_change_callback
        self._filaments: list[db.Filament] = []
        self.COLUMNS = [
            ("matiere", lang.tr("filaments.col_matiere")),
            ("couleur", lang.tr("filaments.col_couleur")),
            ("fournisseur", lang.tr("filaments.col_fournisseur")),
            ("prix_bobine", lang.tr("filaments.col_prix_reel")),
            ("prix_bobine_catalogue", lang.tr("filaments.col_prix_catalogue")),
            ("poids_bobine_g", lang.tr("filaments.col_poids_bobine")),
            ("cout_par_g", lang.tr("filaments.col_cout_g")),
        ]
        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        btn_add = QPushButton(lang.tr("filaments.btn_add"))
        btn_add.clicked.connect(self._add_filament)
        btn_delete = QPushButton(lang.tr("filaments.btn_delete"))
        btn_delete.setObjectName("Danger")
        btn_delete.clicked.connect(self._delete_selected)
        btn_export = QPushButton(lang.tr("filaments.btn_export"))
        btn_export.clicked.connect(self._export_csv)
        btn_import = QPushButton(lang.tr("filaments.btn_import"))
        btn_import.clicked.connect(self._import_csv)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_delete)
        btn_row.addWidget(btn_export)
        btn_row.addWidget(btn_import)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel(lang.tr("filaments.filter_label")))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(lang.tr("filaments.filter_placeholder"))
        self.search_box.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search_box)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([label for _, label in self.COLUMNS])
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self._refresh()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, lang.tr("filaments.export_dialog_title"), "filaments.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            n = db.export_filaments_csv(path)
            QMessageBox.information(self, lang.tr("filaments.export_done_title"),
                                     lang.tr("filaments.export_done_text", n=n, path=path))
        except OSError as e:
            QMessageBox.critical(self, lang.tr("common.error_title"), lang.tr("common.write_error_text", error=e))

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, lang.tr("filaments.import_dialog_title"), "", "CSV (*.csv)")
        if not path:
            return
        try:
            added, updated, errors = db.import_filaments_csv(path)
        except OSError as e:
            QMessageBox.critical(self, lang.tr("common.error_title"), lang.tr("common.read_error_text", error=e))
            return
        self._refresh()
        self.on_change_callback()
        msg = lang.tr("filaments.import_done_text", added=added, updated=updated)
        if errors:
            msg += lang.tr("filaments.import_ignored_lines") + "\n".join(errors[:10])
            if len(errors) > 10:
                msg += "\n" + lang.tr("filaments.import_more_errors", n=len(errors) - 10)
        QMessageBox.information(self, lang.tr("filaments.import_done_title"), msg)

    def _refresh(self):
        self._filaments = db.get_filaments()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._filaments))
        for row_i, f in enumerate(self._filaments):
            values = {
                "matiere": f.matiere or "",
                "couleur": f.couleur or "",
                "fournisseur": f.fournisseur or "",
                "prix_bobine": f.prix_bobine,
                "prix_bobine_catalogue": f.prix_bobine_catalogue if f.prix_bobine_catalogue else "",
                "poids_bobine_g": f.poids_bobine_g,
                "cout_par_g": round(f.cout_par_g, 4),
            }
            for col_i, (key, _label) in enumerate(self.COLUMNS):
                item = QTableWidgetItem()
                val = values[key]
                if isinstance(val, (int, float)):
                    item.setData(Qt.DisplayRole, val)
                else:
                    item.setText(str(val))
                item.setData(Qt.UserRole, f.id)
                self.table.setItem(row_i, col_i, item)
        self.table.setSortingEnabled(True)
        self._apply_filter()

    def _apply_filter(self):
        text = self.search_box.text().strip().lower()
        for row in range(self.table.rowCount()):
            if not text:
                self.table.setRowHidden(row, False)
                continue
            match = any(
                text in (self.table.item(row, col).text().lower())
                for col in range(self.table.columnCount())
            )
            self.table.setRowHidden(row, not match)

    def _selected_filament_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _add_filament(self):
        dlg = FilamentDialog(self)
        if dlg.exec() == QDialog.Accepted:
            if not dlg.matiere.text().strip() and not dlg.couleur.text().strip():
                QMessageBox.warning(self, lang.tr("filaments.missing_fields_title"),
                                     lang.tr("filaments.missing_fields_text"))
                return
            db.add_filament(
                dlg.matiere.text().strip(),
                dlg.couleur.text().strip(),
                dlg.fournisseur.text().strip(),
                dlg.prix_bobine.value(),
                dlg.prix_bobine_catalogue.value(0) or None,
                dlg.poids_bobine.value(1000),
            )
            self._refresh()
            self.on_change_callback()

    def _delete_selected(self):
        fid = self._selected_filament_id()
        if fid is None:
            QMessageBox.information(self, lang.tr("common.no_selection_title"),
                                     lang.tr("common.no_selection_filament"))
            return
        rep = QMessageBox.question(
            self, lang.tr("common.confirm_delete_title"),
            lang.tr("filaments.confirm_delete_text"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if rep == QMessageBox.Yes:
            db.delete_filament(fid)
            self._refresh()
            self.on_change_callback()


class PrintersTab(QWidget):
    """Gestion des imprimantes et de leur puissance moyenne par matière."""

    def __init__(self, on_change_callback):
        super().__init__()
        self.on_change_callback = on_change_callback
        self.COLUMNS = [
            ("matiere", lang.tr("printers.col_matiere")),
            ("conso_kw", lang.tr("printers.col_conso_kw")),
            ("watts", lang.tr("printers.col_watts")),
        ]
        layout = QVBoxLayout(self)

        select_row = QHBoxLayout()
        select_row.addWidget(QLabel(lang.tr("printers.select_label")))
        self.printer_combo = QComboBox()
        self.printer_combo.currentIndexChanged.connect(self._refresh_profiles)
        select_row.addWidget(self.printer_combo)
        btn_add_printer = QPushButton(lang.tr("printers.btn_add_printer"))
        btn_add_printer.clicked.connect(self._add_printer)
        btn_delete_printer = QPushButton(lang.tr("printers.btn_delete_printer"))
        btn_delete_printer.setObjectName("Danger")
        btn_delete_printer.clicked.connect(self._delete_printer)
        select_row.addWidget(btn_add_printer)
        select_row.addWidget(btn_delete_printer)
        layout.addLayout(select_row)

        actions = QHBoxLayout()
        btn_add_profile = QPushButton(lang.tr("printers.btn_add_profile"))
        btn_add_profile.clicked.connect(self._add_or_edit_profile)
        btn_edit_profile = QPushButton(lang.tr("printers.btn_edit_profile"))
        btn_edit_profile.setObjectName("Secondary")
        btn_edit_profile.clicked.connect(self._edit_selected_profile)
        btn_delete_profile = QPushButton(lang.tr("printers.btn_delete_profile"))
        btn_delete_profile.setObjectName("Danger")
        btn_delete_profile.clicked.connect(self._delete_selected_profile)
        actions.addWidget(btn_add_profile)
        actions.addWidget(btn_edit_profile)
        actions.addWidget(btn_delete_profile)
        actions.addStretch()
        layout.addLayout(actions)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([label for _, label in self.COLUMNS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(lambda _row, _col: self._edit_selected_profile())
        layout.addWidget(self.table)
        self._refresh_printers()

    def _refresh_printers(self):
        selected_id = self.printer_combo.currentData()
        self.printer_combo.blockSignals(True)
        self.printer_combo.clear()
        for printer in db.get_printers():
            self.printer_combo.addItem(printer.nom, printer.id)
        self.printer_combo.blockSignals(False)
        index = self.printer_combo.findData(selected_id)
        self.printer_combo.setCurrentIndex(index if index >= 0 else 0)
        self._refresh_profiles()

    def _refresh_profiles(self):
        printer_id = self.printer_combo.currentData()
        profiles = db.get_printer_material_profiles(printer_id) if printer_id is not None else []
        self.table.setRowCount(len(profiles))
        for row, (material, consumption_kw) in enumerate(profiles):
            for col, value in enumerate((material, consumption_kw, round(consumption_kw * 1000, 1))):
                item = QTableWidgetItem()
                item.setData(Qt.DisplayRole, value)
                item.setData(Qt.UserRole, material)
                self.table.setItem(row, col, item)

    def _notify_change(self):
        self.on_change_callback()
        self._refresh_printers()

    def _add_printer(self):
        dlg = PrinterDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        name = dlg.nom.text().strip()
        if not name:
            QMessageBox.warning(self, lang.tr("printers.missing_name_title"), lang.tr("printers.missing_name_text"))
            return
        try:
            db.add_printer(name)
        except Exception as error:
            QMessageBox.warning(self, lang.tr("printers.exists_title"), lang.tr("printers.exists_text", error=error))
            return
        self._notify_change()

    def _delete_printer(self):
        printer_id = self.printer_combo.currentData()
        if printer_id is None:
            return
        name = self.printer_combo.currentText()
        reply = QMessageBox.question(
            self, lang.tr("common.confirm_delete_title"),
            lang.tr("printers.confirm_delete_printer_text", name=name),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            db.delete_printer(printer_id)
            self._notify_change()

    def _selected_material(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.UserRole) if item else None

    def _add_or_edit_profile(self, material: str = "", consumption_kw: float = 0.0):
        printer_id = self.printer_combo.currentData()
        if printer_id is None:
            return
        dlg = ConsumptionDialog(material, consumption_kw, self)
        if dlg.exec() != QDialog.Accepted:
            return
        material = dlg.matiere.text().strip()
        if not material:
            QMessageBox.warning(self, lang.tr("printers.missing_material_title"), lang.tr("printers.missing_material_text"))
            return
        db.set_printer_consumption(printer_id, material, dlg.conso_kw.value())
        self._refresh_profiles()
        self.on_change_callback()

    def _edit_selected_profile(self):
        material = self._selected_material()
        printer_id = self.printer_combo.currentData()
        if material is None or printer_id is None:
            QMessageBox.information(self, lang.tr("common.no_selection_title"), lang.tr("printers.no_material_selected_text"))
            return
        consumption_kw = db.get_printer_consumption(printer_id, material) or 0.0
        self._add_or_edit_profile(material, consumption_kw)

    def _delete_selected_profile(self):
        material = self._selected_material()
        printer_id = self.printer_combo.currentData()
        if material is None or printer_id is None:
            QMessageBox.information(self, lang.tr("common.no_selection_title"), lang.tr("printers.no_material_selected_text"))
            return
        db.delete_printer_consumption(printer_id, material)
        self._refresh_profiles()
        self.on_change_callback()


class FilamentModulesTab(QWidget):
    def __init__(self, on_change_callback):
        super().__init__()
        self.on_change_callback = on_change_callback
        self.COLUMNS = [
            ("nom", lang.tr("modules.col_nom")),
            ("conso_kw", lang.tr("modules.col_conso_kw")),
            ("watts", lang.tr("modules.col_watts")),
        ]
        layout = QVBoxLayout(self)
        actions = QHBoxLayout()
        add_button = QPushButton(lang.tr("modules.btn_add"))
        add_button.clicked.connect(self._add_module)
        edit_button = QPushButton(lang.tr("modules.btn_edit"))
        edit_button.setObjectName("Secondary")
        edit_button.clicked.connect(self._edit_selected_module)
        delete_button = QPushButton(lang.tr("modules.btn_delete"))
        delete_button.setObjectName("Danger")
        delete_button.clicked.connect(self._delete_selected_module)
        actions.addWidget(add_button)
        actions.addWidget(edit_button)
        actions.addWidget(delete_button)
        actions.addStretch()
        layout.addLayout(actions)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([label for _, label in self.COLUMNS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(lambda _row, _col: self._edit_selected_module())
        layout.addWidget(self.table)
        self._refresh()

    def _refresh(self):
        modules = db.get_filament_modules()
        self.table.setRowCount(len(modules))
        for row, module in enumerate(modules):
            for col, value in enumerate((module.nom, module.conso_kw, round(module.conso_kw * 1000, 2))):
                item = QTableWidgetItem()
                item.setData(Qt.DisplayRole, value)
                item.setData(Qt.UserRole, module.id)
                self.table.setItem(row, col, item)

    def _selected_module(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        if item is None:
            return None
        module_id = item.data(Qt.UserRole)
        return next((module for module in db.get_filament_modules() if module.id == module_id), None)

    def _save_dialog(self, module=None):
        dlg = FilamentModuleDialog(
            module.nom if module else "", module.conso_kw if module else 0.0, self
        )
        if dlg.exec() != QDialog.Accepted:
            return
        name = dlg.nom.text().strip()
        if not name:
            QMessageBox.warning(self, lang.tr("modules.missing_name_title"), lang.tr("modules.missing_name_text"))
            return
        try:
            if module:
                db.update_filament_module(module.id, name, dlg.conso_kw.value())
            else:
                db.add_filament_module(name, dlg.conso_kw.value())
        except Exception as error:
            QMessageBox.warning(self, lang.tr("modules.exists_title"), lang.tr("modules.exists_text", error=error))
            return
        self._refresh()
        self.on_change_callback()

    def _add_module(self):
        self._save_dialog()

    def _edit_selected_module(self):
        module = self._selected_module()
        if module is None:
            QMessageBox.information(self, lang.tr("common.no_selection_title"), lang.tr("modules.no_module_selected_text"))
            return
        self._save_dialog(module)

    def _delete_selected_module(self):
        module = self._selected_module()
        if module is None:
            QMessageBox.information(self, lang.tr("common.no_selection_title"), lang.tr("modules.no_module_selected_text"))
            return
        reply = QMessageBox.question(
            self, lang.tr("common.confirm_delete_title"),
            lang.tr("modules.confirm_delete_text", name=module.nom),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            db.delete_filament_module(module.id)
            self._refresh()
            self.on_change_callback()


class PrintedObjectsTab(QWidget):
    COLUMNS = [
        ("nom", "objects.col_name"),
        ("date_creation", "objects.col_date"),
        ("mode", "objects.col_mode"),
        ("poids_total_g", "objects.col_weight"),
        ("temps_impression_h", "objects.col_print_time"),
        ("temps_finition_h", "objects.col_finish_time"),
        ("cout_total_ht", "objects.col_cost"),
        ("prix_conseille_ttc", "objects.col_price"),
        ("notes", "objects.col_notes"),
    ]

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([lang.tr(key) for _, key in self.COLUMNS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellDoubleClicked.connect(self._show_details)
        layout.addWidget(self.table)
        self._refresh()

    def _refresh(self):
        objects = db.get_printed_objects()
        self.table.setRowCount(len(objects))
        for row, item in enumerate(objects):
            values = {
                "nom": item["nom"],
                "date_creation": item.get("date_creation", ""),
                "mode": lang.tr("objects.mode_multi") if item.get("donnees", {}).get("mode_multicouleur")
                else lang.tr("objects.mode_single"),
                "poids_total_g": f"{item.get('poids_total_g', 0):.2f}",
                "temps_impression_h": f"{item.get('temps_impression_h', 0):.2f}",
                "temps_finition_h": f"{item.get('temps_finition_h', 0):.2f}",
                "cout_total_ht": f"{item.get('cout_total_ht', 0):.2f}",
                "prix_conseille_ttc": f"{item.get('prix_conseille_ttc', 0):.2f}",
                "notes": item.get("notes", ""),
            }
            for column, (key, _label) in enumerate(self.COLUMNS):
                cell = QTableWidgetItem(values[key])
                cell.setData(Qt.UserRole, item["id"])
                self.table.setItem(row, column, cell)

    def _show_details(self, row, _column):
        object_id = self.table.item(row, 0).data(Qt.UserRole)
        item = next((obj for obj in db.get_printed_objects() if obj["id"] == object_id), None)
        if item is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(item["nom"])
        dialog.resize(760, 650)
        outer_layout = QVBoxLayout(dialog)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        summary = QGroupBox(lang.tr("objects.detail_summary"))
        summary_form = QFormLayout(summary)
        summary_values = [
            (lang.tr("objects.col_name"), item.get("nom", "")),
            (lang.tr("objects.col_date"), item.get("date_creation", "")),
            (lang.tr("objects.col_mode"), self._mode_text(item)),
            (lang.tr("objects.col_weight"), self._number(item.get("poids_total_g"))),
            (lang.tr("objects.col_print_time"), self._number(item.get("temps_impression_h"))),
            (lang.tr("objects.col_finish_time"), self._number(item.get("temps_finition_h"))),
            (lang.tr("objects.col_cost"), self._money(item.get("cout_total_ht"))),
            (lang.tr("objects.col_price"), self._money(item.get("prix_conseille_ttc"))),
        ]
        for label, value in summary_values:
            summary_form.addRow(label, QLabel(value))
        layout.addWidget(summary)

        notes = QGroupBox(lang.tr("objects.col_notes"))
        notes_layout = QVBoxLayout(notes)
        notes_label = QLabel(item.get("notes") or "-")
        notes_label.setWordWrap(True)
        notes_layout.addWidget(notes_label)
        layout.addWidget(notes)

        parameters = QGroupBox(lang.tr("objects.detail_parameters"))
        parameters_form = QFormLayout(parameters)
        parameter_values = item.get("donnees", {})
        hidden_keys = {"composition", "mode_multicouleur"}
        for key, value in parameter_values.items():
            if key in hidden_keys:
                continue
            label = key.replace("_", " ").capitalize()
            parameters_form.addRow(label, QLabel(self._format_value(value)))
        layout.addWidget(parameters)

        composition = QGroupBox(lang.tr("objects.detail_composition"))
        composition_layout = QVBoxLayout(composition)
        composition_table = QTableWidget(0, 5)
        composition_table.setHorizontalHeaderLabels([
            lang.tr("calc.table_mat"), lang.tr("calc.table_couleur"),
            lang.tr("calc.table_poids"), lang.tr("filaments.col_cout_g"),
            lang.tr("objects.col_total"),
        ])
        composition_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        composition_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rows = item.get("composition", [])
        composition_table.setRowCount(len(rows))
        for row_index, component in enumerate(rows):
            values = [
                component.get("matiere", ""), component.get("couleur", ""),
                self._number(component.get("poids_g")), self._money(component.get("cout_g")),
                self._money(component.get("cout_total")),
            ]
            for column, value in enumerate(values):
                composition_table.setItem(row_index, column, QTableWidgetItem(value))
        composition_layout.addWidget(composition_table)
        layout.addWidget(composition)
        layout.addStretch()
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

        close_button = QPushButton(lang.tr("common.close"))
        close_button.clicked.connect(dialog.accept)
        outer_layout.addWidget(close_button)
        dialog.exec()

    @staticmethod
    def _number(value) -> str:
        return f"{float(value or 0):.2f}"

    @staticmethod
    def _money(value) -> str:
        currency = db.get_parametres().get("devise", "EUR")
        return f"{float(value or 0):.2f} {currency}"

    @staticmethod
    def _format_value(value) -> str:
        if isinstance(value, bool):
            return "Oui" if value else "Non"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    @staticmethod
    def _mode_text(item) -> str:
        return lang.tr("objects.mode_multi") if item.get("donnees", {}).get("mode_multicouleur") \
            else lang.tr("objects.mode_single")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(lang.tr("app.title"))
        self.resize(1050, 680)

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        banner_row = QHBoxLayout()
        banner = QLabel(lang.tr("app.banner"))
        banner.setObjectName("AppBanner")
        banner_row.addWidget(banner)
        banner_row.addStretch()
        banner_row.addWidget(QLabel(lang.tr("app.lang_label")))
        self.lang_combo = QComboBox()
        for code in lang.available_languages():
            self.lang_combo.addItem(code.upper(), code)
        current_index = self.lang_combo.findData(lang.current_language())
        self.lang_combo.setCurrentIndex(current_index if current_index >= 0 else 0)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        banner_row.addWidget(self.lang_combo)
        outer.addLayout(banner_row)

        banner_sub = QLabel(lang.tr("app.banner_sub"))
        banner_sub.setObjectName("AppBannerSub")
        outer.addWidget(banner_sub)

        tabs = QTabWidget()
        parameters_tab = QWidget()
        self.objects_tab = PrintedObjectsTab()
        self.calc_tab = CalculatorTab(parameters_tab, on_object_saved=self.objects_tab._refresh)
        self.fil_tab = FilamentsTab(on_change_callback=self.calc_tab._refresh_filaments)
        self.printer_tab = PrintersTab(on_change_callback=self.calc_tab._refresh_printers)
        self.module_tab = FilamentModulesTab(on_change_callback=self.calc_tab._refresh_filament_modules)
        tabs.addTab(self.calc_tab, lang.tr("app.tab_calculator"))
        tabs.addTab(self.objects_tab, lang.tr("app.tab_objects"))
        tabs.addTab(parameters_tab, lang.tr("app.tab_parameters"))
        tabs.addTab(self.fil_tab, lang.tr("app.tab_filaments"))
        tabs.addTab(self.printer_tab, lang.tr("app.tab_printers"))
        tabs.addTab(self.module_tab, lang.tr("app.tab_modules"))
        QTimer.singleShot(0, self.calc_tab._post_init)
        outer.addWidget(tabs)
        self.setCentralWidget(central)

    # Maintenant que CalculatorTab est attaché → on peut initialiser

    def _on_language_changed(self):
        code = self.lang_combo.currentData()
        if code and code != lang.current_language():
            lang.load_language(code)
            db.set_parametre("langue", code)
            QMessageBox.information(
                self, lang.tr("app.title"),
                "Redémarrez l'application pour appliquer la nouvelle langue.\n"
                "Restart the application to apply the new language."
            )


def main():
    db.init_db()
    saved_lang = db.get_parametres().get("langue", "fr")
    lang.load_language(saved_lang)
    app = QApplication(sys.argv)
    load_application_fonts()
    app.setStyleSheet(theme.MODERN_QSS)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()