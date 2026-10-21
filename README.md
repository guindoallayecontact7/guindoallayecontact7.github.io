# Portfolio — Allaye GUINDO

Géomaticien · SIG & Télédétection · Responsable Géomarketing · Doctorant (USSGB).

Site statique publié avec GitHub Pages : carte interactive Leaflet de la turbidité du lac Wégnia (Sentinel-2, 2016-2021), projets, parcours et publications.

## Structure
- `index.html` — page unique
- `css/style.css`, `js/main.js` — mise en forme et carte Leaflet
- `data/` — couches web : `wegnia/*.png` (turbidité par date), `wegnia.json` (emprise + dates), `communes.geojson`, `villages.geojson`
- `img/` — illustrations des projets
- `cv/` — CV PDF (français, anglais), sans coordonnées des référents

## Mettre à jour
- **Ajouter une date de turbidité** : déposer la nouvelle carte exportée dans `THESE/Map` (même mise en page), puis lancer `python tools/prep_data.py data`.
- **Texte, projets, publications** : modifier `index.html`.

Sources : Copernicus Sentinel-2, limites communales DNCT, localités INSTAT/SPOT6, fonds de carte © Esri et © OpenStreetMap contributors.
