"""
Couche de persistance SQLite : paramètres, filaments et imprimantes.
L'exécutable embarque une base modèle et crée une copie externe modifiable.
"""
import sqlite3
import json
import os
import shutil
import sys
from pathlib import Path
from dataclasses import dataclass, field

APP_FOLDER_NAME = "Calculateur3D"
USER_DB_FILENAME = "print3d_calc.db"
SEED_DB_FILENAME = "default_print3d_calc.db"


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _resource_dir() -> Path:
    """Dossier des fichiers embarqués par PyInstaller, ou celui des sources."""
    if _is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent


def _user_data_dir() -> Path:
    """Choisit un dossier utilisateur : à côté de l'exe si possible, sinon AppData."""
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
        data_dir = local_app_data / APP_FOLDER_NAME
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir


SEED_DB_PATH = _resource_dir() / SEED_DB_FILENAME
DB_PATH = _user_data_dir() / USER_DB_FILENAME


def ensure_user_database() -> None:
    """Crée une copie externe de la base modèle uniquement au premier lancement."""
    if DB_PATH.exists():
        return
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SEED_DB_PATH.exists():
        shutil.copy2(SEED_DB_PATH, DB_PATH)

DEFAULT_PARAMS = {
    "devise": "EUR",
	"langue": "fr",			   
    "taux_machine_h": "0.30",
    "conso_kw": "0.12",
    "prix_kwh": "0.22",
    "taux_main_oeuvre_h": "15.00",
    "taux_charges_pct": "0.0",
    "emballage": "0.20",
    "divers": "0.0",
    "marge_cible_pct": "30.0",
    "tva_pct": "0.0",
}

# Puissances moyennes issues de la capture fournie pour la série Bambu Lab P1.
# Elles sont stockées en kW, l'unité attendue par le moteur de calcul.
DEFAULT_PRINTER_PROFILES = {
    "Bambu Lab P1P": {"PLA": 0.110, "ABS": 0.170, "PC": 0.160},
    "Bambu Lab P1S": {"PLA": 0.105, "ABS": 0.140, "PC": 0.135},
    "Bambu Lab P2S": {"PLA": 0.200},
    "Bambu Lab X1 / X1C": {"PLA": 0.105, "ABS": 0.150, "PC": 0.135},
    "Bambu Lab X1E": {"PLA": 0.185, "ABS": 0.260, "PC": 0.230},
    "Bambu Lab X2D": {"PLA": 0.250, "PC": 0.550},
    "Bambu Lab H2S": {"PLA": 0.200, "PETG": 0.180, "PC": 0.330},
    "Bambu Lab H2D": {"PLA": 0.197, "PETG": 0.150, "PC": 0.395},
    "Bambu Lab H2C": {"PLA": 0.200, "PETG": 0.193, "PC": 0.294},
    "Bambu Lab A2L": {"PLA": 0.145},
    "Bambu Lab A1": {"PLA": 0.095, "ABS": 0.200, "PC": 0.150},
    "Bambu Lab A1 mini": {"PLA": 0.080, "PETG": 0.075},
}

# Puissances en fonctionnement normal. Les cycles de séchage, très ponctuels,
# restent volontairement hors du coût d'une impression standard.
DEFAULT_FILAMENT_MODULES = {
    "Bambu Lab AMS": 0.00578,
    "Bambu Lab AMS lite": 0.00369,
    "Bambu Lab AMS 2 Pro": 0.012,
    "Bambu Lab AMS HT": 0.012,
}


