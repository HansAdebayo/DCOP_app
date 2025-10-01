# Pourquoi des solveurs donnent des solutions différentes ?

## TL;DR

Oui, c’est normal : selon **l’algorithme**, **l’heuristique**, le **traitement des égalités** (ties), la **gestion de `infinity`**, ou de légères **différences de modélisation**, deux solveurs (ou deux runs du même solveur) peuvent produire **des solutions différentes** — parfois avec **le même coût optimal**, parfois avec un **coût différent** si l’algorithme est incomplèt/anytime.

---

## 1) Différences d’algorithmes (complétude & garanties)

* **DPOP/ADPOP** (schéma dynamique + utilité) : *complets* si la fonction d’utilité est correctement agrégée. Ils retournent un **optimum global** (à égalité près) sur l’instance exacte. ADPOP peut être approché selon la borne.
* **Max-Sum / Max-Plus** (message passing, factor graph) : *incomplets* en général sur graphes cycliques → solutions **approchées**; qualité dépend de **damping**, **ordonnancement**, **nb d’itérations**.
* **MGM/MGM2/DSA** (méthodes locales) : *heuristiques locales* → peuvent rester en **optima locaux**; **aléatoire** interne influence le résultat.

**Conséquence** : un solveur complet (DPOP) et un heuristique (Max-Sum) peuvent **ne pas coïncider**.

---

## 2) Heuristiques, ordres et tie-breaking

* **Ordre des variables/facteurs** (pseudo-arbre DFS, ordering) modifie la **décomposition** et le **volume des messages** → peut changer la solution renvoyée en cas d’**ex-aequo**.
* **Ties (coûts ex æquo)** : certains solveurs choisissent la **première** valeur, d’autres la **plus petite** valeur, d’autres **aléatoirement**.
* **Seeds aléatoires** : si non fixés, deux runs donnent des solutions différentes.

---

## 3) Modélisation : même problème ?

* **`infinity` vs pénalité “Big‑M”** : si un solveur n’accepte pas `infinity` et que vous remplacez par `1e6`, il devient **possible** qu’une solution “interdite” soit choisie si elle **gagne** malgré la pénalité (ex. coûts cumulés > 1e6).
* **`defaultCost`** : en soft, tout tuple **non listé** prend `defaultCost`. Assurez‑vous que c’est bien **0** (ou la valeur voulue) des deux côtés.
* **Arity & scope** : l’**ordre** des variables dans `scope` doit correspondre à l’ordre des **valeurs** dans les tuples. Un décalage change le coût évalué.
* **Binarisation** d’une contrainte n‑aire : transformer un facteur n‑aire en somme de binaires **n’est pas équivalent** en général (perte d’information → solutions différentes).
* **Indices de domaine** : `1/2/3` doivent être cohérents avec la sémantique “voiture v1/v2/v3”.

---

## 4) Numérique & encodage

* **Entiers vs flottants** : arrondis différents → coûts totaux différents → tie‑breaking différent.
* **Échelle des coûts** : multiplier tous les coûts par 10 ne change pas l’optimum, mais peut changer le **comportement numérique** (saturation, seuils).

---

## 5) Cas DCOP concrets (FRODO)

* **Graphe montré “vide”** : FRODO n’affiche que les **binaires** sur le graphe; des facteurs **n‑aires** existent quand même.
* **Tous les passagers dans la même voiture** : si les facteurs de capacité (n‑aires K+1) **n’étaient pas présents** ou si la **capacité ≥ nb passagers**, la solution “tout chez v2” est **valide** et souvent **moins chère** (somme des unaires).
* **`infinity`** : s’il n’est pas supporté dans un pipeline, utilisez un **Big‑M** (ex. 1e6) *supérieur à toute somme de coûts plausible*.

---

## 6) Rendre les résultats reproductibles

1. **Fixer les seeds** aléatoires (`--seed` si dispo, sinon config solveur).
2. **Choisir un ordre déterministe** des variables/facteurs (DFS déterministe).
3. **Éviter les égalités** en ajoutant un **micro‑tiebreaker** (ε) : par ex. ajoutez `ε * j` au coût unaire de `y_j` (ε très petit) pour casser les ex‑æquo sans changer l’optimum réel.
4. **Unifier la modélisation** : mêmes domaines, mêmes tuples, mêmes `defaultCost` et même traitement de `infinity` (ou même `Big‑M`).
5. **Utiliser un solveur complet** (DPOP) comme **référence** pour vérifier l’optimum.

---

## 7) Check‑list de diagnostic rapide

* [ ] Les **XML** comparés sont **strictement identiques** (hors `name`).
* [ ] `maxConstraintArity` ≥ arité maximale réelle.
* [ ] Chaque **relation** a un **scope** correct et `arity` cohérent.
* [ ] **`defaultCost`** est celui attendu (souvent `0`).
* [ ] Les **facteurs n‑aires de capacité** sont bien présents (**tous** les sous‑ensembles K+1) et référencés.
* [ ] **`infinity`** supporté ? Sinon `Big‑M` suffisamment grand.
* [ ] **Seeds** et **ordres** fixés (si algo incomplet : nb d’itérations, damping, etc.).

---

## 8) Protocole expérimental recommandé

1. Vérifier l’**optimum** avec **DPOP** (ou un solveur centralisé exact) → coût de référence.
2. Lancer l’heuristique (Max‑Sum, MGM2…) avec **5–10 seeds** et reporter *meilleur, médian, écart type*.
3. Si divergence inexpliquée, exporter la **même instance** vers un format centralisé (ex. WCSP, MiniZinc) et comparer.

---

## 9) En cas d’égalité d’optima

* Deux solutions peuvent partager le **même coût total**. Selon le tie‑breaking, les solveurs peuvent retourner **des affectations différentes** mais **également optimales**. Ajoutez un **tiebreaker** si vous souhaitez une solution unique.

---

### En résumé

Des solutions différentes ne signifient pas forcément une erreur. Confirmez l’**équivalence de coût**, fixez les **seeds/ordres**, harmonisez la **modélisation** (`infinity`/`defaultCost`), et utilisez un **solveur complet** comme “gold standard” pour valider la qualité des autres.
