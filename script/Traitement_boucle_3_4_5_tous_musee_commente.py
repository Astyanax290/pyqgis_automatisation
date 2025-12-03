'''
#  SCRIPT GLOBAL POUR TRAITER TOUS LES MUSÉES AUTOMATIQUEMENT

Pour cela on a défini 3 fonctions:
1- Fonction : run_isochrone_for_one_museum(musee)
Cette fonction exécutera le script 3_isochrone.

2- Fonction : run_symbology_gares()
Elle exécute le script 4_symbologie_isochrone

3- Fonction : run_map_layout(musee)
Elle exécute le script 5_mise_en_page

Ce script permet d'itérer sur chaque musée
'''
from qgis.core import *
from PyQt5.QtGui import QColor
import requests, json, os
import os

project = QgsProject.instance()

# ------------------------------------------------------------
#  Paramètres globaux

layer_musees = project.mapLayersByName("Musees_Paris_4326")[0]
layer_gares = project.mapLayersByName("Gares_dans_Paris")[0]

# Sécurité
if layer_musees is None:
    raise Exception(" La couche des musées est introuvable !")

# CREATION DES FONCTIONS 

# ---------------------------------------------------------------------
#  FONCTION 1 : Calcul Isochrone pour un musée

def run_isochrone_for_one_museum(musee):
            

    import json

    # Calcul isochrone 1 musée
    ORS_API_KEY = ""
    ORS_URL = "https://api.openrouteservice.org/v2/isochrones/foot-walking"

    project = QgsProject.instance()

   
    #            SELECTION DU PREMIER MUSÉE
    
    layer_musees_disk = project.mapLayersByName("Musees_Paris_4326")[0]
    musee = musee

    if musee is None:
        raise Exception("Aucun musée trouvé dans la couche.")

    geom = musee.geometry()
    pt = geom.asPoint()
    lon, lat = pt.x(), pt.y()

    print(f" Musée sélectionné : {lon}, {lat}")
    
    #            ZOOM SUR LE MUSÉE SÉLECTIONNÉ
    
    iface.mapCanvas().setCenter(pt)          # centre la vue sur le musée
    iface.mapCanvas().zoomScale(10000.0)      # définit l'échelle approximative
    iface.mapCanvas().refresh()               # rafraîchit la vue
    print("🔍 Vue centrée sur le musée sélectionné à l'échelle 10000 ")

   
    #            PARAMÈTRES ISOCHRONES
    
    payload = {
        "locations": [[lon, lat]],
        "range": [300, 600],  # 5, 10 minutes
        "units": "m",
        "location_type": "start"
    }

    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }

    print("⏳ Envoi de la requête ORS (foot-walking)…")
    response = requests.post(ORS_URL, headers=headers, data=json.dumps(payload))

    if response.status_code != 200:
        raise Exception(" Erreur ORS : " + response.text)

    iso_data = response.json()

    
    #            SAUVEGARDE GEOJSON
    
    identifiant = musee["identifiant_museofile"]   # ou un autre identifiant unique
    iso_output_test = os.path.join(monCheminDeBase, "isochrones", f"Isochrones_{identifiant}.geojson")


    with open(iso_output_test, "w", encoding="utf-8") as f:
        json.dump(iso_data, f)

    print(" Isochrone test sauvegardé :", iso_output_test)

    
    #            CHARGEMENT DANS QGIS
   
    # Nom de la couche basé sur l'identifiant
    nom_couche_iso = f"Isochrones_{identifiant}"

    layer_iso_test = QgsVectorLayer(iso_output_test, nom_couche_iso, "ogr")
    project.addMapLayer(layer_iso_test)

    print(" Isochrones test (foot-walking) chargés dans QGIS.")


   
    #            SYMBOLOGIE : contours colorés selon catégorie
  
    colors = {
        300: QColor(102, 194, 165),  # 5 min - vert
        600: QColor(252, 141, 98),   # 10 min - orange
    }

    categories = []

    for value, color in colors.items():
        symbol = QgsFillSymbol.createSimple({
            'color': '0,0,0,0',  # pas de remplissage
            'outline_color': f'{color.red()},{color.green()},{color.blue()},255',
            'outline_width': '0.5'
        })
        cat = QgsRendererCategory(value, symbol, f"{value//60} min de marche du musée")
        categories.append(cat)

    renderer = QgsCategorizedSymbolRenderer("value", categories)
    layer_iso_test.setRenderer(renderer)
    layer_iso_test.triggerRepaint()

    print(" Symbologie contours appliquée avec catégories 5/10/15 min ")

   
    #            SYMBOLOGIE SVG POUR LE MUSÉE SÉLECTIONNÉ
    
    svg_path = os.path.join(monCheminDeBase, "icons", "museum1.svg") 
    svg_layer = QgsSvgMarkerSymbolLayer(svg_path)
    svg_layer.setSize(8)  # taille en mm

    symbol_musee_svg = QgsMarkerSymbol()
    symbol_musee_svg.changeSymbolLayer(0, svg_layer)

    # Symboles pour les autres musées
    symbol_other = QgsMarkerSymbol.createSimple({
        'name': 'circle',
        'color': '0,150,0',
        'outline_color': '0,80,0',
        'size': '3'
    })

    # Création du renderer basé sur règles
    root_rule = QgsRuleBasedRenderer.Rule(None)

    # Règle 1 : musée sélectionné basé sur l'identifiant
    identifiant_sel = musee["identifiant_museofile"]  # récupère l'identifiant unique
    rule_selected = QgsRuleBasedRenderer.Rule(symbol_musee_svg)
    rule_selected.setFilterExpression(f'"identifiant_museofile" = \'{identifiant_sel}\'')
    rule_selected.setLabel("Musée sélectionné")
    root_rule.appendChild(rule_selected)

    # Règle 2 : tous les autres musées
    rule_others = QgsRuleBasedRenderer.Rule(symbol_other)
    rule_others.setFilterExpression(f'"identifiant_museofile" != \'{identifiant_sel}\'')
    rule_others.setLabel("Autres musées")
    root_rule.appendChild(rule_others)

    # Appliquer le renderer
    renderer = QgsRuleBasedRenderer(root_rule)
    layer_musees_disk.setRenderer(renderer)
    layer_musees_disk.triggerRepaint()

    print(" Symbologie SVG appliquée uniquement au musée sélectionné (par identifiant_museofile) ")

    pass


    