def get_connection() -> sqlite3.Connection:
    ensure_user_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS parametres (
            cle TEXT PRIMARY KEY,
            valeur TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS filaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matiere TEXT,
            couleur TEXT,
            fournisseur TEXT,
            prix_bobine REAL NOT NULL,
            prix_bobine_catalogue REAL,
            poids_bobine_g REAL NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS imprimantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS consommations_imprimante (
            imprimante_id INTEGER NOT NULL,
            matiere TEXT NOT NULL,
            conso_kw REAL NOT NULL CHECK(conso_kw >= 0),
            PRIMARY KEY (imprimante_id, matiere),
            FOREIGN KEY (imprimante_id) REFERENCES imprimantes(id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS modules_filament (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            conso_kw REAL NOT NULL CHECK(conso_kw >= 0)
        )
    """)
    conn.commit()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS objets_imprimes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    date_creation TEXT DEFAULT (datetime('now')),
    statut TEXT DEFAULT 'termine', -- en_cours | termine | annule
    imprimante_id INTEGER,
    module_filament_id INTEGER,
    
    -- Métriques calculées (pour reporting rapide)
    poids_total_g REAL DEFAULT 0,
    temps_impression_h REAL DEFAULT 0,
    temps_finition_h REAL DEFAULT 0,
    
    -- Coûts & prix (stockés figés au moment du calcul)
    cout_filament_base REAL DEFAULT 0,
    cout_machine REAL DEFAULT 0,
    cout_electrique REAL DEFAULT 0,
    cout_emballage REAL DEFAULT 0,
    cout_divers REAL DEFAULT 0,
    cout_fournitures REAL DEFAULT 0,
    cout_main_oeuvre REAL DEFAULT 0,
    cout_total_ht REAL DEFAULT 0,
    prix_plancher_ht REAL DEFAULT 0,
    prix_conseille_ht REAL DEFAULT 0,
    prix_conseille_ttc REAL DEFAULT 0,
    
    notes TEXT,
    donnees_json TEXT,
    FOREIGN KEY(imprimante_id) REFERENCES imprimantes(id),
    FOREIGN KEY(module_filament_id) REFERENCES modules_filament(id)
);
    """)
    conn.commit()
    object_columns = [row["name"] for row in cur.execute("PRAGMA table_info(objets_imprimes)").fetchall()]
    if "donnees_json" not in object_columns:
        cur.execute("ALTER TABLE objets_imprimes ADD COLUMN donnees_json TEXT")
        conn.commit()
    if "cout_fournitures" not in object_columns:
        cur.execute("ALTER TABLE objets_imprimes ADD COLUMN cout_fournitures REAL DEFAULT 0")
        conn.commit()
    cur.execute("""
    -- Composition multicolore (1:N)
CREATE TABLE IF NOT EXISTS compositions_objet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objet_id INTEGER NOT NULL,
    matiere TEXT NOT NULL,
    couleur TEXT NOT NULL,
    poids_g REAL NOT NULL,
    cout_g REAL,
    cout_total REAL,
    FOREIGN KEY(objet_id) REFERENCES objets_imprimes(id) ON DELETE CASCADE
);
    """)
    conn.commit()

    # Migration : ajoute fournisseur / prix_bobine_catalogue si absents, retire nom si encore présent
    cols = [row["name"] for row in cur.execute("PRAGMA table_info(filaments)").fetchall()]
    if "fournisseur" not in cols:
        cur.execute("ALTER TABLE filaments ADD COLUMN fournisseur TEXT")
        conn.commit()
    if "prix_bobine_catalogue" not in cols:
        cur.execute("ALTER TABLE filaments ADD COLUMN prix_bobine_catalogue REAL")
        conn.commit()
    if "nom" in cols:
        try:
            cur.execute("ALTER TABLE filaments DROP COLUMN nom")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Ancienne version de SQLite sans DROP COLUMN : la colonne reste, inoffensive, plus utilisée

    # Insère les valeurs par défaut si la table paramètres est vide
    cur.execute("SELECT COUNT(*) FROM parametres")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO parametres (cle, valeur) VALUES (?, ?)",
            list(DEFAULT_PARAMS.items()),
        )
        conn.commit()

    # Profils de départ : INSERT OR IGNORE préserve toute valeur déjà modifiée.
    for printer_name, profiles in DEFAULT_PRINTER_PROFILES.items():
        cur.execute("INSERT OR IGNORE INTO imprimantes (nom) VALUES (?)", (printer_name,))
        printer_id = cur.execute(
            "SELECT id FROM imprimantes WHERE nom = ?", (printer_name,)
        ).fetchone()[0]
        for material, consumption_kw in profiles.items():
            cur.execute(
                "INSERT OR IGNORE INTO consommations_imprimante "
                "(imprimante_id, matiere, conso_kw) VALUES (?, ?, ?)",
                (printer_id, material, consumption_kw),
            )
    conn.commit()
    for module_name, consumption_kw in DEFAULT_FILAMENT_MODULES.items():
        cur.execute(
            "INSERT OR IGNORE INTO modules_filament (nom, conso_kw) VALUES (?, ?)",
            (module_name, consumption_kw),
        )
    conn.commit()
    conn.close()


def get_parametres() -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT cle, valeur FROM parametres").fetchall()
    conn.close()
    return {row["cle"]: row["valeur"] for row in rows}


def set_parametre(cle: str, valeur: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO parametres (cle, valeur) VALUES (?, ?) "
        "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
        (cle, valeur),
    )
    conn.commit()
    conn.close()


def add_printed_object(name: str, notes: str, data: dict) -> int:
    """Save a complete calculator snapshot and its multicolor composition."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO objets_imprimes (
                nom, imprimante_id, module_filament_id, poids_total_g,
                temps_impression_h, temps_finition_h, cout_filament_base,
                cout_machine, cout_electrique, cout_emballage, cout_divers, cout_fournitures,
                cout_main_oeuvre, cout_total_ht, prix_plancher_ht,
                prix_conseille_ht, prix_conseille_ttc, notes, donnees_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name.strip(), data.get("imprimante_id"), data.get("module_filament_id"),
                data.get("poids_total_g", 0.0), data.get("temps_impression_h", 0.0),
                data.get("temps_finition_h", 0.0), data.get("cout_matiere", 0.0),
                data.get("cout_machine", 0.0), data.get("cout_electrique", 0.0),
                data.get("cout_emballage", 0.0), data.get("cout_divers", 0.0),
                data.get("cout_fournitures", 0.0),
                data.get("montant_main_oeuvre", 0.0), data.get("cout_base", 0.0),
                data.get("prix_ht_plancher", 0.0), data.get("prix_conseille_ht", 0.0),
                data.get("prix_conseille_ttc", 0.0), notes.strip(), json.dumps(data, ensure_ascii=False),
            ),
        )
        object_id = cursor.lastrowid
        for component in data.get("composition", []):
            conn.execute(
                """INSERT INTO compositions_objet
                (objet_id, matiere, couleur, poids_g, cout_g, cout_total)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    object_id, component.get("matiere", ""), component.get("couleur", ""),
                    component.get("poids_g", 0.0), component.get("cout_g", 0.0),
                    component.get("cout_g", 0.0) * component.get("poids_g", 0.0),
                ),
            )
        conn.commit()
        return object_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_printed_objects() -> list[dict]:
    """Return saved objects with their composition and complete snapshots."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM objets_imprimes ORDER BY date_creation DESC, id DESC"
    ).fetchall()
    objects = []
    for row in rows:
        item = dict(row)
        item["composition"] = [
            dict(component)
            for component in conn.execute(
                "SELECT matiere, couleur, poids_g, cout_g, cout_total "
                "FROM compositions_objet WHERE objet_id = ? ORDER BY id",
                (row["id"],),
            ).fetchall()
        ]
        try:
            item["donnees"] = json.loads(row["donnees_json"] or "{}")
        except json.JSONDecodeError:
            item["donnees"] = {}
        objects.append(item)
    conn.close()
    return objects


@dataclass
class Printer:
    id: int
    nom: str


@dataclass
class FilamentModule:
    id: int
    nom: str
    conso_kw: float


def get_printers() -> list[Printer]:
    conn = get_connection()
    rows = conn.execute("SELECT id, nom FROM imprimantes ORDER BY nom").fetchall()
    conn.close()
    return [Printer(row["id"], row["nom"]) for row in rows]


def add_printer(nom: str) -> int:
    """Ajoute une imprimante et retourne son identifiant."""
    conn = get_connection()
    cur = conn.execute("INSERT INTO imprimantes (nom) VALUES (?)", (nom.strip(),))
    conn.commit()
    printer_id = cur.lastrowid
    conn.close()
    return printer_id


def delete_printer(printer_id: int) -> None:
    """Supprime une imprimante et tous ses profils matière associés."""
    conn = get_connection()
    # Les anciennes bases SQLite peuvent ne pas activer les clés étrangères :
    # on supprime donc explicitement les profils avant l'imprimante.
    conn.execute("DELETE FROM consommations_imprimante WHERE imprimante_id = ?", (printer_id,))
    conn.execute("DELETE FROM imprimantes WHERE id = ?", (printer_id,))
    conn.commit()
    conn.close()


def get_printer_material_profiles(printer_id: int) -> list[tuple[str, float]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT matiere, conso_kw FROM consommations_imprimante "
        "WHERE imprimante_id = ? ORDER BY matiere",
        (printer_id,),
    ).fetchall()
    conn.close()
    return [(row["matiere"], row["conso_kw"]) for row in rows]


def get_printer_consumption(printer_id: int | None, matiere: str) -> float | None:
    """Retourne la consommation du couple imprimante/matière, ou None si absente.

    Un profil exact est prioritaire. Sinon, le nom du profil peut être contenu
    dans le libellé du filament : le profil ``PLA`` s'applique ainsi à
    ``PLA Basic``, ``PLA Matte`` ou ``PLA-CF``.
    """
    if printer_id is None or not matiere:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT conso_kw FROM consommations_imprimante "
        "WHERE imprimante_id = ? AND lower(matiere) = lower(?)",
        (printer_id, matiere.strip()),
    ).fetchone()
    if row:
        conn.close()
        return row["conso_kw"]

    # Les profils les plus spécifiques sont testés en premier : un futur
    # profil "PLA-CF" prévaut donc sur le profil générique "PLA".
    profiles = conn.execute(
        "SELECT matiere, conso_kw FROM consommations_imprimante "
        "WHERE imprimante_id = ? ORDER BY length(matiere) DESC",
        (printer_id,),
    ).fetchall()
    conn.close()
    material_label = matiere.strip().lower()
    for profile in profiles:
        profile_material = profile["matiere"].strip().lower()
        if profile_material and profile_material in material_label:
            return profile["conso_kw"]
    return None


def set_printer_consumption(printer_id: int, matiere: str, conso_kw: float) -> None:
    """Crée ou met à jour la consommation moyenne (kW) d'une matière."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO consommations_imprimante (imprimante_id, matiere, conso_kw) "
        "VALUES (?, ?, ?) "
        "ON CONFLICT(imprimante_id, matiere) DO UPDATE SET conso_kw = excluded.conso_kw",
        (printer_id, matiere.strip().upper(), conso_kw),
    )
    conn.commit()
    conn.close()


