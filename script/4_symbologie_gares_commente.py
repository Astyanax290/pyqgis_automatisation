"""
===========================================================
SCRIPT 4 — SYMBOLOGIE ISOCHRONES ET GARES (10 minutes)
===========================================================

Objectif général :
------------------
Ce script applique une symbologie avancée à la couche des gares
en distinguant :

1. Les gares situées DANS l’isochrone 10 minutes à pied du musée.
2. Les gares situées en DEHORS de l’isochrone.
3. Coloration unique (SVG + couleur palette) pour les gares à 10 min.
4. Points rouges pour les autres gares.
5. Ajout d’un champ "Accessible_10min" dans la couche des gares.
6. Labeling dynamique : n'afficher que le nom des gares accessibles
   à moins de 10 minutes.

Ce script repose sur :
- Une couche "Gares_dans_Paris"
- Une couche "Isochrones_musee_1" (générée par ORS)
- Une icône SVG personnalisée pour les gares accessibles
"""


#  SYMBOLOGIE DES GARES À 10 MIN 

"""
On importe toutes les classes nécessaires pour :
- les symboles SVG
- le renderer catégorisé
- la manipulation des couleurs
"""

from qgis.core import (
    QgsSvgMarkerSymbolLayer, QgsCategorizedSymbolRenderer, QgsRendererCategory,
    QgsMarkerSymbol, QgsVectorLayer, QgsSimpleMarkerSymbolLayer
)
from PyQt5.QtGui import QColor
import os

project = QgsProject.instance()  # récupérer le projet QGIS actif


"""
===========================================================
SECTION 1 — RÉCUPÉRATION DES COUCHES NÉCESSAIRES

On récupère la couche des gares filtrées dans Paris et la
couche des isochrones déjà générée par ORS.
"""

# Couche gares
layer_gares = project.mapLayersByName("Gares_dans_Paris")[0]

# Couche isochrone
layer_iso = project.mapLayersByName("Isochrones_musee_1")[0]


"""
===========================================================
SECTION 2 — PARAMÈTRES GÉNÉRAUX

On définit :
- le champ "value" des isochrones (300 = 5min, 600 = 10min)
- la valeur cible de 10 minutes
- le champ attributaire contenant le nom des gares
- le chemin vers l’icône SVG représentant une gare
"""

iso_field = "value"
iso_10_min = 600
gare_field = "nom_zda"
svg_path = os.path.join(monCheminDeBase, "icons", "railway.svg")

# Vérification présence de l’icône SVG
if not os.path.exists(svg_path):
    raise Exception(f" Le SVG est introuvable : {svg_path}")


"""
===========================================================
SECTION 3 — IDENTIFICATION DES GARES DANS L'ISOCHRONE 10 MIN

Objectif :
Trouver quelles gares se trouvent dans le polygone représentant
la zone accessible en 10 minutes depuis le musée.

Étapes :
1. Trouver dans la couche des isochrones le polygone (value=600).
2. Tester l’intersection géométrique avec chaque gare.
"""

#  1. Récupérer les gares dans l’isochrone 10 min

iso_geom = None
for f in layer_iso.getFeatures():
    if f[iso_field] == iso_10_min:
        iso_geom = f.geometry()
        break

if iso_geom is None:
    raise Exception(" Aucun polygone 10 min trouvé.")

gares_inside = []   # gares accessibles en 10 min
gares_outside = []  # les autres

for g in layer_gares.getFeatures():
    if g.geometry().intersects(iso_geom):
        gares_inside.append(g)
    else:
        gares_outside.append(g)

print(f" {len(gares_inside)} gares dans 10 min.")
print(f" {len(gares_outside)} gares hors 10 min.")

from qgis.core import QgsField
from PyQt5.QtCore import QVariant



"""
===========================================================
SECTION 4 — AJOUT DU CHAMP "Accessible_10min"

Ce champ est ajouté pour indiquer rapidement au sein de la couche :
- 'oui' = accessible en moins de 10 minutes
- 'non' = non accessible

Utilité :
- filtrage
- symbologie
- labeling
"""

#  Ajouter le champ Accesible_10min et le remplir


field_name = "Accesible_10min"

# Ajouter le champ s'il n'existe pas déjà
if field_name not in [f.name() for f in layer_gares.fields()]:
    layer_gares.dataProvider().addAttributes([QgsField(field_name, QVariant.String)])
    layer_gares.updateFields()

# Mise à jour des valeurs du champ
layer_gares.startEditing()
for feat in layer_gares.getFeatures():
    if feat.id() in [g.id() for g in gares_inside]:
        feat[field_name] = "oui"
    else:
        feat[field_name] = "non"
    layer_gares.updateFeature(feat)
