"""
SECTION 1 — IMPORT DES MODULES ET CONFIGURATION DE BASE
===========================================================
Cette section importe l’ensemble des modules Python et QGIS
nécessaires pour :
- interroger une API (requests)
- manipuler les couches QGIS (QgsVectorLayer, QgsFeature…)
- gérer les symboles (QgsMarkerSymbol…)
- lancer les algorithmes Processing
- définir un dossier de travail

C’est la fondation du script.
"""

import requests  # Pour faire des requêtes HTTP vers l’API
import os        # Pour gérer les chemins de fichiers
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsField, QgsFeature,
    QgsGeometry, QgsPointXY, QgsCoordinateReferenceSystem,
    QgsFillSymbol, QgsMarkerSymbol
)
from PyQt5.QtCore import QVariant  # Type de données des champs
import processing  # Accès aux algorithmes QGIS Processing


# ---------------------------------------------------------
#            DÉFINITION DU RÉPERTOIRE DE SORTIE
"""
Ici, on définit le chemin de base où seront stockés les fichiers
générés : couches, exports PNG, etc.
                    Veuillez à l'adapter___
"""
monCheminDeBase = r'C:\Users\sewed\Music\Program_av\MUZ\\'


# ---------------------------------------------------------
#            RÉINITIALISATION DU PROJET QGIS
"""
On réinitialise complètement le projet QGIS :
- suppression des couches
- suppression des paramètres internes
- définition du système de coordonnées (EPSG:2154 – Lambert 93)

Cela permet de travailler sur une base propre.
"""

project = QgsProject.instance()     # Récupération du projet QGIS en cours
project.removeAllMapLayers()        # Supprime toutes les couches
project.clear()                     # Nettoie l’état interne du projet
project.setCrs(QgsCoordinateReferenceSystem("EPSG:2154"))  # CRS du projet
print("Projet QGIS réinitialisé et CRS défini (EPSG:2154).")



"""
===========================================================
SECTION 2 — CHARGEMENT DU FOND DE PLAN POSITRON

On charge une couche XYZ (fond de carte CartoDB Positron)
sous forme de tuile web. Cela sert de base visuelle.
"""
#            FOND DE PLAN POSITRON AVEC LABELS

urlWithParams = "type=xyz&url=https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
positron = QgsRasterLayer(urlWithParams, "CartoDB Positron (labels)", "wms")

# Vérification que le fond s'est chargé correctement
if positron.isValid():
    project.addMapLayer(positron)
    print(" Fond de carte Positron (avec labels) chargé.")
else:
    print(" Impossible de charger le fond de carte Positron.")



"""
===========================================================
SECTION 3 — RÉCUPÉRATION DES DONNÉES API (MUSÉES)

Cette partie interroge l’API Île-de-France pour récupérer
les musées situés à Paris. 
"""

#            RÉCUPÉRATION DES DONNÉES PAR API

api_url = (
    "https://data.iledefrance.fr/api/explore/v2.1/catalog/datasets/"
    "liste_des_musees_franciliens/records?select=*&where=commune%3D%20%22Paris%22&limit=100"
)

response = requests.get(api_url)   # Envoi de requête API
if response.status_code != 200:    # Vérification réponse API
    raise Exception("Erreur lors de la récupération des données API.")

data = response.json()             # Conversion JSON → Python
records = data.get("results", [])  # Extraction des résultats
if not records:
    raise Exception("Aucune donnée trouvée dans 'results'.")

print(f" Données API récupérées : {len(records)} enregistrements trouvés.")



"""
===========================================================
SECTION 4 — CRÉATION D’UNE COUCHE MÉMOIRE (MUSÉES)

On crée une couche temporaire (memory layer) en WGS84 qui
contiendra tous les musées récupérés depuis l’API.
"""
#            CRÉATION DE LA COUCHE MÉMOIRE WGS84

layer = QgsVectorLayer("Point?crs=EPSG:4326", "Musees_Paris", "memory")
provider = layer.dataProvider()  # Fournisseur permettant d'ajouter champs/features

# Extraction de tous les champs existants dans l’API
all_fields = set()
for rec in records:
    all_fields.update(rec.keys())  # On collecte tous les noms de champs

# Création des champs dans QGIS
fields = [QgsField(f, QVariant.String) for f in sorted(all_fields)]
provider.addAttributes(fields)
layer.updateFields()

print(" Couche mémoire WGS84 créée avec tous les champs de l’API.")



"""
===========================================================
SECTION 5 — CRÉATION DES FEATURES MUSÉES

On crée chaque point (lon/lat) et on remplit les attributs.
"""
#            CRÉATION DES FEATURES

for rec in records:
    geo = rec.get("geolocalisation")
    if not geo:  # Pas de coord. → on ignore
        continue

    lon = geo.get("lon")
    lat = geo.get("lat")
    if lon is None or lat is None:
        continue

    feat = QgsFeature()  # nouvelle entité
    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(lon), float(lat))))

    # Création liste des valeurs d’attributs dans l'ordre des champs
    attr = [str(rec.get(f.name(), "")) for f in layer.fields()]
    feat.setAttributes(attr)

    provider.addFeature(feat)

