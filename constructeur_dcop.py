# constructeur_dcop.py
from itertools import combinations
from xml.sax.saxutils import escape
import math, json, random
from typing import Dict, List, Tuple

def euclid(a: Tuple[float,float], b: Tuple[float,float]) -> float:
    """Calcule la distance euclidienne entre deux points (tuples de flottants)."""
    return math.hypot(a[0]-b[0], a[1]-b[1])

def construire_instance_xcsp(
    voitures: List[str],
    passagers: List[str],
    capacite_par_voiture: Dict[str, int],
    couts: Dict[Tuple[str, str], int],
    nom: str = "ramassage_auto",
    format_str: str = "XCSP 2.1_FRODO",
) -> str:
    """
    Construit une instance de Problème d'Optimisation à Contraintes Distribuées (DCOP)
    au format XML XCSP 2.1 (FRODO) pour le problème de ramassage.
    
    Les contraintes incluent :
    - Coûts unitaires doux (minimisation).
    - Chaque passager est pris par EXACTEMENT une voiture.
    - Contrainte de capacité pour chaque voiture.
    """
    # 1. Validations initiales
    for v in voitures:
        if v not in capacite_par_voiture:
            raise ValueError(f"Capacité manquante pour la voiture {v}")
    for v in voitures:
        for p in passagers:
            if (v, p) not in couts:
                raise ValueError(f"Coût manquant pour ({v},{p})")

    nb_agents = len(voitures)
    nb_variables = len(voitures) * len(passagers)

    xml = []
    xml.append('<instance>')
    xml.append(
        f'  <presentation nom="{escape(nom)}" maxConstraintArity="{max(len(voitures), max(capacite_par_voiture.values())+1)}" format="{escape(format_str)}" maximiser="false"/>'
    )

    # 2. Agents
    xml.append(f'  <agents nbAgents="{nb_agents}">')
    for v in voitures:
        xml.append(f'    <agent nom="{escape(v)}"/>')
    xml.append('  </agents>')

    # 3. Domaines
    xml.append('  <domaines nbDomaines="1">')
    xml.append('    <domaine nom="bin" nbValeurs="2">0 1</domaine>')
    xml.append('  </domaines>')

    # 4. Variables
    xml.append(f'  <variables nbVariables="{nb_variables}">')
    noms_variables = {}
    for i, v in enumerate(voitures, start=1):
        for j, p in enumerate(passagers, start=1):
            nom_var = f"x{i}{j}"
            noms_variables[(v, p)] = nom_var
            # x_ij = 1 si la voiture i prend le passager j. La voiture i est l'agent.
            xml.append(f'    <variable nom="{nom_var}" domaine="bin" agent="{escape(v)}"/>')
    xml.append('  </variables>')

    relations, contraintes = [], []

    # 5. Contraintes de Coûts Unitaires (Soft)
    for (v, p), nom_var in noms_variables.items():
        cout = int(couts[(v, p)])
        nom_rel = f"Cout_{nom_var}"
        relations.append(
            # Coût 'cout' si la variable prend la valeur 1
            f'    <relation nom="{nom_rel}" arite="1" semantique="soft" coutParDefaut="0" nbTuples="1">{cout}: 1</relation>'
        )
        contraintes.append(
            f'    <contrainte nom="cout_{nom_var}" arite="1" portee="{nom_var}" reference="{nom_rel}"/>'
        )

    # 6. Contraintes d'Unicité par Passager (AMO + Interdiction Tout-Zéro)
    for j, p in enumerate(passagers, start=1):
        # A. Contraintes AMO (Au Plus Une)
        indices_voitures = list(enumerate(voitures, start=1))
        for (i1, _), (i2, _) in combinations(indices_voitures, 2):
            v1, v2 = f"x{i1}{j}", f"x{i2}{j}"
            nom_rel = f"AMO_{p}_{i1}_{i2}"
            relations.append(
                # Coût infini si les deux sont à 1
                f'    <relation nom="{nom_rel}" arite="2" semantique="soft" coutParDefaut="0" nbTuples="1">infinity: 1 1</relation>'
            )
            contraintes.append(
                f'    <contrainte nom="amo_{p}_{i1}_{i2}" arite="2" portee="{v1} {v2}" reference="{nom_rel}"/>'
            )
        # B. Interdiction du Tout-Zéro (Au Moins Une)
        toutes_vars = " ".join(f"x{i}{j}" for i in range(1, len(voitures)+1))
        zeros = " ".join("0" for _ in voitures)
        nom_rel = f"PAS_DE_TOUT_ZERO_{p}"
        relations.append(
            # Coût infini si toutes les variables sont à 0
            f'    <relation nom="{nom_rel}" arite="{len(voitures)}" semantique="soft" coutParDefaut="0" nbTuples="1">infinity: {zeros}</relation>'
        )
        contraintes.append(
            f'    <contrainte nom="pas_de_tout_zero_{p}" arite="{len(voitures)}" portee="{toutes_vars}" reference="{nom_rel}"/>'
        )

    # 7. Contraintes de Capacité par Voiture (Interdiction Tout-Un sur K+1)
    for i, v in enumerate(voitures, start=1):
        K = int(capacite_par_voiture[v])
        if K >= len(passagers):
            continue
        indices_passagers = range(1, len(passagers)+1)
        for idx, sous_ensemble in enumerate(combinations(indices_passagers, K + 1), start=1):
            vars_portee = [f"x{i}{j}" for j in sous_ensemble]
            portee_str = " ".join(vars_portee)
            uns = " ".join("1" for _ in vars_portee)
            nom_rel = f"CAP_AU_PLUS_{v}_{idx}"
            relations.append(
                # Coût infini si toutes les variables dans le sous-ensemble sont à 1
                f'    <relation nom="{nom_rel}" arite="{K+1}" semantique="soft" coutParDefaut="0" nbTuples="1">infinity: {uns}</relation>'
            )
            contraintes.append(
                f'    <contrainte nom="cap_{v}_{idx}" arite="{K+1}" portee="{portee_str}" reference="{nom_rel}"/>'
            )

    # 8. Assemblage final
    xml.append(f'  <relations nbRelations="{len(relations)}">')
    xml.extend(relations)
    xml.append('  </relations>')

    xml.append(f'  <contraintes nbContraintes="{len(contraintes)}">')
    xml.extend(contraintes)
    xml.append('  </contraintes>')
    xml.append('</instance>')
    return "\n".join(xml)

