"""
Moteur de calcul de prix pour impression 3D.
Port direct de la logique VBA (Excel) validée et testée en conditions réelles.
Indépendant de toute interface graphique : testable seul, réutilisable.
"""
from dataclasses import dataclass


@dataclass
class PricingInputs:
    # Objet / impression
    poids_g: float              # poids de l'objet en grammes
    temps_impression_h: float   # temps machine (impression) en heures
    temps_finition_h: float     # temps de main d'oeuvre (finition manuelle) en heures

    # Filament
    cout_filament_par_g: float  # €/g (déjà = prix_bobine / poids_bobine)
    cout_filament_total: float = 0.0  # Remplace cout_filament_par_g si > 0 (mode multicouleur)
    # Taux (chargés depuis les paramètres, modifiables par l'utilisateur)
    taux_machine_h: float = 0.0     # coût horaire machine (amortissement + maintenance)
    conso_kw: float = 0.0           # consommation électrique moyenne de l'imprimante (kW)
    conso_module_filament_kw: float = 0.0  # consommation moyenne du module filament (AMS...)
    prix_kwh: float = 0.0           # prix de l'électricité (devise/kWh)
    taux_main_oeuvre_h: float = 0.0 # coût horaire de la main d'oeuvre
    taux_charges_pct: float = 0.0   # charges sociales, en % du prix de vente final (ex: URSSAF)
    emballage: float = 0.0          # coût emballage forfaitaire
    divers: float = 0.0             # frais divers forfaitaires
    marge_cible_pct: float = 0.0    # marge cible, en % du prix de vente final
    tva_pct: float = 0.0            # TVA, en % (0 = désactivée / non applicable)
    fournitures: float = 0.0        # vis, colle et autres consommables propres à l'objet


@dataclass
class PricingResult:
    cout_matiere: float
    cout_machine: float
    cout_electrique: float
    cout_module_filament: float
    cout_emballage: float
    cout_divers: float
    cout_fournitures: float
    montant_main_oeuvre: float
    cout_base: float          # somme des coûts, hors charges et marge
    prix_ht_plancher: float   # prix qui couvre juste les coûts + charges sociales (marge = 0)
    montant_charges: float
    prix_conseille_ht: float  # prix qui couvre coûts + charges + marge cible
    prix_conseille_ttc: float


def calculer(i: PricingInputs) -> PricingResult:
    """Calcule tous les coûts et prix à partir des saisies utilisateur.

    Règles reprises telles quelles de la version Excel/VBA validée :
    - Le coût machine et le coût électrique portent sur le temps d'IMPRESSION uniquement
      (l'imprimante tourne seule pendant l'impression, pas pendant la finition).
    - Le coût de main d'oeuvre porte sur le temps de FINITION uniquement
      (travail manuel, pas de main d'oeuvre pendant que la machine imprime).
        - Le prix est construit dans cet ordre : coût de revient, marge, charges,
            puis TVA. La marge et les charges sont des majorations successives
            du coût de revient.
    """
    if i.cout_filament_total > 0.001:
        cout_matiere = i.cout_filament_total
    else:
        cout_matiere = i.poids_g * i.cout_filament_par_g
    cout_machine = i.temps_impression_h * i.taux_machine_h
    cout_electrique_imprimante = i.temps_impression_h * i.conso_kw * i.prix_kwh
    cout_module_filament = i.temps_impression_h * i.conso_module_filament_kw * i.prix_kwh
    cout_electrique = cout_electrique_imprimante + cout_module_filament
    montant_main_oeuvre = i.temps_finition_h * i.taux_main_oeuvre_h

    cout_base = (
        cout_matiere
        + cout_machine
        + cout_electrique
        + montant_main_oeuvre
        + i.emballage
        + i.divers
        + i.fournitures
    )

    taux_charges = max(0.0, i.taux_charges_pct) / 100.0
    taux_marge = max(0.0, i.marge_cible_pct) / 100.0

    # Prix plancher : coût de revient augmenté des charges, sans marge.
    prix_ht_plancher = cout_base * (1 + taux_charges)
    montant_charges = prix_ht_plancher - cout_base

    # Prix conseillé : marge appliquée au coût, puis charges appliquées au résultat.
    prix_apres_marge = cout_base * (1 + taux_marge)
    prix_conseille_ht = prix_apres_marge * (1 + taux_charges)

    prix_conseille_ttc = prix_conseille_ht * (1 + max(0.0, i.tva_pct) / 100.0)

    return PricingResult(
        cout_matiere=cout_matiere,
        cout_machine=cout_machine,
        cout_electrique=cout_electrique,
        cout_module_filament=cout_module_filament,
        cout_emballage=i.emballage,
        cout_divers=i.divers,
        cout_fournitures=i.fournitures,
        montant_main_oeuvre=montant_main_oeuvre,
        cout_base=cout_base,
        prix_ht_plancher=prix_ht_plancher,
        montant_charges=montant_charges,
        prix_conseille_ht=prix_conseille_ht,
        prix_conseille_ttc=prix_conseille_ttc,
    )
