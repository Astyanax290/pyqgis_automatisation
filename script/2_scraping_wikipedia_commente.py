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
