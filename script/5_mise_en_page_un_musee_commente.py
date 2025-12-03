"""
====================================================================
SECTION 1 — IMPORTS DES LIBRAIRIES QGIS & PYQT5

Ce bloc importe toutes les classes nécessaires pour :

- Créer et gérer un layout (mise en page) QGIS.
- Ajouter des éléments graphiques : carte, titre, légende, logos, etc.
- Manipuler les polices, tailles, couleurs, alignements.
- Définir les points, tailles, unités en millimètres dans la mise en page.

Ces importations sont indispensables au fonctionnement du script.
"""
from qgis.core import (
    QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemLegend, QgsLayoutItemScaleBar, QgsLayoutItemPicture,
    QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes
)
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtCore import Qt


"""
====================================================================
 — INITIALISATION DU LAYOUT

Cette section prépare la mise en page :

1. On récupère le projet QGIS actif.
2. On obtient le layoutManager qui gère toutes les mises en page.
3. On lit l’identifiant du musée.
4. On crée un nom unique pour la mise en page.
5. Si une mise en page existe avec ce nom, on la supprime.
6. On crée un nouveau layout vide qui servira de page A4.

"""
project = QgsProject.instance()
manager = project.layoutManager()

# --- Récupérer la valeur du champ identifiant_museofile ---
identifiant = musee["identifiant_museofile"]

# Sécurité si le champ est vide
if not identifiant:
    identifiant = "identifiant_inconnu"

# Construire le nom du layout SANS nettoyage
layoutName = f"Carte_musee_{identifiant}"

# Vérification de la non-existence d'un layout de même nom
layouts_list = manager.printLayouts()
for layout in layouts_list:
    if layout.name() == layoutName:
        manager.removeLayout(layout)
 
# Génération d'un layout vide
layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName(layoutName)
 
manager.addLayout(layout)

# Charger une carte vide
map = QgsLayoutItemMap(layout)
map.setRect(20, 20, 20, 20)
 
# Mettre un canvas basique
rectangle = QgsRectangle(1355502, -46398, 1734534, 137094)
map.setExtent(rectangle)
layout.addLayoutItem(map)

# Mettre finalement le canvas courant
canvas = iface.mapCanvas()
map.setExtent(canvas.extent())
 
layout.addLayoutItem(map)
 
# Redimensionner la carte
map.attemptMove(QgsLayoutPoint(3.217, 30.748, QgsUnitTypes.LayoutMillimeters))
map.attemptResize(QgsLayoutSize(177.323, 162.633, QgsUnitTypes.LayoutMillimeters))
 
map.setFrameEnabled(True)

#====================================================================
    # Légende personnalisée
tree_layers = project.layerTreeRoot().children()
checked_layers = [layer.name() for layer in tree_layers if layer.isVisible()]

layers_to_remove = [layer for layer in project.mapLayers().values() if layer.name() not in checked_layers]

legend = QgsLayoutItemLegend(layout)
legend.setTitle("")
legend.setLinkedMap(map)
layout.addLayoutItem(legend)
legend.attemptMove(QgsLayoutPoint(184.288, 30.598, QgsUnitTypes.LayoutMillimeters))

# Ne pas synchroniser avec le panneau de couches
legend.setAutoUpdateModel(False)

m = legend.model()
g = m.rootGroup()
for l in layers_to_remove:
    g.removeLayer(l)

# Masquer tous les noms de couches dans la légende (layout uniquement)

from qgis.core import QgsLegendRenderer, QgsLegendStyle

def hide_node_labels(node):
    # Appliquer le style "Hidden" à ce nœud
    QgsLegendRenderer.setNodeLegendStyle(node, QgsLegendStyle.Hidden)
    # Parcours récursif des enfants
    if hasattr(node, "children"):
        for child in node.children():
            hide_node_labels(child)

# Appliquer à tous les nœuds racine
for node in g.children():
    hide_node_labels(node)


# Ajuster la légende

legend.setColumnCount(2)   # 2 colonnes
legend.adjustBoxSize()

# Police et style
font_items = QFont("Arial", 8)
symbol_style = legend.style(QgsLegendStyle.SymbolLabel)
symbol_style.setFont(font_items)
legend.setStyle(QgsLegendStyle.SymbolLabel, symbol_style)

# Taille des symboles (mm)
legend.setSymbolWidth(3)
legend.setSymbolHeight(3)

# Mise à jour finale
legend.updateLegend()
iface.mapCanvas().refresh()

#====================================================================
# TITRE
# --- Recuperation du musee selectionne ---
layer_musees_disk = QgsProject.instance().mapLayersByName("Musees_Paris_4326")[0]
musee = next(layer_musees_disk.getFeatures(), None)

if musee is None:
    raise Exception("Aucun musee trouve.")

# Nom du musee correct
nom_musee = musee["nom_officiel_du_musee"]
nom_musee = nom_musee[0].upper() + nom_musee[1:]  # Mettre 1ère lettre en majuscule

