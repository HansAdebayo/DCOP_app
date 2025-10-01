# Générateur DCOP (XCSP 2.1_FRODO) & App Streamlit

Ce projet fournit :

* **Un générateur d’instances DCOP** au format **XCSP 2.1 (profil FRODO)** avec deux **modélisations** :

  * **Modèle 1 (x_ij binaire)** : une variable par couple *voiture–passager* (0/1), contraintes AMO/ALO et capacités par sous-ensembles.
  * **Modèle 2 (y_j catégoriel)** : une variable par passager dont la valeur ∈ {1..N_voitures}, coûts unaires et capacités n‑aires « K+1 interdits ».
* **Une application Streamlit** pour paramétrer, générer, prévisualiser et **télécharger** les fichiers XML.

---

## 🧩 Architecture des fichiers

```
.
├── app.py                               # Application Streamlit (Modèle 1 & 2)
├── constructeur_dcop.py                 # Générateur DCOP (fonctions communes M1 & M2)
├── dcop_builder_model1.py               # (Optionnel) Variante M1 factorisée
├── dcop_builder_model2.py               # (Optionnel) Variante M2 factorisée avec n-aires
└── examples/
    ├── instance_model1.xml
    └── instance_model2.xml
```

> **Remarque** : si vous n’utilisez que `constructeur_dcop.py`, `app.py` s’appuie uniquement sur ce fichier.

---

## ⚙️ Installation rapide

1. Créez un environnement Python ≥ 3.9 et installez Streamlit :

```bash
pip install streamlit
```

2. Placez `app.py` et `constructeur_dcop.py` au même niveau.

3. Lancez l’app :

```bash
streamlit run app.py
```

---

## 🏗️ Modèles de modélisation

### Modèle 1 — Variables binaires x_ij

* **Idée** : `x_ij ∈ {0,1}` vaut 1 si la voiture i prend le passager j.
* **Agents** : les voitures portent les variables liées à leurs couples.
* **Coûts** : relations **unaires soft** sur chacune des variables `x_ij` (coût si `x_ij=1`).
* **Contraintes** :

  * **AMO** (Au Plus Une voiture par passager) via pénalité `infinity` sur les paires `(x_i1j=1, x_i2j=1)`.
  * **ALO** (Au Moins Une voiture par passager) via pénalité `infinity` sur le **n‑aire** « tout‑zéro ».
  * **Capacité** : pour chaque voiture de capacité K, pénalité `infinity` sur tout sous‑ensemble de **K+1** variables `x_i*` toutes à 1.

**Avantages** : formulation standard CSP/DCOP, contrôle fin.
**Inconvénients** : beaucoup de variables (|V|×|P|) et de contraintes.

---

### Modèle 2 — Variables catégorielles y_j

* **Idée** : une variable par passager, `y_j ∈ {1..N_voitures}` = index de la voiture choisie.
* **Agents** : attribution cyclique (ou personnalisée) d’un agent hébergeur à chaque `y_j`.
* **Coûts** : relation **unaire soft** par variable (`cost: value`).
* **Capacité** : pour chaque voiture de capacité K, pénalité `infinity` sur tout **(K+1)-uplet** égal à la valeur correspondante (ex. `2 2 2` si K=2).

**Avantages** : peu de variables (|P|), coûts simples.
**Inconvénients** : nécessite des **relations n‑aires** pour les capacités.

---

## 🧪 Fonctions principales (`constructeur_dcop.py`)

```python
construire_instance_xcsp(voitures, passagers, capacite_par_voiture, couts, nom="...", format_str="XCSP 2.1_FRODO") -> str
```

* Génère **Modèle 1** (binaires) : XMl XCSP complet.

```python
construire_instance_xcsp_alt(voitures, passagers, capacite_par_voiture, couts, nom="...", format_str="XCSP 2.1_FRODO") -> str
```

* Génère **Modèle 2** (catégoriel) : XMl XCSP complet.

```python
generer_positions_aleatoires(n, largeur, hauteur, graine) -> List[(x,y)]
```

* Outil pratique pour simuler des positions.

```python
construire_json_a_partir_positions(nom, voitures, passagers, couts_entiers=True, mode_depot="aucun", dest_commune=None, dest_par_passager=None, poids_ramassage=1.0, poids_depot=1.0) -> dict
```

* Construit un **JSON d’instance** à partir de positions, capacités, etc. et calcule `couts[(v,p)]`.

```python
json_vers_xml(obj_json, modelisation=1|2) -> str
```

* Convertit un **JSON d’instance** en **XML XCSP** via le modèle choisi.

```python
afficher_json_joli(obj) -> str
```

* Rend un JSON joliment indenté.

---

## 🖥️ Utilisation de l’app Streamlit

1. Ouvrez l’app : `streamlit run app.py`
2. Dans la **sidebar** :

   * Renseignez **nom d’instance**, **agents**, **domaine** (nom & valeurs), mode **minimize/maximize**.
3. Utilisez les **onglets** :

   * **Modèle 1** : collez les JSON pour `Variables→Agents`, `Contraintes unaires` (soft/hard) et `Contraintes binaires` (soft/hard). Cliquez **Générer**.
   * **Modèle 2** : collez les JSON pour `Variables→Agents`, `Coûts unaires` et (optionnel) **Relations n‑aires** de capacité. Cliquez **Générer**.
