"""
Système de langue : un fichier JSON par langue, chargé une fois au démarrage.
Toute l'interface passe par tr("cle") pour afficher son texte.

Auto-réparation : si le dossier lang/ ou ses fichiers .json sont absents
(première installation, dossier supprimé par erreur...), ils sont recréés
automatiquement à partir des dictionnaires FALLBACK_FR/FALLBACK_EN intégrés
ci-dessous — l'appli ne dépend donc jamais de fichiers externes pour démarrer.

Ajouter une langue = copier lang/fr.json vers lang/xx.json et traduire les
valeurs (les clés à gauche ne changent jamais, elles servent de repère interne).
"""
import json
import os
import sys
from pathlib import Path

DEFAULT_LANG = "fr"


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _user_data_dir() -> Path:
    """Même logique que database.py : à côté de l'exe si possible, sinon AppData.
    Les deux modules doivent pointer vers le même dossier utilisateur."""
    if not _is_frozen():
        return Path(__file__).parent

    exe_dir = Path(sys.executable).resolve().parent
    try:
        probe = exe_dir / ".calculateur3d_write_test"
        probe.touch(exist_ok=False)
        probe.unlink()
        return exe_dir
    except OSError:
        local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        data_dir = local_app_data / "Calculateur3D"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir


LANG_DIR = _user_data_dir() / "lang"

_strings: dict[str, str] = {}
_fallback: dict[str, str] = {}
_current_lang = DEFAULT_LANG


