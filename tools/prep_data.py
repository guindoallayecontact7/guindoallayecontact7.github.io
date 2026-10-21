"""Prépare les données web du portfolio à partir de THESE/Map.

- Turbidité du lac Wégnia : images exportées (1123x794, sans géoréférencement) -> PNG
  transparents + emprise géographique calée sur le carroyage de la carte
  (8°7'30" O à x=551,5 px ; 13°18' N à y=372,5 px ; échelle 900 m = 309 px).
- Communes et villages (shapefiles WGS84) -> GeoJSON allégés.
"""
import json, math, os, sys, glob
import numpy as np, rasterio, shapefile
from PIL import Image, ImageFilter

SRC = r"C:\Users\Allaye\Downloads\THESE\Map"
OUT = sys.argv[1]
os.makedirs(os.path.join(OUT, "wegnia"), exist_ok=True)

# --- Géoréférencement (UTM 29N quasi aligné nord ; zone < 3 km -> approximation plane)
X0, LON0 = 551.5, -8.125
Y0, LAT0 = 372.5, 13.3
M_PER_PX = 900 / 309
dlat = M_PER_PX / 110574.0
dlon = M_PER_PX / (111320.0 * math.cos(math.radians(LAT0)))
CROP = (60, 170, 1065, 610)  # zone du lac (exclut légende, échelle, rose des vents)
x0, y0, x1, y1 = CROP
bounds = [[LAT0 - (y1 - Y0) * dlat, LON0 + (x0 - X0) * dlon],   # sud-ouest
          [LAT0 - (y0 - Y0) * dlat, LON0 + (x1 - X0) * dlon]]   # nord-est

frames = []
for f in sorted(glob.glob(os.path.join(SRC, "20*_*.tif"))):
    name = os.path.splitext(os.path.basename(f))[0]
    with rasterio.open(f) as r:
        a = np.transpose(r.read(), (1, 2, 0))[y0:y1, x0:x1]
    ai = a.astype(int)
    mx, mn = ai.max(-1), ai.min(-1)
    colored = (mx - mn > 60) & (mx > 90)
    outline = mx < 70
    m = Image.fromarray(((colored | outline) * 255).astype(np.uint8))
    # retire les petits restes isolés
    core = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(9))
    alpha = np.minimum(np.array(m), np.array(core))
    Image.fromarray(np.dstack([a, alpha]).astype(np.uint8), "RGBA").save(
        os.path.join(OUT, "wegnia", name + ".png"), optimize=True)
    y, mth = name.split("_")
    frames.append({"id": name, "year": int(y), "month": int(mth)})

# --- Statistiques de turbidité (part de surface par classe) depuis les couleurs de légende
CLASSES = {"Fortement trouble": (255, 40, 0), "Trouble": (255, 190, 0),
           "Légèrement trouble": (150, 200, 30), "Eau claire": (0, 110, 20)}
for fr in frames:
    im = np.array(Image.open(os.path.join(OUT, "wegnia", fr["id"] + ".png")).convert("RGBA")).astype(int)
    px = im[im[..., 3] > 0][:, :3]
    px = px[(px.max(1) - px.min(1)) > 60]
    cols = np.array(list(CLASSES.values()))
    d = ((px[:, None, :] - cols[None, :, :]) ** 2).sum(-1)
    lab = d.argmin(1)
    tot = len(lab)
    fr["parts"] = {k: round(100 * (lab == i).sum() / tot, 1) for i, k in enumerate(CLASSES)}

json.dump({"bounds": bounds, "frames": frames}, open(os.path.join(OUT, "wegnia.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# --- Vecteurs
def rnd(c, n=5):
    return [round(c[0], n), round(c[1], n)]

def poly_feats(path, props_fn, tol=0.0015):
    from shapely.geometry import shape, mapping
    r = shapefile.Reader(path, encoding="latin1")
    feats = []
    for sr in r.iterShapeRecords():
        g = shape(sr.shape.__geo_interface__).simplify(tol, preserve_topology=True)
        gm = mapping(g)
        def fix(o):
            if isinstance(o, (list, tuple)) and o and isinstance(o[0], (int, float)):
                return rnd(o)
            return [fix(x) for x in o]
        gm = {"type": gm["type"], "coordinates": fix(gm["coordinates"])}
        feats.append({"type": "Feature", "geometry": gm, "properties": props_fn(sr.record)})
    return {"type": "FeatureCollection", "features": feats}

communes = poly_feats(os.path.join(SRC, "limite_commune"),
                      lambda r: {"commune": r["COMMUNE_NA"].title(), "cercle": r["CERCLE_NAM"].title(),
                                 "pop2013": int(r["TOTAL_POP2"] or 0)})
json.dump(communes, open(os.path.join(OUT, "communes.geojson"), "w", encoding="utf-8"), ensure_ascii=False)

v = shapefile.Reader(os.path.join(SRC, "Village"), encoding="latin1")
vf = []
for sr in v.iterShapeRecords():
    rec = sr.record
    nm = rec["Nom_LOC"] or rec["Nom_50K"] or rec["Nom_INSTAT"]
    if not nm:
        continue
    vf.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": rnd(sr.shape.points[0])},
               "properties": {"nom": nm, "type": (rec["Type"] or "").replace("_", " ").title()}})
json.dump({"type": "FeatureCollection", "features": vf},
          open(os.path.join(OUT, "villages.geojson"), "w", encoding="utf-8"), ensure_ascii=False)

print("bounds", bounds)
print(len(frames), "images ;", len(communes["features"]), "communes ;", len(vf), "villages nommés")
print(frames[0], frames[-1])