# --- Titre dans la mise en page ---
title = QgsLayoutItemLabel(layout)
title.setText(nom_musee)  #  insertion dynamique du nom du musée
title.setFont(QFont("Verdana", 18))
title.adjustSizeToText()

layout.addLayoutItem(title)

title.attemptMove(QgsLayoutPoint(5, 4, QgsUnitTypes.LayoutMillimeters))

#====================================================================
#Texte d'information en dessous du titre
from PyQt5.QtCore import QDate
# Récupération des valeurs des champs
nom = musee['nom_officiel_du_musee']
date_appellation = musee['date_arrete_attribution_appellation']
adresse = musee['adresse']
code_postal = musee['code_postal']
commune = musee['commune']
tel = musee['telephone']
site = musee['url']

# Conversion de la date si nécessaire
date_str = ""
if date_appellation and isinstance(date_appellation, QDate):
    date_str = date_appellation.toString("dd/MM/yyyy")

# Construction du texte avec conditions pour ignorer les champs vides
texte = ""

if nom and date_appellation:
    texte += f"Le {nom} a obtenu l’appellation Musée de Paris le {date_str}.\n"

# Adresse complète
adresse_complete = " ".join(filter(None, [adresse, code_postal, commune]))
if adresse_complete:
    texte += f"Adresse : {adresse_complete}\n"

if tel:
    texte += f"Tél : {tel}\n"

if site:
    texte += f"Site web : {site}"

# Ajout dans le layout
TextCustom = QgsLayoutItemLabel(layout)
TextCustom.setText(texte)
TextCustom.setFont(QFont("Verdana", 7))


layout.addLayoutItem(TextCustom)
TextCustom.attemptResize(QgsLayoutSize(108.926, 15.738, QgsUnitTypes.LayoutMillimeters))
TextCustom.attemptMove(QgsLayoutPoint(5, 15.029, QgsUnitTypes.LayoutMillimeters))

#====================================================================
# Échelle
scalebar = QgsLayoutItemScaleBar(layout)
scalebar.setStyle('Single Box')
scalebar.setUnits(QgsUnitTypes.DistanceMeters)
scalebar.setNumberOfSegments(2)
scalebar.setNumberOfSegmentsLeft(0)
scalebar.setUnitsPerSegment(250)
scalebar.setLinkedMap(map)
scalebar.setUnitLabel('m')
scalebar.setFont(QFont('Verdana', 10))
scalebar.update()
 
layout.addLayoutItem(scalebar)
 
scalebar.attemptMove(QgsLayoutPoint(8.895, 174.230, QgsUnitTypes.LayoutMillimeters))

#====================================================================
# Logo

