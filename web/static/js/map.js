import { el, formatNa10k } from "./util.js";

const PALETA = ["#104281", "#1c5cab", "#2a78d6", "#5598e7", "#86b6ef"];
const BEZ_UDAJOV = "#c3c2b7";
const SLOVENSKO = [[47.73, 16.83], [49.61, 22.57]];

export function triedaHodnoty(hodnota, hranice) {
  if (hodnota === null || hodnota === undefined || Number.isNaN(hodnota)) return -1;
  let trieda = 0;
  while (trieda < hranice.length && hodnota >= hranice[trieda]) trieda += 1;
  return trieda;
}

export function farbaHodnoty(hodnota, hranice) {
  const trieda = triedaHodnoty(hodnota, hranice);
  return trieda < 0 ? BEZ_UDAJOV : PALETA[trieda];
}

export function vytvorMapu(idKontajnera, meta) {
  const mapa = L.map(idKontajnera, { minZoom: 6, maxZoom: 17, zoomSnap: 0.5 });
  mapa.fitBounds(SLOVENSKO);
  L.tileLayer(meta.tile_url, {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(mapa);
  return mapa;
}

export class VrstvaOkresov {
  constructor(mapa, geojson, nastavenia) {
    this.nastavenia = nastavenia;
    this.vybrany = null;
    this.priehladne = false;
    this.vrstva = L.geoJSON(geojson, {
      style: (feature) => this.styl(feature),
      onEachFeature: (feature, layer) => {
        layer.bindTooltip(() => this.tooltip(feature), { sticky: true });
        layer.on("click", () => nastavenia.priKliknuti(feature));
      },
    }).addTo(mapa);
  }

  hodnota(feature) {
    return feature.properties[`${this.nastavenia.typ().toLowerCase()}_na10k`];
  }

  styl(feature) {
    const vybrany = this.vybrany === feature.properties.kod;
    return {
      color: vybrany ? "#0b0b0b" : "#ffffff",
      weight: vybrany ? 3 : 1,
      fillColor: farbaHodnoty(this.hodnota(feature), this.nastavenia.hranice()),
      fillOpacity: this.priehladne ? 0.3 : 0.85,
    };
  }

  tooltip(feature) {
    return el(
      "div",
      null,
      el("div", { trieda: "tooltip-nazov", text: `Okres ${feature.properties.nazov}` }),
      el("div", { text: `${formatNa10k(this.hodnota(feature))} na 10 000` }),
    );
  }

  obnov({ vybrany, priehladne }) {
    this.vybrany = vybrany;
    this.priehladne = priehladne;
    this.vrstva.setStyle((feature) => this.styl(feature));
    this.vrstva.eachLayer((layer) => {
      if (layer.feature.properties.kod === vybrany) layer.bringToFront();
    });
  }

  hranicaOkresu(kod) {
    let vysledok = null;
    this.vrstva.eachLayer((layer) => {
      if (layer.feature.properties.kod === kod) vysledok = layer.getBounds();
    });
    return vysledok;
  }
}

export class VrstvaOkolia {
  constructor(mapa) {
    this.mapa = mapa;
    this.skupina = L.layerGroup().addTo(mapa);
    this.body = new Map();
  }

  zobraz(obec, ambulancie, polomery, priKliknuti) {
    this.skupina.clearLayers();
    this.body.clear();
    for (const polomer of polomery) {
      L.circle([obec.lat, obec.lon], {
        radius: polomer * 1000,
        color: "#0b0b0b",
        weight: 1.5,
        dashArray: "6 6",
        fill: false,
        interactive: false,
      }).addTo(this.skupina);
    }
    ambulancie.forEach((zaznam, index) => {
      const bod = L.circleMarker([zaznam.ambulancia.lat, zaznam.ambulancia.lon], {
        radius: 6,
        color: "#ffffff",
        weight: 2,
        fillColor: "#0b0b0b",
        fillOpacity: 1,
      });
      bod.bindTooltip(() => el("div", { text: zaznam.ambulancia.nazov }));
      bod.on("click", () => priKliknuti(index));
      bod.addTo(this.skupina);
      this.body.set(index, bod);
    });
    L.circleMarker([obec.lat, obec.lon], {
      radius: 8,
      color: "#0b0b0b",
      weight: 3,
      fillColor: "#ffffff",
      fillOpacity: 1,
    })
      .bindTooltip(() => el("div", { text: `Stred obce ${obec.nazov}` }))
      .addTo(this.skupina);
    this.mapa.fitBounds(L.latLng(obec.lat, obec.lon).toBounds(polomery[polomery.length - 1] * 2000));
  }

  zvyrazni(index) {
    for (const [i, bod] of this.body) {
      bod.setStyle(i === index ? { radius: 10, fillColor: "#ffffff", color: "#0b0b0b", weight: 3 } : { radius: 6, fillColor: "#0b0b0b", color: "#ffffff", weight: 2 });
      if (i === index) bod.bringToFront();
    }
  }

  vycisti() {
    this.skupina.clearLayers();
    this.body.clear();
  }
}

export function vykresliLegendu(kontajner, nadpis, hranice, hodnoty) {
  const pocty = new Array(hranice.length + 1).fill(0);
  for (const hodnota of hodnoty) {
    const trieda = triedaHodnoty(hodnota, hranice);
    if (trieda >= 0) pocty[trieda] += 1;
  }
  const polozky = [el("span", { trieda: "titulok", text: nadpis })];
  for (let trieda = 0; trieda <= hranice.length; trieda += 1) {
    let popis;
    if (trieda === 0) popis = `menej ako ${formatNa10k(hranice[0])}`;
    else if (trieda === hranice.length) popis = `${formatNa10k(hranice[trieda - 1])} a viac`;
    else popis = `${formatNa10k(hranice[trieda - 1])} – ${formatNa10k(hranice[trieda])}`;
    const vzorka = el("span", { trieda: "vzorka", atributy: { "aria-hidden": "true" } });
    vzorka.style.backgroundColor = PALETA[trieda];
    polozky.push(el("span", { trieda: "polozka" }, vzorka, el("span", { text: `${popis} (${pocty[trieda]})` })));
  }
  polozky.push(el("span", { trieda: "polozka", text: "Tmavšia farba = menej ambulancií. V zátvorke je počet okresov." }));
  kontajner.replaceChildren(...polozky);
}