def delete_printer_consumption(printer_id: int, matiere: str) -> None:
    conn = get_connection()
    conn.execute(
        "DELETE FROM consommations_imprimante WHERE imprimante_id = ? AND matiere = ?",
        (printer_id, matiere),
    )
    conn.commit()
    conn.close()


def get_filament_modules() -> list[FilamentModule]:
    conn = get_connection()
    rows = conn.execute("SELECT id, nom, conso_kw FROM modules_filament ORDER BY nom").fetchall()
    conn.close()
    return [FilamentModule(row["id"], row["nom"], row["conso_kw"]) for row in rows]


def add_filament_module(nom: str, conso_kw: float) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO modules_filament (nom, conso_kw) VALUES (?, ?)",
        (nom.strip(), conso_kw),
    )
    conn.commit()
    module_id = cur.lastrowid
    conn.close()
    return module_id


def update_filament_module(module_id: int, nom: str, conso_kw: float) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE modules_filament SET nom = ?, conso_kw = ? WHERE id = ?",
        (nom.strip(), conso_kw, module_id),
    )
    conn.commit()
    conn.close()


def delete_filament_module(module_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM modules_filament WHERE id = ?", (module_id,))
    conn.commit()
    conn.close()


@dataclass
class Filament:
    id: int
    matiere: str
    couleur: str
    fournisseur: str
    prix_bobine: float             # prix réellement payé (avec remise éventuelle)
    prix_bobine_catalogue: float   # prix catalogue fournisseur, sans remise (0/None = inconnu)
    poids_bobine_g: float

    @property
    def cout_par_g(self) -> float:
        """Coût réel par gramme, basé sur le prix effectivement payé."""
        return self.prix_bobine / self.poids_bobine_g if self.poids_bobine_g else 0.0

    @property
    def cout_par_g_catalogue(self) -> float:
        """Coût par gramme au prix catalogue (sans remise). Si inconnu, retombe sur le prix réel
        (pas de remise connue => bas et haut se confondent, plutôt qu'un coût à zéro absurde)."""
        prix_ref = self.prix_bobine_catalogue if self.prix_bobine_catalogue else self.prix_bobine
        return prix_ref / self.poids_bobine_g if self.poids_bobine_g else 0.0

    @property
    def display_name(self) -> str:
        base = " ".join(p for p in (self.matiere, self.couleur) if p)
        return f"{base} ({self.fournisseur})" if self.fournisseur else base


def _row_to_filament(row) -> Filament:
    return Filament(row["id"], row["matiere"], row["couleur"], row["fournisseur"],
                     row["prix_bobine"], row["prix_bobine_catalogue"], row["poids_bobine_g"])


def get_filaments() -> list[Filament]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM filaments ORDER BY matiere, couleur").fetchall()
    conn.close()
    return [_row_to_filament(row) for row in rows]


def add_filament(matiere: str, couleur: str, fournisseur: str,
                  prix_bobine: float, prix_bobine_catalogue: float, poids_bobine_g: float) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO filaments (matiere, couleur, fournisseur, prix_bobine, prix_bobine_catalogue, poids_bobine_g) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (matiere, couleur, fournisseur, prix_bobine, prix_bobine_catalogue or None, poids_bobine_g),
    )
    conn.commit()
    conn.close()


