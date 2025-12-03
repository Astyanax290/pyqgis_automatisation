# pyqgis_automatisation

Testé pour QGIS 3.44
### Contexte: 

Ce travail mené sur les musées parisiens dotés de l’appellation « Musée de France » s’inscrit dans une démarche visant à mieux comprendre l’accessibilité et l’intégration territoriale de ces équipements culturels au sein du tissu urbain. Les musées jouent un rôle essentiel dans la diffusion du patrimoine, l’animation culturelle et l’attractivité du territoire. Analyser leur localisation, leur accessibilité piétonne (notamment via le calcul d’isochrones) ainsi que leur connexion aux réseaux de transport permet d’évaluer la qualité de leur desserte et leur potentiel de fréquentation.

Ce travail constitue une base essentielle pour la création d’un atlas cartographique.



### Données utilisées:



\- Liste des Musées d'ile de France; la liste officielle des institutions dotées de l'appellation "Musée de France" au sens du Code du patrimoine

Selection par les paramètres select \* where commune = "Paris" limit=100 et recupération directe du lien de l'API:

https://data.iledefrance.fr/api/explore/v2.1/catalog/datasets/liste\_des\_musees\_franciliens/records?select=\*\&where=commune%3D%20%22Paris%22\&limit=100

Lien directe source de données

https://data.iledefrance.fr/explore/dataset/liste\_des\_musees\_franciliens/table/?disjunctive.departement\&disjunctive.region\_administrative



\- Gares et stations du réseau ferré d'Île-de-France (donnée généralisée) : https://data.iledefrance.fr/explore/dataset/gares-et-stations-du-reseau-ferre-dile-de-france-donnee-generalisee/export/?location=13,48.88594,2.32979\&basemap=jawg.sunny



Téléchargement de la donnée + découpage spatiale sur la commune de Paris



* Couche Périmètre Paris



### Workflow



A) Chargement des couches et création des cartes de localisation



&nbsp;	- Import des modules et configuration de base

&nbsp;	- Définition du répertoire de sortie

&nbsp;	- Réinitialisation du projet

&nbsp;	- Chargement du fond de couche

&nbsp;	- Récupération des données musées via l'API, création et chargement comme couche et 		symbologie

&nbsp;	- Chargement de la couche du périmètre de la commune de Paris

&nbsp;	- Génération des cartes de localisation

&nbsp;	- Chargement de la couche des gares, sélection par localisation et symbologie 



B) Webscraping  Wikipédia



&nbsp;	- Scraper l'url des musées de Paris dans la section dédié sur la page 	https://fr.wikipedia.org/wiki/Mus%C3%A9e\_de\_France et enregistrement csv

&nbsp;	- Jointure entre csv et couche des musées

&nbsp;	- Scraping information sur les musées via le champ url issu de la jointure et résumé



C) Isochrone à 5 et 10 min de chaque musée et symbologie catégorisée

D) Symbologie basée sur règle des gares

E) Mise en page


## Utilisation

1. Télécharger ou cloner ce dépôt  
2. Ouvrir QGIS  
3. Placer les scripts dans le dossier Python de votre choix  
4. Adapter la variable `monCheminDeBase` dans les scripts  
5. Exécuter les scripts directement depuis l’éditeur Python de QGIS

---

## Auteur

Projet réalisé par **Astyanax GNANSOUNOU**,  
Étudiant en Master Géomatique.

---

## Licence

Ce projet peut être réutilisé à des fins pédagogiques ou personnelles.  
Merci de mentionner l’auteur en cas de reprise.
