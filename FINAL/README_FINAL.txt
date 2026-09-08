CALCULATEUR 3D - DISTRIBUTION FINALE
====================================

EXECUTION DIRECTE
-----------------
Double-cliquer sur Calculateur3D.exe.

La base utilisateur print3d_calc.db est creee automatiquement au premier
lancement a cote de l'executable. Elle contient les donnees modifiables de
l'utilisateur et ne doit pas etre remplacee lors d'une mise a jour.

RECOMPILATION
-------------
Le sous-dossier source contient tout le necessaire pour reconstruire le projet.
Depuis ce dossier, avec Python 3.11 ou plus recent :

1. Creer un environnement virtuel :
   python -m venv .venv

2. Activer l'environnement sous Windows :
   .venv\Scripts\Activate.ps1

3. Installer les dependances :
   python -m pip install -r requirements.txt
   python -m pip install pyinstaller

4. Construire l'executable :
   pyinstaller --noconfirm --clean Calculateur3D.spec

Les fontes IBM Plex sont distribuees sous licence SIL Open Font License 1.1.
Le texte de licence est fourni dans source\assets\fonts\LICENSE-IBM-PLEX.txt.