def delete_filament(filament_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM filaments WHERE id = ?", (filament_id,))
    conn.commit()
    conn.close()


def _norm(s: str) -> str:
    """Normalise pour comparaison : espaces superflus retirés, insensible à la casse."""
    return (s or "").strip().lower()


def find_matching_filament(matiere: str, couleur: str, fournisseur: str,
                            prix_bobine: float) -> "Filament | None":
    """Cherche une référence existante identique : même matière, même couleur,
    même fournisseur et même prix de bobine (comparaison insensible à la casse/espaces,
    prix arrondi au centime pour éviter les faux négatifs d'arrondi flottant)."""
    for f in get_filaments():
        if (_norm(f.matiere) == _norm(matiere)
                and _norm(f.couleur) == _norm(couleur)
                and _norm(f.fournisseur) == _norm(fournisseur)
                and round(f.prix_bobine, 2) == round(prix_bobine, 2)):
            return f
    return None


CSV_COLUMNS = ["matiere", "couleur", "fournisseur", "prix_bobine", "prix_bobine_catalogue", "poids_bobine_g"]


def export_filaments_csv(path: str) -> int:
    """Exporte tous les filaments vers un fichier CSV. Retourne le nombre de lignes écrites."""
    import csv
    filaments = get_filaments()
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, delimiter=";")
        writer.writeheader()
        for fil in filaments:
            writer.writerow({
                "matiere": fil.matiere,
                "couleur": fil.couleur,
                "fournisseur": fil.fournisseur,
                "prix_bobine": fil.prix_bobine,
                "prix_bobine_catalogue": fil.prix_bobine_catalogue or "",
                "poids_bobine_g": fil.poids_bobine_g,
            })
    return len(filaments)