# ---------------------------------------------------------------------
#  FONCTION 2 : Symbologie gares + croisement isochrone

def run_symbology_gares(nom_couche_iso):
    """
    Applique la symbologie sur les gares et marque celles dans l'isochrone 10 min
    nom_couche_iso : nom exact de la couche d'isochrone dans QGIS
    """
    project = QgsProject.instance()

    # Couche gares
    layer_gares_list = project.mapLayersByName("Gares_dans_Paris")
    if not layer_gares_list:
        raise Exception(" Couche 'Gares_dans_Paris' introuvable !")
    layer_gares = layer_gares_list[0]

    # Couche isochrone
    layer_iso_list = project.mapLayersByName(nom_couche_iso)
    if not layer_iso_list:
        raise Exception(f" Couche '{nom_couche_iso}' introuvable !")
    layer_iso = layer_iso_list[0]

    # --- paramètres ---
    iso_field = "value"
    iso_10_min = 600
    gare_field = "nom_zda"
    svg_path = os.path.join(monCheminDeBase, "icons", "railway.svg")

    if not os.path.exists(svg_path):
        raise Exception(f" Le SVG est introuvable : {svg_path}")

   
    # 1. Récupérer les gares dans l’isochrone 10 min
    
    iso_geom = None
    for f in layer_iso.getFeatures():
        if f[iso_field] == iso_10_min:
            iso_geom = f.geometry()
            break

    if iso_geom is None:
        raise Exception(" Aucun polygone 10 min trouvé dans la couche d'isochrone.")

    gares_inside = []
    gares_outside = []

    for g in layer_gares.getFeatures():
        if g.geometry().intersects(iso_geom):
            gares_inside.append(g)
        else:
            gares_outside.append(g)

    print(f" {len(gares_inside)} gares dans 10 min.")
    print(f" {len(gares_outside)} gares hors 10 min.")

   
    #  2. Ajouter le champ Accesible_10min et le remplir
    
    from qgis.core import QgsField
    from PyQt5.QtCore import QVariant

    field_name = "Accesible_10min"

    if field_name not in [f.name() for f in layer_gares.fields()]:
        layer_gares.dataProvider().addAttributes([QgsField(field_name, QVariant.String)])
        layer_gares.updateFields()

    layer_gares.startEditing()
    for feat in layer_gares.getFeatures():
        if feat.id() in [g.id() for g in gares_inside]:
            feat[field_name] = "oui"
        else:
            feat[field_name] = "non"
        layer_gares.updateFeature(feat)
    layer_gares.commitChanges()

    print(f" Champ '{field_name}' mis à jour : 'oui' pour les gares dans l’isochrone, 'non' sinon.")


    
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


   
    #  3. Construire la symbologie catégorisée
    
    categories = []

    # --- 3A : Gares dans l’isochrone → SVG + couleur unique ---
    for i, feat in enumerate(gares_inside):
        nom = feat[gare_field]
        mode = feat["mode"]
        res = feat["res_com"]

        label = f"{nom} ({mode} – {res})"
        color = ColorPalette[i % len(ColorPalette)]

        svg_layer = QgsSvgMarkerSymbolLayer(svg_path)
        svg_layer.setSize(5)

        symbol = QgsMarkerSymbol()
        symbol.changeSymbolLayer(0, svg_layer)
        symbol.setColor(color)

        cat = QgsRendererCategory(nom, symbol, label)
        categories.append(cat)

    # --- 3B : Autres gares → simple point rouge ---
    symbol_red = QgsMarkerSymbol.createSimple({
        "name": "circle",
        "size": "2",
        "color": "red"
    })

    # Catégorie "autres" basée sur une valeur absente (None)
    cat_red = QgsRendererCategory(None, symbol_red, "Autres gares (+ de 10 min)")
    categories.append(cat_red)

    
    #  4. Appliquer le renderer
    
    renderer = QgsCategorizedSymbolRenderer(gare_field, categories)
    layer_gares.setRenderer(renderer)
    layer_gares.triggerRepaint()


    
    #  Labeling uniquement pour les gares accessibles à 10 min
   
    from qgis.core import Qgis


    # Format du texte
    text_format = QgsTextFormat()
    text_format.setSize(10)
    text_format.setColor(QColor("black"))

    # Paramètres de labeling
    pal_layer = QgsPalLayerSettings()
    pal_layer.fieldName = "nom_zda"
    pal_layer.setFormat(text_format)

    # Placement → OrderedPositionsAroundPoint
    pal_layer.placement = Qgis.LabelPlacement.OrderedPositionsAroundPoint

    # Positions possibles autour du point
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

    # Priorisation
    pal_layer.prioritization = Qgis.LabelPrioritization.PreferPositionOrdering

    # Décalage
    pal_layer.dist = 3  # mm

    # Règles
    root_rule = QgsRuleBasedLabeling.Rule(None)

    rule_10min = QgsRuleBasedLabeling.Rule(pal_layer)
    rule_10min.setDescription("Gares accessibles 10 min")
    rule_10min.setFilterExpression("\"Accesible_10min\" = 'oui'")
    root_rule.appendChild(rule_10min)

    rule_labeling = QgsRuleBasedLabeling(root_rule)

    layer_gares.setLabeling(rule_labeling)
    layer_gares.setLabelsEnabled(True)
    layer_gares.triggerRepaint()

    print(" Étiquettes positionnées autour des gares (version compatible QGIS).")

    pass