layer.updateExtents()  # Mise à jour étendue de la couche pour zoom


"""
===========================================================
SECTION 6 — SAUVEGARDE ET RECHARGEMENT DE LA COUCHE MUSÉES

On enregistre la couche mémoire en GeoJSON, puis on la recharge dans QGIS.
"""
#         SAUVEGARDE EN DISQUE DU COUCHE MUSEES

output_musees = os.path.join(monCheminDeBase, "Musees_Paris_4326.geojson")

processing.run("native:savefeatures", {
    'INPUT': layer,
    'OUTPUT': output_musees
})

print(" Couche Musees_Paris sauvegardée :", output_musees)

#        RECHARGEMENT DANS QGIS

layer_musees_disk = QgsVectorLayer(output_musees, "Musees_Paris_4326", "ogr")
project.addMapLayer(layer_musees_disk)

print("Couche Musees_Paris_4326 chargée depuis le disque.")


"""
===========================================================
SECTION 7 — SYMBOLOGIE DES MUSÉES

On applique une symbologie simple : un cercle vert.
"""

# ---------------------------------------------------------
#            SYMBOLOGIE MUSÉES (VERT) 
# ---------------------------------------------------------

symbol_musees = QgsMarkerSymbol.createSimple({
    'name': 'circle',
    'color': '0,150,0',
    'outline_color': '0,80,0',
    'size': '3'
})

layer_musees_disk.setRenderer(QgsSingleSymbolRenderer(symbol_musees))
layer_musees_disk.triggerRepaint()

print(" Symbologie verte appliquée aux musées.")


"""
===========================================================
SECTION 8 — CHARGEMENT DE LA COUCHE PARIS

On charge Paris.geojson pour délimiter la zone de travail.
"""

#       CHARGEMENT DE LA COMMUNE DE PARIS (GeoJSON)

chemin_paris = os.path.join(monCheminDeBase, "Paris.geojson")
layer_paris = QgsVectorLayer(chemin_paris, "Paris", "ogr")
if not layer_paris.isValid():
    raise Exception("Impossible de charger Paris.geojson")

project.addMapLayer(layer_paris)
print("Couche Paris.geojson chargée.")

#       SYMBOLOGIE SANS REMPLISSAGE

symbol = QgsFillSymbol.createSimple({
    'color': '0,0,0,0',
    'outline_color': '0,0,0,255',
    'outline_width': '0.8'
})
layer_paris.renderer().setSymbol(symbol)
layer_paris.triggerRepaint()
print("Symbologie 'sans remplissage' appliquée à la couche Paris.")


"""
===========================================================
SECTION 9 — GÉNÉRATION DES CARTES DE LOCALISATION A6

Cette section génère une carte A6 centrée sur Paris
pour chacun des musées.
Chaque carte est exportée en PNG à 300 dpi.
"""

#     GÉNÉRATION DES CARTES DE LOCALISATION A6 CENTRÉES


print("\n🗺️ DÉBUT DE LA GÉNÉRATION DES CARTES DE LOCALISATION (A6)\n")

from qgis.core import (
    QgsLayoutItemMap, QgsLayoutExporter, QgsPrintLayout,
    QgsLayoutItemPage, QgsLayoutSize, QgsUnitTypes, QgsLayoutPoint,
    QgsProject
)
from qgis.PyQt.QtGui import QColor
from qgis.utils import iface
import os

# Dossier de sortie
folder_localisation = os.path.join(monCheminDeBase, "localisation")
os.makedirs(folder_localisation, exist_ok=True)

# Récupérer les couches
project = QgsProject.instance()
layer_paris = project.mapLayersByName("Paris")[0]
layer_musees = project.mapLayersByName("Musees_Paris_4326")[0]
manager = project.layoutManager()

# -------- Centrer et zoomer sur Paris dans le canvas --------
layer_paris.selectAll()
iface.mapCanvas().zoomToSelected(layer_paris)
layer_paris.removeSelection()  # ne pas garder la sélection

# -------- Définition taille page A6 paysage --------
page_width = 148
page_height = 105