layer_gares.commitChanges()

print(f" Champ '{field_name}' mis à jour : 'oui' pour les gares dans l’isochrone, 'non' sinon.")


"""
===========================================================
SECTION 5 — PALETTE DE COULEURS POUR LES GARES ACCESSIBLES

Palette ColorBrewer Set2 — idéale pour symboliser des catégories.
"""

#  2. Palette ColorBrewer Set2

ColorPalette = [
    QColor(102, 102, 204),   # bleu
    QColor(255, 153, 51),    # orange
    QColor(153, 51, 204),    # violet
    QColor(255, 204, 0),     # jaune doré
    QColor(51, 153, 204),    # cyan
    QColor(204, 102, 153),   # rose
    QColor(102, 153, 255),   # bleu clair
    QColor(204, 153, 51)     # marron clair
]


"""
===========================================================
SECTION 6 — CONSTRUCTION DU RENDERER CATÉGORISÉ

Deux groupes :
A → gares accessibles : symbole SVG + couleur palette
B → autres gares : point rouge simple
"""
#  3. Construire la symbologie catégorisée

categories = []

# --- 3A : Gares accessibles (SVG + couleurs uniques) ---
for i, feat in enumerate(gares_inside):
    nom = feat[gare_field]
    mode = feat["mode"]
    res = feat["res_com"]

    label = f"{nom} ({mode} – {res})"
    color = ColorPalette[i % len(ColorPalette)]  # cycle dans palette

    # Symbole SVG pour gare
    svg_layer = QgsSvgMarkerSymbolLayer(svg_path)
    svg_layer.setSize(5)

    symbol = QgsMarkerSymbol()
    symbol.changeSymbolLayer(0, svg_layer)
    symbol.setColor(color)

    cat = QgsRendererCategory(nom, symbol, label)
    categories.append(cat)

# --- 3B : Gares hors 10 min (point rouge) ---
symbol_red = QgsMarkerSymbol.createSimple({
    "name": "circle",
    "size": "2",
    "color": "red"
})

# Catégorie "None" → attrape toutes les autres valeurs
cat_red = QgsRendererCategory(None, symbol_red, "Autres gares (+ de 10 min)")
categories.append(cat_red)


"""
===========================================================
SECTION 7 — APPLICATION DU RENDERER À LA COUCHE
"""

#  4. Appliquer le renderer
renderer = QgsCategorizedSymbolRenderer(gare_field, categories)
layer_gares.setRenderer(renderer)
layer_gares.triggerRepaint()


"""
===========================================================
SECTION 8 — LABELING DYNAMIQUE DES GARES ACCESSIBLES

On affiche les étiquettes SEULEMENT pour les gares à moins
de 10 min.

Méthode :
- Labeling basé sur règles (RuleBasedLabeling)
- Placement intelligent autour des points
"""
#  Labeling uniquement pour les gares accessibles à 10 min

from qgis.core import Qgis

# Format du texte
text_format = QgsTextFormat()
text_format.setSize(10)
text_format.setColor(QColor("black"))

# Paramètres du labelling
pal_layer = QgsPalLayerSettings()
pal_layer.fieldName = "nom_zda"      # nom affiché
pal_layer.setFormat(text_format)

# Placement intelligent
pal_layer.placement = Qgis.LabelPlacement.OrderedPositionsAroundPoint

# Position possible autour des points
pal_layer.orderedPositions = [
    Qgis.LabelPredefinedPointPosition.TopLeft,
    Qgis.LabelPredefinedPointPosition.TopMiddle,
    Qgis.LabelPredefinedPointPosition.TopRight,
    Qgis.LabelPredefinedPointPosition.MiddleLeft,
    Qgis.LabelPredefinedPointPosition.MiddleRight,
    Qgis.LabelPredefinedPointPosition.BottomLeft,
    Qgis.LabelPredefinedPointPosition.BottomMiddle,
    Qgis.LabelPredefinedPointPosition.BottomRight
]

# Priorité du placement
pal_layer.prioritization = Qgis.LabelPrioritization.PreferPositionOrdering
pal_layer.dist = 3  # mm de décalage

# Règles de labeling
root_rule = QgsRuleBasedLabeling.Rule(None)

rule_10min = QgsRuleBasedLabeling.Rule(pal_layer)
rule_10min.setDescription("Gares accessibles 10 min")
rule_10min.setFilterExpression("\"Accesible_10min\" = 'oui'")
root_rule.appendChild(rule_10min)

rule_labeling = QgsRuleBasedLabeling(root_rule)

layer_gares.setLabeling(rule_labeling)
layer_gares.setLabelsEnabled(True)
layer_gares.triggerRepaint()

print(" Étiquettes positionnées autour des gares.")
