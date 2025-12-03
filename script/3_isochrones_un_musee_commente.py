"""
===========================================================
SECTION 1 — IMPORTS ET CONFIGURATION API OPENROUTESERVICE
===========================================================
Ce script génère des isochrones (zones accessibles à pied en
5 et 10 minutes) autour d’un musée sélectionné.

Objectifs :
- Sélectionner automatiquement le 1er musée de la couche
- Appeler l’API OpenRouteService pour les isochrones
- Stocker les résultats en GeoJSON
- Charger et styliser la couche dans QGIS
- Mettre en évidence le musée sélectionné avec un symbole SVG

Ce script nécessite :
- Une clé OpenRouteService valide. Merci de mettre votre clé dans ORS_API_KEY = ""
- La couche "Musees_Paris_4326" chargée dans le projet QGIS
"""

import json  # Pour convertir données → JSON ou écrire des fichiers

# API ORS : clé personnelle + endpoint pour les isochrones piétons
ORS_API_KEY = ""
ORS_URL = "https://api.openrouteservice.org/v2/isochrones/foot-walking"

# Récupération du projet QGIS en cours
project = QgsProject.instance()

"""
===========================================================
SECTION 2 — SÉLECTION DU PREMIER MUSÉE DANS LA COUCHE

Ici, on récupère la couche des musées, puis on sélectionne
automatiquement le premier musée (feature 0).
"""
#            SELECTION DU PREMIER MUSÉE
layer_musees_disk = project.mapLayersByName("Musees_Paris_4326")[0]

# next(...) permet de récupérer la première entité du layer
musee = next(layer_musees_disk.getFeatures(), None)

if musee is None:
    raise Exception("Aucun musée trouvé dans la couche.")

# Extraction des coordonnées du musée sélectionné
geom = musee.geometry()
pt = geom.asPoint()
lon, lat = pt.x(), pt.y()   # ORS attend lon/lat (ordre important)

print(f" Musée sélectionné : {lon}, {lat}")


"""
===========================================================
SECTION 3 — ZOOM AUTOMATIQUE SUR LE MUSÉE

On centre la carte QGIS sur les coordonnées du musée sélectionné
pour visualiser correctement les résultats.
"""

#            ZOOM SUR LE MUSÉE SÉLECTIONNÉ


iface.mapCanvas().setCenter(pt)          # centre la vue
iface.mapCanvas().zoomScale(10000.0)     # échelle approx. 1:10 000
iface.mapCanvas().refresh()              # mise à jour du rendu
print("🔍 Vue centrée sur le musée sélectionné à l'échelle 10000 ")


"""
===========================================================
SECTION 4 — CONSTRUCTION DU PAYLOAD POUR ORS

On prépare :
- la position de départ
- les distances max accessibles (300 m, 600 m)
- le type de déplacement (“foot-walking”)
"""

#            PARAMÈTRES ISOCHRONES
payload = {
    "locations": [[lon, lat]],   # toujours lon, lat !
    "range": [300, 600],         # 5 min (300s), 10 min (600s)
    "units": "m",
    "location_type": "start"     # point de départ
}

headers = {
    "Authorization": ORS_API_KEY,     # clé API obligatoire
    "Content-Type": "application/json"
}

print(" Envoi de la requête ORS (foot-walking)…")

# Envoi de la requête POST à OpenRouteService
response = requests.post(ORS_URL, headers=headers, data=json.dumps(payload))

if response.status_code != 200:
    raise Exception(" Erreur ORS : " + response.text)

# Données GeoJSON reçues
iso_data = response.json()


"""
===========================================================
SECTION 5 — SAUVEGARDE DES ISOCHRONES EN GEOJSON

On crée un fichier GeoJSON pour rendre les isochrones persistants,
et pouvoir les recharger, analyser, styliser ou exporter.
"""
#            SAUVEGARDE GEOJSON

iso_output_test = os.path.join(monCheminDeBase, "isochrones", "Isochrones_musee_1.geojson")