# ----------------------------------------------------------------------
# Fonctions de Génération et Conversion JSON
# ----------------------------------------------------------------------

def generer_positions_aleatoires(n: int, largeur: float, hauteur: float, graine: int):
    """Génère n positions (x,y) aléatoires dans une zone définie [0, L] x [0, H]."""
    rng = random.Random(graine)
    return [(rng.uniform(0, largeur), rng.uniform(0, hauteur)) for _ in range(n)]

def construire_json_a_partir_positions(
    nom: str,
    voitures: List[Tuple[str, int, Tuple[float, float]]],        # (id_voiture, capacite, (x,y))
    passagers: List[Tuple[str, Tuple[float, float]]],       # (id_passager, (x,y))
    couts_entiers: bool = True,
    mode_depot: str = "aucun",                                 # "aucun" | "commun" | "par_passager"
    dest_commune: Tuple[float,float] = None,                  # si "commun"
    dest_par_passager: Dict[str, Tuple[float,float]] = None,     # si "par_passager"
    poids_ramassage: float = 1.0,
    poids_depot: float = 1.0,
):
    """
    Construit un objet JSON décrivant l'instance (positions/capacités/coûts).
    Coût(v, p) = poids_ramassage * dist(pos_v, pos_p) + poids_depot * dist(pos_p, dest).
    """
    # Calcul des coûts
    couts = {}
    for id_v, _, pos_v in voitures:
        for id_p, pos_p in passagers:
            d_ramassage = euclid(pos_v, pos_p)
            d_depot = 0.0
            
            if mode_depot == "commun":
                if dest_commune is None:
                    raise ValueError("dest_commune requise avec mode_depot='commun'")
                d_depot = euclid(pos_p, dest_commune)
            elif mode_depot == "par_passager":
                if dest_par_passager is None or id_p not in dest_par_passager:
                    raise ValueError(f"Destination manquante pour {id_p}")
                d_depot = euclid(pos_p, dest_par_passager[id_p])
            
            valeur = poids_ramassage * d_ramassage + poids_depot * d_depot
            couts[(id_v, id_p)] = int(round(valeur)) if couts_entiers else valeur

    obj_json = {
        "nom": nom,
        "voitures": [
            {"id": id_v, "capacite": cap, "pos": {"x": pos_v[0], "y": pos_v[1]}}
            for (id_v, cap, pos_v) in voitures
        ],
        "passagers": [id_p for (id_p, _) in passagers],
        "positions_passagers": {
            id_p: {"x": pos_p[0], "y": pos_p[1]} for (id_p, pos_p) in passagers
        },
        "couts": {
            id_v: {id_p: couts[(id_v, id_p)] for (id_p, _) in passagers}
            for (id_v, _, _) in voitures
        },
    }
    # Stocker les destinations pour la traçabilité
    if mode_depot == "commun" and dest_commune is not None:
        obj_json["destination"] = {"x": dest_commune[0], "y": dest_commune[1]}
        obj_json["mode_depot"] = "commun"
        obj_json["poids_ramassage"] = poids_ramassage
        obj_json["poids_depot"] = poids_depot
    if mode_depot == "par_passager" and dest_par_passager is not None:
        obj_json["destinations"] = {
            id_p: {"x": d[0], "y": d[1]} for id_p, d in dest_par_passager.items()
        }
        obj_json["mode_depot"] = "par_passager"
        obj_json["poids_ramassage"] = poids_ramassage
        obj_json["poids_depot"] = poids_depot
    return obj_json

def json_vers_xml(obj_json: dict) -> str:
    """Convertit un objet JSON d'instance en chaîne XML XCSP."""
    voitures = [v["id"] for v in obj_json["voitures"]]
    passagers = list(obj_json["passagers"])
    
    # Récupérer les capacités (avec une valeur par défaut si absente)
    capacite_par_voiture = {v["id"]: int(v.get("capacite", len(passagers))) for v in obj_json["voitures"]}
    
    # Reconstruire le dictionnaire de coûts pour la fonction XCSP
    couts = {(id_v, id_p): int(obj_json["couts"][id_v][id_p]) 
             for id_v in obj_json["couts"] 
             for id_p in obj_json["couts"][id_v]}
             
    return construire_instance_xcsp(
        voitures, passagers, capacite_par_voiture, couts, nom=obj_json.get("nom", "ramassage_auto")
    )

def afficher_json_joli(obj: dict) -> str:
    """Affiche un objet JSON avec une indentation propre."""
    return json.dumps(obj, indent=2, ensure_ascii=False)