def import_filaments_csv(path: str) -> tuple[int, int, list[str]]:
    """Importe des filaments depuis un CSV.

    Règle de fusion : si un filament existant a déjà la même matière, la même
    couleur, le même fournisseur ET le même prix réel de bobine, on considère
    que c'est la même référence — on met juste à jour son poids de bobine et
    son prix catalogue au lieu d'en créer une deuxième ligne. Sinon, nouvelle
    référence. La colonne prix_bobine_catalogue est optionnelle dans le CSV.

    Retourne (ajoutés, mis_a_jour, erreurs) — une ligne invalide est ignorée
    avec un message, l'import continue toujours jusqu'au bout.
    """
    import csv

    added = 0
    updated = 0
    errors: list[str] = []

    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(2048)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        reader = csv.DictReader(f, dialect=dialect)

        for line_num, row in enumerate(reader, start=2):
            matiere = (row.get("matiere") or "").strip()
            couleur = (row.get("couleur") or "").strip()
            if not matiere and not couleur:
                errors.append(f"Ligne {line_num} : matière et couleur manquantes, ignorée")
                continue
            try:
                prix_bobine = float(str(row.get("prix_bobine", "0")).replace(",", "."))
                poids_bobine_g = float(str(row.get("poids_bobine_g", "0")).replace(",", "."))
            except ValueError:
                errors.append(f"Ligne {line_num} ('{matiere} {couleur}') : prix ou poids invalide, ignorée")
                continue

            raw_catalogue = str(row.get("prix_bobine_catalogue", "")).strip()
            prix_bobine_catalogue = None
            if raw_catalogue:
                try:
                    prix_bobine_catalogue = float(raw_catalogue.replace(",", "."))
                except ValueError:
                    errors.append(f"Ligne {line_num} ('{matiere} {couleur}') : prix catalogue invalide, ignoré (garde le reste de la ligne)")

            fournisseur = (row.get("fournisseur") or "").strip()

            existing = find_matching_filament(matiere, couleur, fournisseur, prix_bobine)
            conn = get_connection()
            if existing:
                # Même référence (matière + couleur + fournisseur + prix réel identiques) : on fusionne
                conn.execute(
                    "UPDATE filaments SET poids_bobine_g=?, prix_bobine_catalogue=? WHERE id=?",
                    (poids_bobine_g, prix_bobine_catalogue, existing.id),
                )
                updated += 1
            else:
                conn.execute(
                    "INSERT INTO filaments (matiere, couleur, fournisseur, prix_bobine, prix_bobine_catalogue, poids_bobine_g) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (matiere, couleur, fournisseur, prix_bobine, prix_bobine_catalogue, poids_bobine_g),
                )
                added += 1
            conn.commit()
            conn.close()

    return added, updated, errors
