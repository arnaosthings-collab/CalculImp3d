CALCULATEUR DE PRIX — IMPRESSION 3D
=====================================

INSTALLATION (sur votre PC Windows)
------------------------------------
1. Installer Python (une seule fois) : https://www.python.org/downloads/
   Important : cocher "Add Python to PATH" pendant l'installation.

2. Ouvrir une invite de commandes dans le dossier de l'application, puis :
   pip install -r requirements.txt

3. Lancer l'application :
   python appV1.py

CRÉER LE .EXE (pour distribuer sans que l'utilisateur installe Python)
------------------------------------------------------------------------
1. Installer PyInstaller :
   pip install pyinstaller

2. Générer l'exécutable :
   pyinstaller --onefile --windowed --name "Calculateur3D" appV1.py

3. Le fichier .exe apparaît dans le dossier "dist" — c'est lui qu'on distribue.
   Il embarque tout (Python + PySide6 + votre code) : la personne qui le reçoit
   n'a besoin d'installer ni Python, ni rien d'autre.

Note : l'exécutable embarque une base modèle préremplie. Au premier lancement,
il crée une copie externe modifiable nommée print3d_calc.db à côté de l'exécutable.
Si ce dossier n'est pas accessible en écriture, elle est créée dans
%LOCALAPPDATA%\Calculateur3D. Conservez ce fichier pour garder vos filaments,
imprimantes et taux enregistrés lors d'une mise à jour.

CONSOMMATION SELON L'IMPRIMANTE ET LA MATIÈRE
----------------------------------------------
Dans l'onglet « Calculateur », la matière du filament et l'imprimante
sélectionnée déterminent automatiquement la consommation électrique utilisée.
L'onglet « Imprimantes » permet d'ajouter une machine et de créer, modifier ou
supprimer sa puissance moyenne (en kW) pour chaque matière.

Des profils Bambu Lab sont créés au premier lancement à partir des puissances
moyennes fournies : séries P1, P2, X1/X2, H2 et A1/A2. La consommation
manuelle reste disponible comme valeur de secours lorsqu'aucun profil ne
correspond à la matière. Les puissances maximales et celles de l'AMS ne sont
pas utilisées dans le coût d'impression : elles correspondent à des pics ou à
des accessoires optionnels, pas à la puissance moyenne d'impression.

MODULES D'ALIMENTATION FILAMENT
-------------------------------
Le calculateur permet de sélectionner « Aucun module » ou un module
d'alimentation filament (AMS, AMS lite, AMS 2 Pro, AMS HT, ou un module ajouté
manuellement). Sa puissance moyenne en fonctionnement est ajoutée au coût
électrique pour toute la durée d'impression. L'onglet « Modules filament »
permet de créer et modifier les modules d'autres marques.

STRUCTURE DU PROJET
--------------------
- pricing.py    : le moteur de calcul (formules), indépendant de l'interface
- database.py   : sauvegarde SQLite (paramètres + filaments + imprimantes)
- appV1.py      : l'interface graphique principale, avec le thème visuel
- app.py        : ancienne interface fonctionnelle, conservée comme référence
