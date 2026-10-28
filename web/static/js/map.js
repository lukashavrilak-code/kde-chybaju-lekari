import { el, formatKm, formatNa10k } from "./util.js";

const PALETA = ["#104281", "#1c5cab", "#2a78d6", "#5598e7", "#86b6ef"];
export const PALETA_VZDIALENOST = [...PALETA].reverse();
const BEZ_UDAJOV = "#c3c2b7";
const SLOVENSKO = [[47.73, 16.83], [49.61, 22.57]];

export function triedaHodnoty(hodnota, hranice) {
  if (hodnota === null || hodnota === undefined || Number.isNaN(hodnota)) return -1;
  let trieda = 0;
  while (trieda < hranice.length && hodnota >= hranice[trieda]) trieda += 1;
  return trieda;
}

export function farbaHodnoty(hodnota, hranice, paleta = PALETA) {
  const trieda = triedaHodnoty(hodnota, hranice);
  return trieda < 0 ? BEZ_UDAJOV : paleta[trieda];
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
    this.lenObrys = false;
    this.vrstva = L.geoJSON(geojson, {
      style: (feature) => this.styl(feature),
      onEachFeature: (feature, layer) => {
        layer.bindTooltip(() => this.tooltip(feature), { sticky: true });
        layer.on("click", () => nastavenia.priKliknuti(feature));
      },
    }).addTo(mapa);
  }

  hodnota(feature) {
    return feature.properties[`${this.nastavenia.typ().toLowerCase()}_${this.nastavenia.ukazovatel()}`];
  }

  styl(feature) {
    const vybrany = this.vybrany === feature.properties.kod;
    let vypln = this.priehladne ? 0.3 : 0.85;
    if (this.lenObrys) vypln = 0;
    let obrys = this.lenObrys ? "#52514e" : "#ffffff";
    if (vybrany) obrys = "#0b0b0b";
    return {
      color: obrys,
      weight: vybrany ? 3 : 1,
      fillColor: farbaHodnoty(this.hodnota(feature), this.nastavenia.hranice()),
      fillOpacity: vypln,
    };
  }

  tooltip(feature) {
    return el(
      "div",
      null,
      el("div", { trieda: "tooltip-nazov", text: `Okres ${feature.properties.nazov}` }),
      el("div", { text: `${formatNa10k(this.hodnota(feature))} ${this.nastavenia.popis()}` }),
    );
  }

  obnov({ vybrany, priehladne, lenObrys = false }) {
    this.vybrany = vybrany;
    this.priehladne = priehladne;
    this.lenObrys = lenObrys;
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

export class VrstvaObci {
  constructor(mapa, priKliknuti) {
    this.mapa = mapa;
    this.priKliknuti = priKliknuti;
    this.skupina = L.layerGroup();
    this.body = [];
    this.kluc = null;
  }

  zobraz(obce, typ, hranice) {
    this.kluc = `${typ.toLowerCase()}_km`;
    if (!this.body.length) {
      for (const obec of obce) {
        const bod = L.circleMarker([obec.lat, obec.lon], { radius: 4, weight: 0.5, color: "#ffffff", fillOpacity: 0.9 });
        bod.bindTooltip(() => el("div", { text: `${obec.nazov}: najbližšia ambulancia ${formatKm(obec[this.kluc])}` }));
        bod.on("click", () => this.priKliknuti(obec));
        bod.addTo(this.skupina);
        this.body.push([obec, bod]);
      }
    }
    for (const [obec, bod] of this.body) {
      bod.setStyle({ fillColor: farbaHodnoty(obec[this.kluc], hranice, PALETA_VZDIALENOST) });
    }
    this.skupina.addTo(this.mapa);
  }

  skry() {
    this.skupina.remove();
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

export function vykresliLegendu(kontajner, nadpis, hranice, hodnoty, moznosti = {}) {
  const paleta = moznosti.paleta || PALETA;
  const format = moznosti.format || formatNa10k;
  const poznamka = moznosti.poznamka || "Tmavšia farba = menej ambulancií. V zátvorke je počet okresov.";
  const pocty = new Array(hranice.length + 1).fill(0);
  for (const hodnota of hodnoty) {
    const trieda = triedaHodnoty(hodnota, hranice);
    if (trieda >= 0) pocty[trieda] += 1;
  }
  const polozky = [el("span", { trieda: "titulok", text: nadpis })];
  for (let trieda = 0; trieda <= hranice.length; trieda += 1) {
    let popis;
    if (trieda === 0) popis = `menej ako ${format(hranice[0])}`;
    else if (trieda === hranice.length) popis = `${format(hranice[trieda - 1])} a viac`;
    else popis = `${format(hranice[trieda - 1])} – ${format(hranice[trieda])}`;
    const vzorka = el("span", { trieda: "vzorka", atributy: { "aria-hidden": "true" } });
    vzorka.style.backgroundColor = paleta[trieda];
    polozky.push(el("span", { trieda: "polozka" }, vzorka, el("span", { text: `${popis} (${pocty[trieda]})` })));
  }
  polozky.push(el("span", { trieda: "polozka", text: poznamka }));
  kontajner.replaceChildren(...polozky);
}
