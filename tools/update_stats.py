"""Met à jour data/stats.json à partir de l'API publique d'OpenStreetMap.

Lancé chaque jour par GitHub Actions (.github/workflows/update-stats.yml).
Aucune clé ni mot de passe : seules des données publiques sont lues.

Calcule pour l'utilisateur OSM :
- date de création du compte, nombre de changesets, total des modifications (changes_count) ;
- changesets réalisés via le HOT Tasking Manager (hashtag #hotosm-project-N) et projets HOT distincts ;
- date de la dernière contribution.
"""
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

UID = 5943826  # Allaye Guindo sur OpenStreetMap
API = "https://api.openstreetmap.org/api/0.6"
UA = "portfolio-stats/1.0 (+https://guindoallayecontact7.github.io)"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "data", "stats.json")
HOT_RE = re.compile(r"hotosm-project-(\d+)", re.I)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


user = get(f"{API}/user/{UID}.json")["user"]

changesets, before = [], None
while True:
    url = f"{API}/changesets.json?user={UID}&limit=100"
    if before:
        url += f"&time=2004-01-01T00:00:00Z,{before}"
    batch = get(url)["changesets"]
    new = [c for c in batch if c["id"] not in {x["id"] for x in changesets[-100:]}]
    changesets += new
    if len(batch) < 100 or not new:
        break
    before = min(c["created_at"] for c in batch)
    time.sleep(1)

edits = sum(c.get("changes_count", 0) for c in changesets)
hot_cs, hot_projects = 0, set()
for c in changesets:
    tags = c.get("tags", {})
    text = " ".join(str(tags.get(k, "")) for k in ("comment", "hashtags"))
    ids = HOT_RE.findall(text)
    if ids:
        hot_cs += 1
        hot_projects.update(int(i) for i in ids)

last = max((c.get("closed_at") or c["created_at"]) for c in changesets) if changesets else None
stats = {
    "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "osm": {
        "username": user["display_name"],
        "since": user["account_created"][:10],
        "changesets": user.get("changesets", {}).get("count", len(changesets)),
        "edits": edits,
        "hot_changesets": hot_cs,
        "hot_projects": len(hot_projects),
        "last_edit": last[:10] if last else None,
    },
}

os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=1)
print(json.dumps(stats, ensure_ascii=False))
print(f"{len(changesets)} changesets lus")