FALLBACK_FR = {
    'app.banner': '🖨  Calculateur de prix — Impression 3D',
    'app.banner_sub': "Matière, temps machine, main d'oeuvre, marge — un prix juste, calculé automatiquement.",
    'app.lang_label': 'Langue :',
    'app.tab_calculator': 'Calculateur',
    'app.tab_filaments': 'Filaments',
    'app.tab_modules': 'Modules filament',
    'app.tab_parameters': 'Paramètres',
    'app.tab_objects': 'Objets',
    'app.tab_printers': 'Imprimantes',
    'app.title': 'Calculateur de prix — Impression 3D',
    'calc.btn_save_params': 'Enregistrer ces taux comme défaut',
    'calc.btn_save_object': 'Ajouter objet',
    'dialog.object.title': 'Ajouter un objet',
    'dialog.object.label_name': "Nom de l'objet",
    'dialog.object.label_notes': 'Notes',
    'dialog.object.placeholder_name': 'ex : Boîtier électronique',
    'dialog.object.placeholder_notes': 'Ajoutez une note ou plusieurs informations...',
    'dialog.object.missing_name_title': 'Nom manquant',
    'dialog.object.missing_name_text': "Saisissez le nom de l'objet.",
    'dialog.object.saved_title': 'Objet enregistré',
    'dialog.object.saved_text': 'L’objet « {name} » a été enregistré.',
    'calc.conso_default': 'Consommation par défaut',
    'calc.conso_default_no_profile': 'Consommation par défaut (profil matière indisponible)',
    'calc.conso_profile': 'Profil {printer} · {material}: {watts} W',
    'calc.duration_days': 'jour(s)',
    'calc.duration_hours': 'heure(s)',
    'calc.duration_minutes': 'min',
    'calc.group_charges': 'Charges et marge',
    'calc.group_couts': 'Coûts et taux',
    'calc.group_detail': 'Détail des coûts',
    'calc.group_fourchette': 'Fourchette de prix conseillé',
    'calc.group_object': 'Objet à imprimer',
    'calc.group_prix': 'Prix conseillé',
    'calc.label_charges_pct': 'Charges sociales (%)',
    'calc.label_conso_imprimante': 'Consommation imprimante (kW)',
    'calc.label_couleur': 'Couleur',
    'calc.label_divers': 'Frais divers (forfait)',
    'calc.label_emballage': 'Emballage (forfait)',
    'calc.label_imprimante': 'Imprimante',
    'calc.label_marge_pct': 'Marge cible (%)',
    'calc.label_matiere': 'Matière',
    'calc.label_module_filament': 'Module filament',
    'calc.label_poids': 'Poids (g)',
    'calc.label_prix_bas': 'Bas (coût réel payé)',
    'calc.label_prix_haut': 'Haut (prix catalogue, sans remise)',
    'calc.label_prix_ht': 'Prix HT',
    'calc.label_prix_kwh': 'Prix électricité (/kWh)',
    'calc.label_prix_ttc': 'Prix TTC',
    'calc.label_taux_machine': 'Taux machine (/h)',
    'calc.label_taux_main_oeuvre': "Taux main d'oeuvre (/h)",
    'calc.label_temps_finition': 'Temps de finition',
    'calc.label_temps_impression': "Temps d'impression",
    'calc.label_tva_pct': 'TVA (%, 0 = désactivée)',
    'calc.msg_saved_text': 'Ces taux sont maintenant vos valeurs par défaut.',
    'calc.msg_saved_title': 'Enregistré',
    'calc.no_filament': '(aucun filament — onglet Filaments)',
    'calc.no_filament_module': 'Aucun module',
    'calc.placeholder_poids': 'ex: 25.4',
    'calc.row_charges': 'Charges sociales',
    'calc.row_divers': '▢  Frais divers',
    'calc.row_electrique': 'ϟ  Électricité (total)',
    'calc.row_emballage': '▢  Emballage',
    'calc.row_finition': '◌  Finition',
    'calc.row_machine': '◉  Machine',
    'calc.row_matiere': '◈  Matière',
    'calc.row_module_filament': '    dont module filament',
    'calc.row_prix_plancher': 'Prix plancher HT',
    'calc.row_total': 'Total des coûts',
    'common.confirm_delete_title': 'Confirmer la suppression',
    'common.error_title': 'Erreur',
    'common.no_selection_filament': "Sélectionnez d'abord une ligne dans le tableau.",
    'common.no_selection_title': 'Aucune sélection',
    'common.read_error_text': 'Impossible de lire le fichier :\n{error}',
    'common.write_error_text': "Impossible d'écrire le fichier :\n{error}",
    'dialog.conso.label_matiere': 'Matière',
    'dialog.conso.label_puissance': 'Puissance moyenne (kW)',
    'dialog.conso.placeholder_matiere': 'ex : PLA, PETG, ABS',
    'dialog.conso.title': 'Consommation par matière',
    'dialog.filament.label_couleur': 'Couleur',
    'dialog.filament.label_fournisseur': 'Fournisseur',
    'dialog.filament.label_matiere': 'Matière (PLA, PETG...)',
    'dialog.filament.label_poids_bobine': 'Poids de la bobine (g)',
    'dialog.filament.label_prix_catalogue': 'Prix catalogue (sans remise)',
    'dialog.filament.label_prix_reel': 'Prix réel payé (avec remise)',
    'dialog.filament.placeholder_catalogue': 'optionnel, laisser vide si inconnu',
    'dialog.filament.title': 'Ajouter un filament',
    'dialog.module.label_nom': 'Nom du module',
    'dialog.module.label_puissance': 'Puissance moyenne (kW)',
    'dialog.module.placeholder_nom': 'ex : AMS, MMU, CFS',
    'dialog.module.title': "Module d'alimentation filament",
    'dialog.printer.label_nom': "Nom de l'imprimante",
    'dialog.printer.placeholder_nom': 'ex : Bambu Lab P1P',
    'dialog.printer.title': 'Ajouter une imprimante',
    'filaments.btn_add': 'Ajouter un filament',
    'filaments.btn_delete': 'Supprimer la sélection',
    'filaments.btn_export': 'Exporter en CSV',
    'filaments.btn_import': 'Importer depuis CSV',
    'filaments.col_couleur': 'Couleur',
    'filaments.col_cout_g': 'Coût/g',
    'filaments.col_fournisseur': 'Fournisseur',
    'filaments.col_matiere': 'Matière',
    'filaments.col_poids_bobine': 'Poids bobine (g)',
    'filaments.col_prix_catalogue': 'Prix catalogue',
    'filaments.col_prix_reel': 'Prix réel',
    'filaments.confirm_delete_text': 'Supprimer ce filament ? Cette action est irréversible.',
    'filaments.export_dialog_title': 'Exporter les filaments',
    'filaments.export_done_text': '{n} filament(s) exporté(s) vers :\n{path}',
    'filaments.export_done_title': 'Export terminé',
    'filaments.filter_label': 'Filtrer :',
    'filaments.filter_placeholder': 'Tapez pour filtrer (matière, couleur, fournisseur...)',
    'filaments.import_dialog_title': 'Importer des filaments',
    'filaments.import_done_text': 'Ajoutés : {added}\nMis à jour : {updated}',
    'filaments.import_done_title': 'Import terminé',
    'filaments.import_ignored_lines': '\n\nLignes ignorées :\n',
    'filaments.import_more_errors': '... et {n} autre(s)',
    'filaments.missing_fields_text': 'Renseignez au moins la matière ou la couleur.',
    'filaments.missing_fields_title': 'Champs manquants',
    'modules.btn_add': 'Ajouter un module',
    'modules.btn_delete': 'Supprimer la sélection',
    'modules.btn_edit': 'Modifier la sélection',
    'modules.col_conso_kw': 'Consommation (kW)',
    'modules.col_nom': 'Module',
    'modules.col_watts': 'Puissance (W)',
    'modules.confirm_delete_text': 'Supprimer le module « {name} » ?',
    'modules.exists_text': "Impossible d'enregistrer ce module :\n{error}",
    'modules.exists_title': 'Module existant',
    'modules.missing_name_text': 'Saisissez le nom du module.',
    'modules.missing_name_title': 'Nom manquant',
    'modules.no_module_selected_text': "Sélectionnez d'abord un module.",
    'printers.btn_add_printer': 'Ajouter une imprimante',
    'printers.btn_add_profile': 'Ajouter une matière',
    'printers.btn_delete_printer': "Supprimer l'imprimante",
    'printers.btn_delete_profile': 'Supprimer la sélection',
    'printers.btn_edit_profile': 'Modifier la sélection',
    'printers.col_conso_kw': 'Consommation (kW)',
    'printers.col_matiere': 'Matière',
    'printers.col_watts': 'Puissance (W)',
    'printers.confirm_delete_printer_text': "Supprimer l'imprimante « {name} » et ses profils matière ?",
    'printers.exists_text': "Impossible d'ajouter cette imprimante :\n{error}",
    'printers.exists_title': 'Imprimante existante',
    'printers.missing_material_text': 'Saisissez une matière.',
    'printers.missing_material_title': 'Matière manquante',
    'printers.missing_name_text': "Saisissez le nom de l'imprimante.",
    'printers.missing_name_title': 'Nom manquant',
    'printers.no_material_selected_text': "Sélectionnez d'abord une matière.",
    'printers.select_label': 'Imprimante :',
    'objects.col_name': 'Nom',
    'objects.col_date': 'Date',
    'objects.col_mode': 'Mode',
    'objects.col_weight': 'Poids (g)',
    'objects.col_print_time': "Temps d'impression (h)",
    'objects.col_finish_time': 'Temps de finition (h)',
    'objects.col_cost': 'Coût HT',
    'objects.col_price': 'Prix TTC',
    'objects.col_notes': 'Notes',
    'objects.col_total': 'Total',
    'objects.mode_single': 'Mono',
    'objects.mode_multi': 'Multicouleur',
    'objects.detail_summary': 'Résumé',
    'objects.detail_parameters': 'Paramètres enregistrés',
    'objects.detail_composition': 'Composition',
    'common.close': 'Fermer',
}


