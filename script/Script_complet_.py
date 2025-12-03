"""
Ce script a été réalisé par SEWEDO GNANSOUNOU, étudiant en master Géomatique CY Cergy Paris Université
@ Décembre 2025

N'oubliez pas de définir votre répertoire de travail à la ligne 40
et la clé ORS_API_KEY =    à la ligne 1008


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

#_____________________________________________________________________________________________________________________________________________________________
# Import des librairies

import requests
from html.parser import HTMLParser
from urllib.parse import urljoin
from qgis.core import (
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsFields,
    QgsWkbTypes,
    QgsProject,
    QgsVectorFileWriter
)
from PyQt5.QtCore import QVariant
import os


# ------------------------------
# 1) Scraper l'url des musées de Paris dans la section dédié sur la page https://fr.wikipedia.org/wiki/Mus%C3%A9e_de_France 


class ParisMuseumsParser(HTMLParser):
    in_paris_section = False
    in_colonnes_div = False
    in_li = False
    current_href = None
    current_text = ""
    museums = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "h4" and attrs.get("id") == "Paris":
            self.in_paris_section = True

        if self.in_paris_section and tag == "div" and attrs.get("class") == "colonnes":
            self.in_colonnes_div = True

        if self.in_colonnes_div and tag == "li":
            self.in_li = True

        if self.in_li and tag == "a":
            self.current_href = attrs.get("href", "")
            self.current_text = ""

    def handle_endtag(self, tag):
        if tag == "li" and self.in_li:
            self.in_li = False

        if tag == "div" and self.in_colonnes_div:
            self.in_colonnes_div = False
            self.in_paris_section = False

        if tag == "a" and self.current_href:
            if self.current_text:
                self.museums.append({
                    "nom": self.current_text,
                    "url": urljoin(BASE, self.current_href)
                })
            self.current_href = None
            self.current_text = ""

    def handle_data(self, data):
        if self.in_li and self.current_href:
            self.current_text += data.strip()


URL = "https://fr.wikipedia.org/wiki/Mus%C3%A9e_de_France"
BASE = "https://fr.wikipedia.org"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

response = requests.get(URL, headers=headers)
response.raise_for_status()

parser = ParisMuseumsParser()
parser.feed(response.text)

musees = parser.museums

print("Musées trouvés :", len(musees))


# ------------------------------
# 2) Enregistrement CSV


csv_path = os.path.join(monCheminDeBase, "Musees_Paris_Scrapping.csv")

fields = QgsFields()
fields.append(QgsField("nom", QVariant.String))
fields.append(QgsField("url", QVariant.String))

writer = QgsVectorFileWriter(
    csv_path,
    "UTF-8",
    fields,
    QgsWkbTypes.NoGeometry,
    driverName="CSV",
    layerOptions=["DELIMITER=,", "QUOTE_ALL=YES"]   # IMPORTANT pour CSV standard
)

for m in musees:
    feat = QgsFeature()
    feat.setFields(fields)
    feat["nom"] = m["nom"]
    feat["url"] = m["url"]
    writer.addFeature(feat)

del writer

print("CSV enregistré :", csv_path)


# ------------------------------
# 3) Chargement du csv dans QGIS


uri = f"file:///{csv_path}?delimiter=,&detectTypes=yes&decimalPoint=.&quote=\""

layer = QgsVectorLayer(uri, "Musees_Paris_Scrapping", "delimitedtext")

if layer.isValid():
    QgsProject.instance().addMapLayer(layer)
    print("Couche ajoutée :", layer.name())
else:
    print(" ERREUR : impossible de charger le CSV dans QGIS.")




# Jointure 1 entre le csv et la couche des musées

from PyQt5.QtCore import QVariant
from qgis.core import QgsField, QgsProject
import re
import difflib

# Récupération des couches
layer_musees = QgsProject.instance().mapLayersByName("Musees_Paris_4326")[0]
layer_csv = QgsProject.instance().mapLayersByName("Musees_Paris_Scrapping")[0]

# Extraction du CSV (IMPORTANT : NE PAS TOUCHER À L’URL)
scrap_data = []
for f in layer_csv.getFeatures():
    nom_scrap = f["nom"]
    url_scrap_original = f["url"]              # URL EXACTE
    url_scrap_clean = url_scrap_original.lower() if url_scrap_original else ""  # uniquement pour comparaison

    if nom_scrap:
        scrap_data.append({
            "nom": nom_scrap.lower().strip(),
            "tokens": set(re.findall(r'\w+', nom_scrap.lower())),
            "url_original": url_scrap_original,     # URL CONSERVÉE
            "url_clean": url_scrap_clean            # version pour comparaison
        })

# Ajout des champs
prov = layer_musees.dataProvider()
prov.addAttributes([
    QgsField("scrap_nom", QVariant.String),
    QgsField("scrap_url", QVariant.String),
])
layer_musees.updateFields()

idx_nom = layer_musees.fields().indexOf("scrap_nom")
idx_url = layer_musees.fields().indexOf("scrap_url")

# Vu que la seule facon de joindre est d'utiliser le champ des noms, or le csv et la 
#couche des musées ne porte pas exactement le même nombre de mots, on est obligé de passer par des comparaisons
#de mots et du champ d'url contenu dans la couche des musées qui redirige vers le site web du musée et non vers wikipedia

# Première passe : comparaison des noms
SEUIL = 0.4
features_sans_match = []

for feat in layer_musees.getFeatures():
    nom_sig = feat["nom_officiel_du_musee"]
    if not nom_sig:
        features_sans_match.append(feat)
        continue

    tokens_sig = set(re.findall(r'\w+', nom_sig.lower()))
    meilleur_match = None
    meilleur_score = 0

    for s in scrap_data:
        inter = tokens_sig & s["tokens"]
        union = tokens_sig | s["tokens"]
        score_token = len(inter) / len(union) if union else 0

        if score_token > meilleur_score:
            meilleur_score = score_token
            meilleur_match = s

    if meilleur_match and meilleur_score >= SEUIL:
        # ICI : on copie l’URL EXACTE
        attrs = {
            idx_nom: meilleur_match["nom"],
            idx_url: meilleur_match["url_original"]
        }
        prov.changeAttributeValues({feat.id(): attrs})
    else:
        features_sans_match.append(feat)

# Deuxième passe : URL SIG → nom CSV
for feat in features_sans_match:
    url_sig = feat["url"]
    url_sig_clean = url_sig.lower().strip() if url_sig else ""

    meilleur_match = None
    meilleur_score = 0

    for s in scrap_data:

        # Match exact substring (version clean)
        score_url = 1.0 if url_sig_clean and url_sig_clean in s["nom"] else 0

        if score_url == 0:
            score_url = difflib.SequenceMatcher(None, url_sig_clean, s["nom"]).ratio()

        if score_url > meilleur_score:
            meilleur_score = score_url
            meilleur_match = s

    if meilleur_match and meilleur_score >= 0.4:
        # COPIE EXACTE DE L’URL DU CSV
        attrs = {
            idx_nom: meilleur_match["nom"],
            idx_url: meilleur_match["url_original"]
        }
        prov.changeAttributeValues({feat.id(): attrs})

layer_musees.commitChanges()

print(" Jointure renforcée terminée — URLs copiées sans modification !")


#====================================================================
#Scrapping de l'information wikipedia et résumé avec summarize_text

from html.parser import HTMLParser
import requests
import re
from qgis.PyQt.QtCore import QVariant

# ----------------- Nettoyage texte -----------------
def clean_text(txt):
    if not txt:
        return ""
    txt = re.sub(r'\[\s*[\d\w\s\.-]+\s*\]', '', txt)  # supprime [1], [réf]
    txt = re.sub(r'\s+', ' ', txt)
    return txt.strip()

# ----------------- Variantes du titre -----------------
def generate_title_variants(title):
    title = title.lower()
    stopwords = ["musée", "de", "du", "des", "d'", "la", "le", "l’", "à"]
    words = [w for w in re.split(r'\W+', title) if w not in stopwords]
    variants = set()
    if words:
        variants.add(" ".join(words))          # version courte
        variants.add(title)                     # version complète
        variants.update(words)                  # mots clés individuels
    else:
        variants.add(title)
    return variants

# ----------------- Parser pour le titre -----------------
class TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_h1 = False
        self.title = None
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1" and attrs.get("id") == "firstHeading":
            self.in_h1 = True
    def handle_endtag(self, tag):
        if tag == "h1" and self.in_h1:
            self.in_h1 = False
    def handle_data(self, data):
        if self.in_h1:
            self.title = data.strip()

# ----------------- Parser principal -----------------
class ParagraphParserAfterTitleVariants(HTMLParser):
    def __init__(self, title_variants):
        super().__init__()
        self.title_variants = set([v.lower() for v in title_variants])
        self.in_infobox = False
        self.in_bandeau = False
        self.in_p = False
        self.current_text = ""
        self.paragraphs = []
        self.found_title_paragraph = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and "class" in attrs and "infobox" in attrs["class"]:
            self.in_infobox = True
        if tag == "div" and "class" in attrs and "bandeau" in attrs["class"]:
            self.in_bandeau = True
        if tag == "p" and not self.in_infobox and not self.in_bandeau:
            self.in_p = True
            self.current_text = ""

    def handle_endtag(self, tag):
        if tag == "table" and self.in_infobox:
            self.in_infobox = False
        if tag == "div" and self.in_bandeau:
            self.in_bandeau = False
        if tag == "p" and self.in_p:
            self.in_p = False
            txt = clean_text(self.current_text)
            if re.match(r"^(Pour les articles homonymes|Ne pas confondre)", txt, re.IGNORECASE):
                return
            if not self.found_title_paragraph:
                for variant in self.title_variants:
                    if variant in txt.lower():
                        self.found_title_paragraph = True
                        break
            if self.found_title_paragraph and len(txt) > 30:
                self.paragraphs.append(txt)

    def handle_data(self, data):
        if self.in_p:
            self.current_text += data

# ----------------- Fallback -----------------
class SecondParagraphParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_p = False
        self.current_text = ""
        self.paragraphs = []
    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self.in_p = True
            self.current_text = ""
    def handle_endtag(self, tag):
        if tag == "p" and self.in_p:
            self.in_p = False
            txt = clean_text(self.current_text)
            if len(txt) > 30:
                self.paragraphs.append(txt)
    def handle_data(self, data):
        if self.in_p:
            self.current_text += data

# ----------------- Nettoyage global pour toutes les résumés -----------------
def clean_summary_global(txt):
    if not txt:
        return txt
    patterns = [
        r"modifier\s*-\s*modifier le code\s*-\s*modifier wikidata",
        r"\d+\s*m2\s*d'expositions permanentes",
        r"\d+\s*m²\s*d'expositions permanentes"
    ]
    for pat in patterns:
        txt = re.sub(pat, '', txt, flags=re.IGNORECASE)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt

# ----------------- Résumé ~150 mots -----------------
def summarize_text(text, max_words=150):
    if not text:
        return None
    sentences = re.split(r'(?<=[.!?]) +', text)
    summary_words = []
    word_count = 0
    for s in sentences:
        s_words = s.split()
        if word_count + len(s_words) > max_words and word_count > 0:
            break
        summary_words.append(s)
        word_count += len(s_words)
    summary = " ".join(summary_words).strip()
    if not summary.endswith("."):
        summary += "."
    return summary

# ----------------- Scraper principal -----------------
def get_summary_wiki_variants(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        html = r.text

        # Titre de la page
        title_parser = TitleParser()
        title_parser.feed(html)
        page_title = title_parser.title
        if not page_title:
            return None

        # Variantes du titre
        title_variants = generate_title_variants(page_title)

        # Parser principal
        parser = ParagraphParserAfterTitleVariants(title_variants)
        parser.feed(html)
        if parser.paragraphs:
            full_text = " ".join(parser.paragraphs)
            summary = summarize_text(full_text)
            return clean_summary_global(summary)

        # Fallback
        fallback_parser = SecondParagraphParser()
        fallback_parser.feed(html)
        if len(fallback_parser.paragraphs) >= 2:
            fallback_text = fallback_parser.paragraphs[1]
        elif len(fallback_parser.paragraphs) == 1:
            fallback_text = fallback_parser.paragraphs[0]
        else:
            return None

        # Nettoyage global fallback
        fallback_text = clean_summary_global(fallback_text)
        return summarize_text(fallback_text)

    except:
        return None

# ----------------- Injection dans QGIS -----------------
layer = QgsProject.instance().mapLayersByName("Musees_Paris_4326")[0]

field_name = "information_musee"
idx_info = layer.fields().indexOf(field_name)
if idx_info == -1:
    layer.dataProvider().addAttributes([QgsField(field_name, QVariant.String)])
    layer.updateFields()
    idx_info = layer.fields().indexOf(field_name)

idx_url = layer.fields().indexOf("scrap_url")

layer.startEditing()
for f in layer.getFeatures():
    url = f[idx_url]
    if not url:
        continue

    print("Scraping :", url)
    summary = get_summary_wiki_variants(url)
    if summary:
        # Nettoyage global appliqué à tous les résumés
        summary = clean_summary_global(summary)
        f[idx_info] = summary
    else:
        f[idx_info] = "[Résumé non trouvé]"

    layer.updateFeature(f)

layer.commitChanges()
print(" Scraping et nettoyage global appliqué à toutes les lignes terminé !")

#Nettoyage du champ information_musee et suppression des chiffres avant le texte
import re
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsProject, QgsField

# ----------------- Configuration -----------------
layer_name = "Musees_Paris_4326"
field_name = "information_musee"

# Récupérer la couche
layer = QgsProject.instance().mapLayersByName(layer_name)[0]

# Vérifier que le champ existe
idx_info = layer.fields().indexOf(field_name)
if idx_info == -1:
    layer.dataProvider().addAttributes([QgsField(field_name, QVariant.String)])
    layer.updateFields()
    idx_info = layer.fields().indexOf(field_name)

# ----------------- Fonction de nettoyage -----------------
def keep_from_first_uppercase(text):
    if not text:
        return text
    # Cherche la première lettre majuscule (y compris accents)
    match = re.search(r'[A-ZÀ-ÖÙ-Ý]', text)
    if match:
        return text[match.start():].strip()
    return text

# ----------------- Mise à jour des entités -----------------
layer.startEditing()

for f in layer.getFeatures():
    original_text = f[idx_info]
    if original_text:
        cleaned_text = keep_from_first_uppercase(original_text)
        f[idx_info] = cleaned_text
        layer.updateFeature(f)

layer.commitChanges()

print(" Champ '{}' mis à jour pour commencer par la première majuscule.".format(field_name))

#_____________________________________________________________________________________________________________________________________________________________

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