# ---------------------------------------------------------------------
#  FONCTION 3 : Mise en page + export PDF

def run_map_layout(musee):
    #5
    from qgis.core import (
        QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
        QgsLayoutItemLegend, QgsLayoutItemScaleBar, QgsLayoutItemPicture,
        QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes
    )
    from PyQt5.QtGui import QFont, QFontMetrics
    from PyQt5.QtCore import Qt
    import os
    # Ajouter au début, avant toute manipulation de layout
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

    # Légende personnalisée
    tree_layers = project.layerTreeRoot().children()
    checked_layers = [layer.name() for layer in tree_layers if layer.isVisible()]

    layers_to_remove = [layer for layer in project.mapLayers().values() if layer.name() not in checked_layers]

    legend = QgsLayoutItemLegend(layout)
    legend.setTitle("")
    legend.setLinkedMap(map)
    layout.addLayoutItem(legend)
    legend.attemptMove(QgsLayoutPoint(184.288, 25.395, QgsUnitTypes.LayoutMillimeters))

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

    # -------------------------------
    # Ajuster la légende
    # -------------------------------
    legend.setColumnCount(1)   # 1 colonnes
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

    # Titre
    # --- Recuperation du musee selectionne ---
    layer_musees_disk = QgsProject.instance().mapLayersByName("Musees_Paris_4326")[0]
    musee = musee

    if musee is None:
        raise Exception("Aucun musee trouve.")

    # Nom du musee correct
    nom_musee = str(musee["nom_officiel_du_musee"]) if musee["nom_officiel_du_musee"] else "Nom inconnu"
    nom_musee = nom_musee[0].upper() + nom_musee[1:]  # Mettre 1ère lettre en majuscule

    # --- Titre dans la mise en page ---
    title = QgsLayoutItemLabel(layout)
    title.setText(nom_musee)  #  insertion dynamique du nom du musée
    title.setFont(QFont("Verdana", 14))
    title.adjustSizeToText()

    layout.addLayoutItem(title)

    title.attemptMove(QgsLayoutPoint(5, 4, QgsUnitTypes.LayoutMillimeters))


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


    # Échelle
    scalebar = QgsLayoutItemScaleBar(layout)
    scalebar.setStyle('Single Box')
    scalebar.setUnits(QgsUnitTypes.DistanceMeters)
    scalebar.setNumberOfSegments(2)
    scalebar.setNumberOfSegmentsLeft(0)
    scalebar.setUnitsPerSegment(250)
    scalebar.setLinkedMap(map)
    scalebar.setUnitLabel('m')
    scalebar.setFont(QFont('Verdana', 8))
    scalebar.update()
     
    layout.addLayoutItem(scalebar)
     
    scalebar.attemptMove(QgsLayoutPoint(8.895, 174.230, QgsUnitTypes.LayoutMillimeters))


    # Logo

    Logo = QgsLayoutItemPicture(layout)
    Logo.setPicturePath("https://upload.wikimedia.org/wikipedia/commons/4/4e/Logo_label_mus%C3%A9e_de_France.svg")
    Logo.attemptResize(QgsLayoutSize(40, 15, QgsUnitTypes.LayoutMillimeters))
    Logo.attemptMove(QgsLayoutPoint(250, 4, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(Logo)


    from qgis.core import QgsLayoutMeasurement, QgsUnitTypes, QgsLayoutItemLabel
    from qgis.PyQt.QtGui import QFont, QColor
    from qgis.PyQt.QtCore import Qt

    # --- Récupération du champ "information_musee" ---
    # musee = l'entité du musée sélectionné dans ta couche (déjà définie avant ce code)
    info = musee["information_musee"]
    info = str(info) if info else ""

    # Si le champ est NULL, éviter une erreur
    if info is None:
        info = ""

    # Création de l'item texte
    TextCustom = QgsLayoutItemLabel(layout)
    TextCustom.setText(info)
    TextCustom.setFont(QFont("Verdana", 8))

    # --- Ajouter un cadre autour du texte ---
    TextCustom.setFrameEnabled(True)
    TextCustom.setFrameStrokeWidth(QgsLayoutMeasurement(0.3))  # épaisseur du cadre
    TextCustom.setFrameStrokeColor(QColor(0, 0, 0))             # couleur cadre

    # --- Marges internes ---
    TextCustom.setMarginX(2)
    TextCustom.setMarginY(2)

    # --- Justification ---
    TextCustom.setHAlign(Qt.AlignJustify)

    # Ajouter au layout
    layout.addLayoutItem(TextCustom)

    # Taille et position du bloc (à adapter selon la maquette)
    TextCustom.attemptResize(QgsLayoutSize(108.395, 49.349, QgsUnitTypes.LayoutMillimeters))
    TextCustom.attemptMove(QgsLayoutPoint(184.438, 158, QgsUnitTypes.LayoutMillimeters))

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
    
    #LOGO Master
    Logomaster = QgsLayoutItemPicture(layout)
    Logomaster.setPicturePath("https://upload.wikimedia.org/wikipedia/commons/c/cc/CY_Cergy_Paris_Universite_-_Logo.png")
    Logomaster.attemptResize(QgsLayoutSize(36.561, 12.023, QgsUnitTypes.LayoutMillimeters))
    Logomaster.attemptMove(QgsLayoutPoint(144.129, 195.477, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(Logomaster)


   
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
    #Mettre la carte de localisation
    #Mettre la carte de localisation
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

    pass


# EXECUTION DES FONCTIONS

# =====================================================================
#  BOUCLE GÉNÉRALE : TRAITEMENT DE CHAQUE MUSÉE


total = layer_musees.featureCount()
print(f" Début du traitement automatique de {total} musées…")

for i, musee in enumerate(layer_musees.getFeatures(), start=1):

    nom = musee["nom_officiel_du_musee"]
    ident = musee["identifiant_museofile"]

    print("\n" + "="*70)
    print(f"  Musée {i}/{total} : {nom} (ID {ident})")
    print("="*70)

    # ------------------------------
    # 1️⃣ Calcul isochrone
    # ------------------------------
    print(" Étape 1 : calcul des isochrones…")
    run_isochrone_for_one_museum(musee)

    # ------------------------------
    # Définir le nom dynamique de la couche isochrone
    # ------------------------------
    nom_couche_iso = f"Isochrones_{ident}"

    # ------------------------------
    # 2️⃣ Symbologie gares
    # ------------------------------
    print(" Étape 2 : symbologie et analyse des gares…")
    run_symbology_gares(nom_couche_iso)

    # ------------------------------
    # 3️⃣ Mise en page + PDF
    # ------------------------------
    print(" Étape 3 : création du layout + export PDF…")
    run_map_layout(musee)

    # ------------------------------
    # 4️⃣ Supprimer la couche d'isochrones et le fichier GeoJSON
    # ------------------------------

    # 1. Supprimer la couche si elle existe
    iso_layer = project.mapLayersByName(nom_couche_iso)
    if iso_layer:
        iso_layer = iso_layer[0]
        QgsProject.instance().removeMapLayer(iso_layer.id())
        print(f" Couche d'isochrones supprimée : {nom_couche_iso}")

    # 2. Attendre la libération du fichier GeoJSON
    import time
    time.sleep(0.5)


print(" Tous les musées ont été traités !")