FALLBACK_EN = {
    'app.banner': '🖨  3D Printing Price Calculator',
    'app.banner_sub': 'Material, machine time, labor, margin — a fair price, calculated automatically.',
    'app.lang_label': 'Language:',
    'app.tab_calculator': 'Calculator',
    'app.tab_filaments': 'Filaments',
    'app.tab_modules': 'Filament modules',
    'app.tab_parameters': 'Settings',
    'app.tab_objects': 'Objects',
    'app.tab_printers': 'Printers',
    'app.title': '3D Printing Price Calculator',
    'calc.btn_save_params': 'Save these rates as default',
    'calc.btn_save_object': 'Add object',
    'dialog.object.title': 'Add an object',
    'dialog.object.label_name': 'Object name',
    'dialog.object.label_notes': 'Notes',
    'dialog.object.placeholder_name': 'e.g. Electronic enclosure',
    'dialog.object.placeholder_notes': 'Add one or more notes...',
    'dialog.object.missing_name_title': 'Missing name',
    'dialog.object.missing_name_text': 'Enter the object name.',
    'dialog.object.saved_title': 'Object saved',
    'dialog.object.saved_text': 'The object "{name}" was saved.',
    'calc.conso_default': 'Default consumption',
    'calc.conso_default_no_profile': 'Default consumption (no material profile available)',
    'calc.conso_profile': 'Profile {printer} · {material}: {watts} W',
    'calc.duration_days': 'day(s)',
    'calc.duration_hours': 'hour(s)',
    'calc.duration_minutes': 'min',
    'calc.group_charges': 'Charges and margin',
    'calc.group_couts': 'Costs and rates',
    'calc.group_detail': 'Cost breakdown',
    'calc.group_fourchette': 'Suggested price range',
    'calc.group_object': 'Object to print',
    'calc.group_prix': 'Suggested price',
    'calc.label_charges_pct': 'Social charges (%)',
    'calc.label_conso_imprimante': 'Printer consumption (kW)',
    'calc.label_couleur': 'Color',
    'calc.label_divers': 'Misc costs (flat fee)',
    'calc.label_emballage': 'Packaging (flat fee)',
    'calc.label_imprimante': 'Printer',
    'calc.label_marge_pct': 'Target margin (%)',
    'calc.label_matiere': 'Material',
    'calc.label_module_filament': 'Filament module',
    'calc.label_poids': 'Weight (g)',
    'calc.label_prix_bas': 'Low (real cost paid)',
    'calc.label_prix_haut': 'High (list price, no discount)',
    'calc.label_prix_ht': 'Price (pre-tax)',
    'calc.label_prix_kwh': 'Electricity price (/kWh)',
    'calc.label_prix_ttc': 'Price (incl. tax)',
    'calc.label_taux_machine': 'Machine rate (/h)',
    'calc.label_taux_main_oeuvre': 'Labor rate (/h)',
    'calc.label_temps_finition': 'Finishing time',
    'calc.label_temps_impression': 'Print time',
    'calc.label_tva_pct': 'Tax (%, 0 = disabled)',
    'calc.msg_saved_text': 'These rates are now your default values.',
    'calc.msg_saved_title': 'Saved',
    'calc.no_filament': '(no filament — see Filaments tab)',
    'calc.no_filament_module': 'No module',
    'calc.placeholder_poids': 'e.g. 25.4',
    'calc.row_charges': 'Social charges',
    'calc.row_divers': '▢  Misc costs',
    'calc.row_electrique': 'ϟ  Electricity (total)',
    'calc.row_emballage': '▢  Packaging',
    'calc.row_finition': '◌  Finishing',
    'calc.row_machine': '◉  Machine',
    'calc.row_matiere': '◈  Material',
    'calc.row_module_filament': '    incl. filament module',
    'calc.row_prix_plancher': 'Floor price (pre-tax)',
    'calc.row_total': 'Total costs',
    'common.confirm_delete_title': 'Confirm deletion',
    'common.error_title': 'Error',
    'common.no_selection_filament': 'Select a row in the table first.',
    'common.no_selection_title': 'No selection',
    'common.read_error_text': 'Could not read the file:\n{error}',
    'common.write_error_text': 'Could not write the file:\n{error}',
    'dialog.conso.label_matiere': 'Material',
    'dialog.conso.label_puissance': 'Average power (kW)',
    'dialog.conso.placeholder_matiere': 'e.g. PLA, PETG, ABS',
    'dialog.conso.title': 'Consumption per material',
    'dialog.filament.label_couleur': 'Color',
    'dialog.filament.label_fournisseur': 'Supplier',
    'dialog.filament.label_matiere': 'Material (PLA, PETG...)',
    'dialog.filament.label_poids_bobine': 'Spool weight (g)',
    'dialog.filament.label_prix_catalogue': 'List price (no discount)',
    'dialog.filament.label_prix_reel': 'Real price paid (with discount)',
    'dialog.filament.placeholder_catalogue': 'optional, leave blank if unknown',
    'dialog.filament.title': 'Add a filament',
    'dialog.module.label_nom': 'Module name',
    'dialog.module.label_puissance': 'Average power (kW)',
    'dialog.module.placeholder_nom': 'e.g. AMS, MMU, CFS',
    'dialog.module.title': 'Filament feed module',
    'dialog.printer.label_nom': 'Printer name',
    'dialog.printer.placeholder_nom': 'e.g. Bambu Lab P1P',
    'dialog.printer.title': 'Add a printer',
    'filaments.btn_add': 'Add a filament',
    'filaments.btn_delete': 'Delete selection',
    'filaments.btn_export': 'Export to CSV',
    'filaments.btn_import': 'Import from CSV',
    'filaments.col_couleur': 'Color',
    'filaments.col_cout_g': 'Cost/g',
    'filaments.col_fournisseur': 'Supplier',
    'filaments.col_matiere': 'Material',
    'filaments.col_poids_bobine': 'Spool weight (g)',
    'filaments.col_prix_catalogue': 'List price',
    'filaments.col_prix_reel': 'Real price',
    'filaments.confirm_delete_text': 'Delete this filament? This action cannot be undone.',
    'filaments.export_dialog_title': 'Export filaments',
    'filaments.export_done_text': '{n} filament(s) exported to:\n{path}',
    'filaments.export_done_title': 'Export complete',
    'filaments.filter_label': 'Filter:',
    'filaments.filter_placeholder': 'Type to filter (material, color, supplier...)',
    'filaments.import_dialog_title': 'Import filaments',
    'filaments.import_done_text': 'Added: {added}\nUpdated: {updated}',
    'filaments.import_done_title': 'Import complete',
    'filaments.import_ignored_lines': '\n\nIgnored lines:\n',
    'filaments.import_more_errors': '... and {n} more',
    'filaments.missing_fields_text': 'Enter at least the material or the color.',
    'filaments.missing_fields_title': 'Missing fields',
    'modules.btn_add': 'Add a module',
    'modules.btn_delete': 'Delete selection',
    'modules.btn_edit': 'Edit selection',
    'modules.col_conso_kw': 'Consumption (kW)',
    'modules.col_nom': 'Module',
    'modules.col_watts': 'Power (W)',
    'modules.confirm_delete_text': 'Delete module "{name}"?',
    'modules.exists_text': 'Could not save this module:\n{error}',
    'modules.exists_title': 'Module already exists',
    'modules.missing_name_text': 'Enter the module name.',
    'modules.missing_name_title': 'Missing name',
    'modules.no_module_selected_text': 'Select a module first.',
    'printers.btn_add_printer': 'Add a printer',
    'printers.btn_add_profile': 'Add a material',
    'printers.btn_delete_printer': 'Delete printer',
    'printers.btn_delete_profile': 'Delete selection',
    'printers.btn_edit_profile': 'Edit selection',
    'printers.col_conso_kw': 'Consumption (kW)',
    'printers.col_matiere': 'Material',
    'printers.col_watts': 'Power (W)',
    'printers.confirm_delete_printer_text': 'Delete printer "{name}" and its material profiles?',
    'printers.exists_text': 'Could not add this printer:\n{error}',
    'printers.exists_title': 'Printer already exists',
    'printers.missing_material_text': 'Enter a material.',
    'printers.missing_material_title': 'Missing material',
    'printers.missing_name_text': 'Enter the printer name.',
    'printers.missing_name_title': 'Missing name',
    'printers.no_material_selected_text': 'Select a material first.',
    'printers.select_label': 'Printer:',
    'objects.col_name': 'Name',
    'objects.col_date': 'Date',
    'objects.col_mode': 'Mode',
    'objects.col_weight': 'Weight (g)',
    'objects.col_print_time': 'Print time (h)',
    'objects.col_finish_time': 'Finishing time (h)',
    'objects.col_cost': 'Cost (pre-tax)',
    'objects.col_price': 'Price (incl. tax)',
    'objects.col_notes': 'Notes',
    'objects.col_total': 'Total',
    'objects.mode_single': 'Single',
    'objects.mode_multi': 'Multicolor',
    'objects.detail_summary': 'Summary',
    'objects.detail_parameters': 'Saved parameters',
    'objects.detail_composition': 'Composition',
    'common.close': 'Close',
}