4. Visualisez le **XML** généré et **téléchargez** le fichier.

### Exemples JSON (Modèle 2)

**Variables → Agents**

```json
{
  "y1": "v1",
  "y2": "v2",
  "y3": "v3"
}
```

**Coûts unaires**

```json
{
  "y1": {"1": 201, "2": 170, "3": 150},
  "y2": {"1": 169, "2": 169, "3": 198},
  "y3": {"1": 151, "2": 140, "3": 161}
}
```

**Capacité (n‑aire, optionnel)**

```json
[
  {"name":"CAP_V1_SUBSET1","arity":3,"scope":["y1","y2","y3"],"tuples":[[1000000,[1,1,1]]]},
  {"name":"CAP_V2_SUBSET1","arity":3,"scope":["y1","y2","y3"],"tuples":[[1000000,[2,2,2]]]},
  {"name":"CAP_V3_SUBSET1","arity":3,"scope":["y1","y2","y3"],"tuples":[[1000000,[3,3,3]]]}
]
```

> Utilisez une **grande pénalité** (ex. `1000000`) si votre solveur n’accepte pas littéralement `infinity`.

---

## 🧾 Exemple de sortie (Modèle 2, extrait)

```xml
<relations nbRelations="6">
  <relation name="Cost_y1" arity="1" semantics="soft" defaultCost="0" nbTuples="3">
    201: 1 | 170: 2 | 150: 3
  </relation>
  ...
  <relation name="CAP_V2_SUBSET1" arity="3" semantics="soft" defaultCost="0" nbTuples="1">
    1000000: 2 2 2
  </relation>
</relations>
```

---

## 🧠 Notes importantes (XCSP / FRODO)

* **Tags/attributs** doivent être en **anglais** : `name`, `arity`, `semantics`, `defaultCost`, `scope`, `maximize`, `domains`, `constraints`, etc.
* **maxConstraintArity** ≥ **toute arité** réellement utilisée (ex. 3 si vous avez des contraintes ternaires).
* **Coûts soft** : `"cost: values"` séparés par `|`.
* **Hard** (autorisations) : soit `semantics="hard"` avec *tuples autorisés*, soit **soft** avec grosse pénalité pour les interdits.
* **`agent="..."` n’est pas une affectation de valeur** : il désigne l’**hébergeur** de la variable dans l’algo distribué.
* Le **graphe de contraintes** affiché par certains outils ne montre que les **binaires** ; les **n‑aires** peuvent ne pas apparaître visuellement.

---

## 🔧 Dépannage (FAQ)

**Q1. FRODO donne une solution où tous les passagers vont dans la même voiture.**
R: Vérifiez que vos **relations n‑aires de capacité** sont bien présentes avec le **scope correct** et `arity` cohérente. Si la capacité K ≥ nb de passagers, aucune contrainte n‑aire ne sera générée (c’est normal).

**Q2. Le graphe de contraintes est vide.**
R: Vous n’avez que des **unaires** (et éventuellement des n‑aires). Ajoutez au moins une **binaire** si vous voulez voir des arêtes.

**Q3. Erreur de parsing XCSP.**
R: Vérifiez l’**ordre des variables** dans `scope` vs. l’ordre des valeurs listées dans les `tuples`. Assurez-vous que `nbRelations`/`nbConstraints` correspondent réellement au contenu.

**Q4. `infinity` non supporté.**
R: Remplacez par une **grosse pénalité** (ex. `1000000`).

**Q5. Comment choisir les agents ?**
R: L’assignation `agent="vX"` est **organisationnelle** (qui héberge la variable) et peut influer sur la performance de l’algo distribué (DFS, messages). Fonctionnellement, cela n’impose pas la valeur de la variable.

---

## 🧪 Exemple d’usage Python (sans Streamlit)

```python
from constructeur_dcop import (
    construire_instance_xcsp,
    construire_instance_xcsp_alt,
    construire_json_a_partir_positions,
    json_vers_xml,
)

voitures = ["v1","v2","v3"]
passagers = ["p1","p2","p3"]
capacite = {"v1": 2, "v2": 2, "v3": 2}
# coûts au format dict[(voiture, passager)] = coût
couts = { (v,p): 100 for v in voitures for p in passagers }

xml_m1 = construire_instance_xcsp(voitures, passagers, capacite, couts, nom="ex_M1")
xml_m2 = construire_instance_xcsp_alt(voitures, passagers, capacite, couts, nom="ex_M2")

print(xml_m2)
```

---

## 🗺️ Feuille de route (extensions possibles)

* Ajout d’un **import/export CSV** des coûts.
* Validation automatique : couverture complète des valeurs du domaine, **types**, **scopes**.
* Binarisation optionnelle des contraintes n‑aires.
* Paramètre global `penalite_inf` pour remplacer `infinity` par une grande valeur.

---

## 📝 Licence

Projet fourni à titre pédagogique. Vérifiez la licence de FRODO pour l’utilisation et la redistribution de l’outil de résolution.