Logo = QgsLayoutItemPicture(layout)
Logo.setPicturePath("https://upload.wikimedia.org/wikipedia/commons/4/4e/Logo_label_mus%C3%A9e_de_France.svg")
Logo.attemptResize(QgsLayoutSize(40, 15, QgsUnitTypes.LayoutMillimeters))
Logo.attemptMove(QgsLayoutPoint(250, 4, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(Logo)

#====================================================================
# METTRE L'INFORMATION ISSUE DE WIKIPEDIA
from qgis.core import QgsLayoutMeasurement, QgsUnitTypes, QgsLayoutItemLabel
from qgis.PyQt.QtGui import QFont, QColor
from qgis.PyQt.QtCore import Qt

# --- Récupération du champ "information_musee" ---
# musee = l'entité du musée sélectionné dans la couche 
info = musee["information_musee"]

# Si le champ est NULL, éviter une erreur
if info is None:
    info = ""

# Création de l'item texte
TextCustom = QgsLayoutItemLabel(layout)
TextCustom.setText(info)
TextCustom.setFont(QFont("Verdana", 9))

# --- Ajouter un cadre autour du texte ---
TextCustom.setFrameEnabled(True)
TextCustom.setFrameStrokeWidth(QgsLayoutMeasurement(0.3))  # épaisseur du cadre
TextCustom.setFrameStrokeColor(QColor(0, 0, 0))             # couleur cadre

# --- Marges internes ---
TextCustom.setMarginX(3)
TextCustom.setMarginY(3)

# --- Justification ---
TextCustom.setHAlign(Qt.AlignJustify)

# Ajouter au layout
layout.addLayoutItem(TextCustom)

# Taille et position du bloc (à adapter selon la maquette)
TextCustom.attemptResize(QgsLayoutSize(108.395, 68.775, QgsUnitTypes.LayoutMillimeters))
TextCustom.attemptMove(QgsLayoutPoint(184.438, 124.775, QgsUnitTypes.LayoutMillimeters))

#====================================================================
# Signature de la carte et source
from PyQt5.QtCore import QDate
from PyQt5.QtGui import QFont

# Récupérer la date actuelle
from datetime import datetime
date_aujourdhui = datetime.now().strftime("%d/%m/%Y")

# Texte de signature
texte_signature = (
    f"Carte réalisée par Sewedo GNANSOUNOU le {date_aujourdhui}.\n"
    "Atlas des musées de Paris dotés de l'appellation 'Musée de France' au sens du Code du patrimoine.\n"
    "Source des données : Open Data Région Ile de France publié le 30 Avril 2025, https://data.iledefrance.fr"
)

# Créer un item texte pour la signature
signature_item = QgsLayoutItemLabel(layout)
signature_item.setText(texte_signature)
signature_item.setFont(QFont("Verdana", 7))
signature_item.setFrameEnabled(False)  # pas de cadre
signature_item.setHAlign(Qt.AlignLeft)  # alignement à gauche

# Positionner la signature en bas de la page (à adapter selon la taille du layout)
signature_item.attemptMove(QgsLayoutPoint(5, 200, QgsUnitTypes.LayoutMillimeters))  # X=5mm, Y=200mm
signature_item.attemptResize(QgsLayoutSize(200, 15, QgsUnitTypes.LayoutMillimeters))  # largeur=200mm, hauteur=15mm

# Ajouter au layout
layout.addLayoutItem(signature_item)

#====================================================================
#LOGO Master
Logomaster = QgsLayoutItemPicture(layout)
Logomaster.setPicturePath("https://upload.wikimedia.org/wikipedia/commons/c/cc/CY_Cergy_Paris_Universite_-_Logo.png")
Logomaster.attemptResize(QgsLayoutSize(36.561, 12.023, QgsUnitTypes.LayoutMillimeters))
Logomaster.attemptMove(QgsLayoutPoint(144.129, 195.477, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(Logomaster)


# ====================================================================
#        AJOUT DU NORD (SVG) AVEC ROTATION AUTOMATIQUE


# Ton chemin vers le fichier nord.svg
svg_path2 = os.path.join(monCheminDeBase, "icons", "nord.svg")

# Récupération de la rotation de la carte dans la mise en page
map_rotation = map.rotation()

# Création de l'item SVG
north_item = QgsLayoutItemPicture(layout)
north_item.setPicturePath(svg_path2)

# Taille du nord (en mm)
north_item.attemptResize(QgsLayoutSize(10, 10, QgsUnitTypes.LayoutMillimeters))

# Position (à ajuster selon besoin)
north_item.attemptMove(QgsLayoutPoint(7.802, 35.029, QgsUnitTypes.LayoutMillimeters))

# Appliquer la rotation du layout map
north_item.setRotation(-map_rotation)   # le signe - compense la rotation inverse de QGIS

# Ajouter l'item à la mise en page
layout.addLayoutItem(north_item)

print(" Nord ajouté et synchronisé avec la rotation de la carte.")

#====================================================================
# Mettre la carte de localisation
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsLayoutMeasurement
import os
from qgis.PyQt.QtGui import QPixmap

# --- Dossier où sont stockées les cartes de localisation ---
folder_localisation = os.path.join(monCheminDeBase, "localisation")  # le même que pour l'export

# --- Récupérer la valeur du champ identifiant_museofile ---
identifiant = musee["identifiant_museofile"]
if not identifiant:
    identifiant = f"musee_{musee.id()}"  # fallback

# --- Construire le chemin du fichier PNG ---
localisation_image = os.path.join(folder_localisation, f"{identifiant}.png")
# --- Vérifier si le fichier existe ---
if os.path.exists(localisation_image):
    Cartelocalisation = QgsLayoutItemPicture(layout)
    Cartelocalisation.setPicturePath(localisation_image)

    # Définir la taille et la position dans le layout principal
    Cartelocalisation.attemptResize(QgsLayoutSize(55.676, 40.733, QgsUnitTypes.LayoutMillimeters))
    Cartelocalisation.attemptMove(QgsLayoutPoint(125.014, 19.000, QgsUnitTypes.LayoutMillimeters))

    # -------- Ajouter un cadre --------
    Cartelocalisation.setFrameEnabled(True)                                 # active le cadre
    Cartelocalisation.setFrameStrokeColor(QColor(0, 0, 255))                # couleur bleue
    Cartelocalisation.setFrameStrokeWidth(QgsLayoutMeasurement(0.5))        # épaisseur en mm

    layout.addLayoutItem(Cartelocalisation)
    print(f" Carte de localisation ajoutée avec cadre pour {identifiant}")
else:
    print(f" Aucun fichier de localisation trouvé pour {identifiant}")


print(" Mise en page paysage utilisant la vue actuelle du canvas avec barre d'échelle et légende créée !")

#====================================================================
#Export_pdf
manager = QgsProject.instance().layoutManager()
layout = manager.layoutByName(layoutName)

if layout is None:
    raise Exception("La mise en page n'existe pas !")

exporter = QgsLayoutExporter(layout)

# Construire le chemin PDF correctement
pdf_path = os.path.join(monCheminDeBase, "cartes", f"{layoutName}.pdf")

pdf_settings = QgsLayoutExporter.PdfExportSettings()
pdf_settings.dpi = 300

result = exporter.exportToPdf(pdf_path, pdf_settings)

if result == QgsLayoutExporter.Success:
    print(" PDF exporté :", pdf_path)
else:
    print(" Erreur lors de l'export")