'ollama'


@dataclass
class Composition:
    id: int
    objet_id: int
    matiere: str
    couleur: str
    poids_g: float
    cout_g: float
    cout_total: float


@dataclass
class ObjetImpression:
    id: int
    nom: str
    date_creation: str
    statut: str
    imprimante_id: int | None
    module_filament_id: int | None
    poids_total_g: float
    temps_impression_h: float
    temps_finition_h: float
    cout_filament_base: float
    cout_machine: float
    cout_electrique: float
    cout_emballage: float
    cout_divers: float
    cout_main_oeuvre: float
    cout_total_ht: float
    prix_plancher_ht: float
    prix_conseille_ht: float
    prix_conseille_ttc: float
    notes: str | None
    compositions: list[Composition] = field(default_factory=list)


def get_connection() -> sqlite3.Connection:
    ensure_user_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # ⬅️ Ajoute ici
    return conn


# ─── CRUD Objets ───
def save_objet(obj: ObjetImpression, compositions: list[Composition]) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO objets_imprimes
               (nom, date_creation, statut, imprimante_id, module_filament_id,
                poids_total_g, temps_impression_h, temps_finition_h,
                cout_filament_base, cout_machine, cout_electrique,
                cout_emballage, cout_divers, cout_main_oeuvre,
                cout_total_ht, prix_plancher_ht, prix_conseille_ht, prix_conseille_ttc, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (obj.nom, obj.date_creation, obj.statut, obj.imprimante_id, obj.module_filament_id,
             obj.poids_total_g, obj.temps_impression_h, obj.temps_finition_h,
             obj.cout_filament_base, obj.cout_machine, obj.cout_electrique,
             obj.cout_emballage, obj.cout_divers, obj.cout_main_oeuvre,
             obj.cout_total_ht, obj.prix_plancher_ht, obj.prix_conseille_ht, obj.prix_conseille_ttc, obj.notes)
        )
        objet_id = cur.lastrowid
        for c in compositions:
            conn.execute(
                "INSERT INTO compositions_objet (objet_id, matiere, couleur, poids_g, cout_g, cout_total) VALUES (?,?,?,?,?,?)",
                (objet_id, c.matiere, c.couleur, c.poids_g, c.cout_g, c.cout_total)
            )
        conn.commit()
    return objet_id


def get_objets(imprimante_id: int | None = None) -> list[ObjetImpression]:
    with get_connection() as conn:
        sql = "SELECT * FROM objets_imprimes"
        params = ()
        if imprimante_id is not None:
            sql += " WHERE imprimante_id = ?"
            params = (imprimante_id,)

        rows = conn.execute(sql, params).fetchall()
        objets = []
        for row in rows:
            comps_rows = conn.execute(
                "SELECT * FROM compositions_objet WHERE objet_id = ?", (row["id"],)
            ).fetchall()
            compositions = [Composition(**dict(r)) for r in comps_rows]
            objs = ObjetImpression(**dict(row), compositions=compositions)
            objets.append(objs)
        return sorted(objets, key=lambda x: x.date_creation, reverse=True)


