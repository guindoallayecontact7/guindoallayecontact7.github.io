document.getElementById("year").textContent = new Date().getFullYear();

const MOIS = ["", "janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

const map = L.map("map", { scrollWheelZoom: false, zoomControl: true }).setView([13.2995, -8.1247], 14);

const satellite = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  { maxZoom: 18, attribution: "Imagerie © Esri, Maxar, Earthstar Geographics" }
).addTo(map);
const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  { maxZoom: 19, attribution: "© OpenStreetMap contributors" });

const overlays = {};
const layersCtl = L.control.layers({ "Satellite": satellite, "OpenStreetMap": osm }, overlays, { collapsed: true, position: "topleft" }).addTo(map);
L.control.scale({ imperial: false }).addTo(map);

const fmt = n => n.toLocaleString("fr-FR");

// Statistiques OSM / HOT mises à jour chaque jour par GitHub Actions (data/stats.json)
fetch("data/stats.json", { cache: "no-store" }).then(r => r.json()).then(s => {
  const o = s.osm, set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  const date = d => new Date(d).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" });
  set("osm-edits", fmt(o.edits));
  set("osm-changesets", fmt(o.changesets));
  set("osm-hot-cs", fmt(o.hot_changesets));
  set("osm-hot-proj", fmt(o.hot_projects));
  set("osm-last", o.last_edit ? date(o.last_edit) : "—");
  set("osm-updated", `Mis à jour automatiquement le ${date(s.updated)} depuis l'API publique d'OpenStreetMap (contributeur depuis ${new Date(o.since).getFullYear()}).`);
}).catch(() => {});

// Communes
fetch("data/communes.geojson").then(r => r.json()).then(gj => {
  const communes = L.geoJSON(gj, {
    style: { color: "#ffffff", weight: 1.5, fillColor: "#82beff", fillOpacity: 0.06, dashArray: "4 4" },
    onEachFeature: (f, l) => l.bindPopup(
      `<b>${f.properties.commune}</b><br>Cercle de ${f.properties.cercle}<br>Population 2013 : ${fmt(f.properties.pop2013)} hab.`)
  }).addTo(map);
  layersCtl.addOverlay(communes, "Communes");
});

// Villages
fetch("data/villages.geojson").then(r => r.json()).then(gj => {
  const villages = L.geoJSON(gj, {
    pointToLayer: (f, ll) => L.circleMarker(ll, { radius: 3, color: "#fff", weight: 1, fillColor: "#0a66c2", fillOpacity: 0.9 }),
    onEachFeature: (f, l) => l.bindTooltip(f.properties.nom)
  });
  layersCtl.addOverlay(villages, "Localités");
});

// Turbidité du lac Wégnia
const slider = document.getElementById("slider");
const dateEl = document.getElementById("date");
const playBtn = document.getElementById("play");
const opacityEl = document.getElementById("opacity");
let frames = [], overlay = null, timer = null;

fetch("data/wegnia.json").then(r => r.json()).then(meta => {
  frames = meta.frames;
  const b = L.latLngBounds(meta.bounds);
  map.invalidateSize();
  map.fitBounds(b.pad(0.35));
  window.addEventListener("load", () => { map.invalidateSize(); map.fitBounds(b.pad(0.35)); });
  overlay = L.imageOverlay(`data/wegnia/${frames[0].id}.png`, b, { opacity: +opacityEl.value }).addTo(map);
  layersCtl.addOverlay(overlay, "Turbidité (Sentinel-2)");
  frames.forEach(f => { const i = new Image(); i.src = `data/wegnia/${f.id}.png`; }); // préchargement
  slider.max = frames.length - 1;
  show(0);
});

function show(i) {
  const f = frames[i];
  if (!f || !overlay) return;
  overlay.setUrl(`data/wegnia/${f.id}.png`);
  dateEl.textContent = `${MOIS[f.month]} ${f.year}`;
  slider.value = i;
}
slider.addEventListener("input", e => { stop(); show(+e.target.value); });
opacityEl.addEventListener("input", e => overlay && overlay.setOpacity(+e.target.value));

function stop() { clearInterval(timer); timer = null; playBtn.textContent = "▶"; }
playBtn.addEventListener("click", () => {
  if (timer) return stop();
  playBtn.textContent = "❚❚";
  timer = setInterval(() => show((+slider.value + 1) % frames.length), 1100);
});

// Galerie des cartes (data/galerie.json) + visionneuse
(() => {
  const grid = document.getElementById("gallery"), lb = document.getElementById("lightbox");
  if (!grid || !lb) return;
  const img = document.getElementById("lb-img"), cap = document.getElementById("lb-cap");
  let items = [], shown = [], cur = 0;
  const render = g => {
    shown = g === "all" ? items : items.filter(i => i.g === g);
    grid.innerHTML = "";
    shown.forEach((it, k) => {
      const b = document.createElement("button");
      b.innerHTML = `<img src="img/cartes/mini/${it.f}" alt="${it.t}" loading="lazy"><span>${it.t}</span>`;
      b.addEventListener("click", () => open(k));
      grid.appendChild(b);
    });
  };
  const open = k => { cur = (k + shown.length) % shown.length; const it = shown[cur];
    img.src = `img/cartes/${it.f}`; img.alt = it.t; cap.textContent = `${it.t} (${cur + 1}/${shown.length})`;
    lb.hidden = false; lb.querySelector(".lb-close").focus(); };
  const close = () => { lb.hidden = true; };
  lb.querySelector(".lb-close").addEventListener("click", close);
  lb.querySelector(".lb-prev").addEventListener("click", () => open(cur - 1));
  lb.querySelector(".lb-next").addEventListener("click", () => open(cur + 1));
  lb.addEventListener("click", e => { if (e.target === lb) close(); });
  document.addEventListener("keydown", e => {
    if (lb.hidden) return;
    if (e.key === "Escape") close(); else if (e.key === "ArrowLeft") open(cur - 1); else if (e.key === "ArrowRight") open(cur + 1);
  });
  document.querySelectorAll(".chip-btn").forEach(btn => btn.addEventListener("click", () => {
    document.querySelectorAll(".chip-btn").forEach(x => x.classList.toggle("active", x === btn));
    render(btn.dataset.g);
  }));
  fetch("data/galerie.json").then(r => r.json()).then(d => { items = d; render("all"); });
})();
