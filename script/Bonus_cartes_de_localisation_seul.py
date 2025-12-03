# ---------------------------------------------------------
#     📌 GÉNÉRATION DES CARTES DE LOCALISATION A6 CENTRÉES
# ---------------------------------------------------------
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
    # Décommente ces lignes si tu veux un cadre bleu autour de la carte
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
        print(f"   ✔ Carte exportée : {output_path}")
    else:
        print(f"   ❌ Erreur d’export pour : {ident}")

# -------- Réafficher tous les musées --------
layer_musees.setSubsetString("")

print("\n🎉 FIN : Toutes les cartes de localisation A6 ont été générées et centrées !")



#fin carte localisation