FALLBACKS_BY_LANG = {
    "fr": FALLBACK_FR,
    "en": FALLBACK_EN,
}


def ensure_lang_files() -> None:
    """Crée lang/ et ses fichiers .json s'ils sont absents, à partir des
    dictionnaires intégrés au code. Appelée automatiquement par load_language(),
    jamais besoin de l'appeler à la main."""
    LANG_DIR.mkdir(parents=True, exist_ok=True)
    for code, strings in FALLBACKS_BY_LANG.items():
        path = LANG_DIR / f"{code}.json"
        if not path.exists():
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(strings, f, ensure_ascii=False, indent=2)
            except OSError:
                pass  # Dossier non inscriptible : tant pis, le fallback en mémoire suffit


def available_languages() -> list[str]:
    """Liste les langues disponibles à partir des fichiers présents dans lang/."""
    ensure_lang_files()
    codes = sorted(p.stem for p in LANG_DIR.glob("*.json"))
    return codes or list(FALLBACKS_BY_LANG.keys())


def load_language(lang_code: str) -> None:
    """Charge le fichier de langue demandé. Recrée les fichiers manquants,
    puis retombe sur le dictionnaire intégré si la lecture échoue malgré
    tout — l'appli ne doit jamais planter ni rester sans texte."""
    global _strings, _fallback, _current_lang

    ensure_lang_files()

    _fallback = dict(FALLBACKS_BY_LANG.get(DEFAULT_LANG, FALLBACK_FR))
    fallback_path = LANG_DIR / f"{DEFAULT_LANG}.json"
    if fallback_path.exists():
        try:
            _fallback = json.loads(fallback_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass  # Garde le fallback intégré

    path = LANG_DIR / f"{lang_code}.json"
    try:
        _strings = json.loads(path.read_text(encoding="utf-8"))
        _current_lang = lang_code
    except (json.JSONDecodeError, OSError):
        _strings = dict(FALLBACKS_BY_LANG.get(lang_code, _fallback))
        _current_lang = lang_code if lang_code in FALLBACKS_BY_LANG else DEFAULT_LANG


def current_language() -> str:
    return _current_lang


def tr(key: str, **kwargs) -> str:
    """Retourne le texte associé à la clé dans la langue active.

    Si la clé manque dans la langue active, retombe sur le français.
    Si elle manque partout, affiche la clé elle-même entre crochets
    (visible mais pas de plantage — un signal clair qu'il manque une traduction).
    """
    text = _strings.get(key) or _fallback.get(key) or f"[{key}]"
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


# Chargement initial avec la langue par défaut, au cas où load_language()
# explicite n'est pas encore appelée par le point d'entrée de l'appli.
load_language(DEFAULT_LANG)