def delete_objet(id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM compositions_objet WHERE objet_id = ?", (id,))
        conn.execute("DELETE FROM objets_imprimes WHERE id = ?", (id,))
        conn.commit()

        @dataclass
        class CompositionObjet:
            """Représente une ligne de filament dans un objet (pour le mode multicolore)."""
            id: int
            objet_id: int
            matiere: str
            couleur: str
            poids_g: float
            cout_g: float
            cout_total: float

        @dataclass
        class ObjetImpression:
            """Structure de données pour un objet imprimé finalisé."""
            id: int
            nom: str
            date_creation: str
            statut: str  # 'termine', 'en_cours', etc.
            imprimante_id: int | None
            module_filament_id: int | None

            poids_total_g: float
            temps_impression_h: float
            temps_finition_h: float

            cout_filament_base: float
            cout_machine: float
            cout_electrique: float
            cout_emballage: float
            cout_divers: float
            cout_main_oeuvre: float
            cout_total_ht: float
            prix_plancher_ht: float
            prix_conseille_ht: float
            prix_conseille_ttc: float

            notes: str | None

            # Liste des composants (seulement si mode multicolore, sinon une liste de 1)
            compositions: list[CompositionObjet] = field(default_factory=list)

        def save_objet_et_compositions(
                objet: ObjetImpression,
                compositions: list[CompositionObjet],
                db_path: str = DB_PATH
        ):
            """Enregistre un objet et ses composants (filaments) dans la base."""
            with sqlite3.connect(db_path) as conn:
                # 1. On insère l'objet principal
                cur = conn.execute(
                    """INSERT INTO objets_imprimes
                       (nom, date_creation, statut, imprimante_id, module_filament_id,
                        poids_total_g, temps_impression_h, temps_finition_h,
                        cout_filament_base, cout_machine, cout_electrique,
                        cout_emballage, cout_divers, cout_main_oeuvre,
                        cout_total_ht, prix_plancher_ht, prix_conseille_ht, prix_conseille_ttc, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (objet.nom, objet.date_creation, objet.statut,
                     objet.imprimante_id, objet.module_filament_id,
                     objet.poids_total_g, objet.temps_impression_h, objet.temps_finition_h,
                     objet.cout_filament_base, objet.cout_machine, objet.cout_electrique,
                     objet.cout_emballage, objet.cout_divers, objet.cout_main_oeuvre,
                     objet.cout_total_ht, objet.prix_plancher_ht, objet.prix_conseille_ht,
                     objet.prix_conseille_ttc, objet.notes)
                )

                # 2. On récupère l'ID de l'objet qu'on vient de créer
                id_objet = cur.lastrowid

                # 3. On insère toutes les lignes de la composition (Multicolor)
                for c in compositions:
                    conn.execute(
                        """INSERT INTO compositions_objet
                               (objet_id, matiere, couleur, poids_g, cout_g, cout_total)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (id_objet, c.matiere, c.couleur, c.poids_g, c.cout_g, c.cout_total)
                    )

                conn.commit()
            return id_objet

        def get_objets_historique(db_path: str = DB_PATH, limit: int = 50):
            """Récupère l'historique des impressions avec leurs détails."""
            with sqlite3.connect(db_path) as conn:
                # On récupère les objets (trier par date décroissante pour voir le plus récent en haut)
                rows = conn.execute(
                    "SELECT * FROM objets_imprimes ORDER BY date_creation DESC LIMIT ?",
                    (limit,)
                ).fetchall()

                resultats = []
                for row in rows:
                    # Pour chaque objet, on charge ses filaments (compositions)
                    comps_rows = conn.execute(
                        "SELECT * FROM compositions_objet WHERE objet_id = ?",
                        (row["id"],)
                    ).fetchall()

                    compositions = [CompositionObjet(**dict(r)) for r in comps_rows]

                    # On assemble tout dans notre dataclass
                    o_data = dict(row)
                    o_data['compositions'] = compositions
                    resultats.append(ObjetImpression(**o_data))

            return resultats