# Parcours de chaque musée
for musee in layer_musees.getFeatures():

    ident = musee["identifiant_museofile"]
    if not ident:
        ident = f"musee_{musee.id()}"

    print(f"➡ Génération de la carte pour : {ident}")

    # -------- Afficher uniquement CE musée --------
    layer_musees.setSubsetString(f'"fid" = {musee.id()}')

    # -------- Layout : suppression ancienne version --------
    layout_name = f"Localisation_{ident}"
    for l in manager.printLayouts():
        if l.name() == layout_name:
            manager.removeLayout(l)

    # -------- Création du layout A6 paysage --------
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(layout_name)
    manager.addLayout(layout)

    page = QgsLayoutItemPage(layout)
    page.setPageSize(QgsLayoutSize(page_width, page_height, QgsUnitTypes.LayoutMillimeters))
    pc = layout.pageCollection()
    pc.clear()
    pc.addPage(page)

    # -------- Dimensions carte --------
    map_width = 146.15
    map_height = 101.15

    # Calcul du coin supérieur gauche pour centrer la carte
    x_pos = (page_width - map_width) / 2
    y_pos = (page_height - map_height) / 2

    # -------- Ajout de la carte --------
    map_item = QgsLayoutItemMap(layout)
    map_item.attemptMove(QgsLayoutPoint(x_pos, y_pos, QgsUnitTypes.LayoutMillimeters))
    map_item.attemptResize(QgsLayoutSize(map_width, map_height, QgsUnitTypes.LayoutMillimeters))

    # -------- Étendue basée sur le canvas QGIS (Paris centré) --------
    current_extent = iface.mapCanvas().extent()
    map_item.setExtent(current_extent)
    map_item.refresh()
    layout.addLayoutItem(map_item)

    # -------- Optionnel : cadre autour de la carte --------
    # map_item.setFrameEnabled(True)
    # map_item.setFrameStrokeColor(QColor(0,0,255))
    # from qgis.core import QgsLayoutMeasurement
    # map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.5))

    # -------- Export PNG --------
    output_path = os.path.join(folder_localisation, f"{ident}.png")
    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.ImageExportSettings()
    settings.dpi = 300

    result = exporter.exportToImage(output_path, settings)

    if result == QgsLayoutExporter.Success:
        print(f"    Carte exportée : {output_path}")
    else:
        print(f"    Erreur d’export pour : {ident}")

# -------- Réafficher tous les musées --------
layer_musees.setSubsetString("")

print("\n FIN : Toutes les cartes de localisation A6 ont été générées et centrées !")


"""
===========================================================
SECTION 10 — CHARGEMENT ET TRAITEMENT DES GARES

On charge les gares, on les masque, puis on extrait celles
situées dans Paris.
"""
#             CHARGEMENT DES GARES 4326 (GPKG)

chemin_gares = os.path.join(monCheminDeBase, "Gares_4326.gpkg")
layer_gares = QgsVectorLayer(chemin_gares, "Gares_4326", "ogr")
if not layer_gares.isValid():
    raise Exception("Impossible de charger Gares_4326.gpkg")

project.addMapLayer(layer_gares)
print(" Couche Gares_4326.gpkg chargée (masquée dans le projet).")

# Masquer la couche Gares dans le panneau de couches
root = QgsProject.instance().layerTreeRoot()
node = root.findLayer(layer_gares.id())
if node:
    node.setItemVisibilityChecked(False)
    print(" La couche 'Gares_4326' est masquée dans le panneau des couches.")


"""
===========================================================
SECTION 11 — EXTRACTION DES GARES DANS PARIS

On utilise Processing → extractByLocation pour récupérer
uniquement les gares intersectant Paris.
"""
#             EXTRACTION DES GARES DANS PARIS

output_gares_paris = os.path.join(monCheminDeBase, "Gares_dans_Paris_4326.gpkg")

processing.run("native:extractbylocation", {
    'INPUT': layer_gares,
    'PREDICATE': 0,
    'INTERSECT': layer_paris,
    'OUTPUT': output_gares_paris
})

layer_final = QgsVectorLayer(output_gares_paris, "Gares_dans_Paris", "ogr")
if not layer_final.isValid():
    raise Exception("Impossible de charger la couche finale Gares_dans_Paris.")

project.addMapLayer(layer_final)

print(" Extraction des gares intersectant Paris terminée.")
print(" Fichier final :", output_gares_paris)


"""
===========================================================
SECTION 12 — SYMBOLOGIE DES GARES

On affiche les gares en rouge.
"""
#            SYMBOLOGIE GARES (ROUGE) 

symbol_gares = QgsMarkerSymbol.createSimple({
    'name': 'circle',
    'color': '200,0,0',
    'outline_color': '120,0,0',
    'size': '2'
})

layer_final.setRenderer(QgsSingleSymbolRenderer(symbol_gares))
layer_final.triggerRepaint()

print(" Symbologie rouge appliquée aux gares.")

# Actualiser l’affichage
iface.mapCanvas().refresh()
print(" Actualisation du projet terminée.")


"""

SECTION 13 — CHANGEMENT DE CRS DU PROJET 
===========================================================
On remet le projet en WGS84 à la fin. Utile car la suite du
travail doit être en lat/lon.
"""

from qgis.core import QgsCoordinateReferenceSystem, QgsProject

project = QgsProject.instance()
crs_4326 = QgsCoordinateReferenceSystem("EPSG:4326")
project.setCrs(crs_4326)
print(" Projet passé en EPSG:4326")