# Écriture du fichier GeoJSON
with open(iso_output_test, "w", encoding="utf-8") as f:
    json.dump(iso_data, f)

print(" Isochrone test sauvegardé :", iso_output_test)

"""
===========================================================
SECTION 6 — CHARGEMENT DU GEOJSON DANS QGIS

On recharge les résultats pour les afficher, manipuler et styliser.
"""
#            CHARGEMENT DANS QGIS
layer_iso_test = QgsVectorLayer(iso_output_test, "Isochrones_musee_1", "ogr")
project.addMapLayer(layer_iso_test)

print(" Isochrones test (foot-walking) chargés dans QGIS.")


"""
===========================================================
SECTION 7 — SYMBOLOGIE CATÉGORISÉE DES ISOCHRONES

Objectif : afficher les isochrones par tranche de temps :
- 5 min (vert)
- 10 min (orange)

On utilise un renderer catégorisé.
"""

#            SYMBOLOGIE : contours colorés selon catégorie
colors = {
    300: QColor(102, 194, 165),  # vert clair – 5 min
    600: QColor(252, 141, 98),   # orange – 10 min
}

categories = []

for value, color in colors.items():
    # Symbole sans remplissage, uniquement contour coloré
    symbol = QgsFillSymbol.createSimple({
        'color': '0,0,0,0',
        'outline_color': f'{color.red()},{color.green()},{color.blue()},255',
        'outline_width': '0.5'
    })

    # Une catégorie par durée (5 ou 10 min)
    cat = QgsRendererCategory(value, symbol, f"{value//60} min de marche du musée")
    categories.append(cat)

# Application d’un renderer catégorisé sur le champ "value"
renderer = QgsCategorizedSymbolRenderer("value", categories)
layer_iso_test.setRenderer(renderer)
layer_iso_test.triggerRepaint()

print(" Symbologie contours appliquée avec catégories 5/10 min ")


"""
===========================================================
SECTION 8 — SYMBOLOGIE AVANCÉE : SVG POUR LE MUSÉE

Objectif :
- Mettre un symbole SVG sur le musée sélectionné
- Laisser les autres musées avec un symbole simple

Méthode :
→ Renderer basé sur des règles (RuleBasedRenderer)
"""


#            SYMBOLOGIE SVG POUR LE MUSÉE SÉLECTIONNÉ


svg_path = os.path.join(monCheminDeBase, "icons", "museum1.svg")  # chemin vers icône SVG
svg_layer = QgsSvgMarkerSymbolLayer(svg_path)
svg_layer.setSize(8)  # taille en mm

# Symbole personnalisé basé sur SVG
symbol_musee_svg = QgsMarkerSymbol()
symbol_musee_svg.changeSymbolLayer(0, svg_layer)

# Symbole par défaut pour les autres musées
symbol_other = QgsMarkerSymbol.createSimple({
    'name': 'circle',
    'color': '0,150,0',
    'outline_color': '0,80,0',
    'size': '3'
})

# Création du renderer par règles
root_rule = QgsRuleBasedRenderer.Rule(None)

# Récupération identifiant unique du musée sélectionné
identifiant_sel = musee["identifiant_museofile"]

# Règle 1 : musée sélectionné → symbole SVG
rule_selected = QgsRuleBasedRenderer.Rule(symbol_musee_svg)
rule_selected.setFilterExpression(f'"identifiant_museofile" = \'{identifiant_sel}\'')
rule_selected.setLabel("Musée sélectionné")
root_rule.appendChild(rule_selected)

# Règle 2 : autres musées → symbole simple
rule_others = QgsRuleBasedRenderer.Rule(symbol_other)
rule_others.setFilterExpression(f'"identifiant_museofile" != \'{identifiant_sel}\'')
rule_others.setLabel("Autres musées")
root_rule.appendChild(rule_others)

# Application du renderer
renderer = QgsRuleBasedRenderer(root_rule)
layer_musees_disk.setRenderer(renderer)
layer_musees_disk.triggerRepaint()

print(" Symbologie SVG appliquée uniquement au musée sélectionné (par identifiant_museofile) ")
