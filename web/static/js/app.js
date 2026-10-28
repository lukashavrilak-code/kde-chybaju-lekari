import { PALETA_VZDIALENOST, VrstvaObci, VrstvaOkolia, VrstvaOkresov, vykresliLegendu, vytvorMapu } from "./map.js";
import { vykresliChybu, vykresliObec, vykresliOkres } from "./panel.js";
import { nastavHladanie } from "./search.js";
import { bezDiakritiky, formatCislo, haversineKm, nacitajJson } from "./util.js";

const panel = document.getElementById("panel");
const legenda = document.getElementById("legenda");
const vstup = document.getElementById("hladat");
const uvodPanela = Array.from(panel.childNodes, (uzol) => uzol.cloneNode(true));
const stav = { typ: null, vrstva: "okresy" };
let meta = null;
let okresy = null;
let vrstvaOkresov = null;
let vrstvaObci = null;
let vrstvaOkolia = null;
let zvyrazniKartu = null;
let indexPromise = null;

function citajHash() {
  const parametre = new URLSearchParams(location.hash.slice(1));
  return { typ: parametre.get("typ"), obec: parametre.get("obec"), okres: parametre.get("okres"), vrstva: parametre.get("vrstva") };
}

function zapisHash(zmena) {
  const hodnoty = { ...citajHash(), ...zmena };
  const parametre = new URLSearchParams();
  for (const [kluc, hodnota] of Object.entries(hodnoty)) {
    if (hodnota) parametre.set(kluc, hodnota);
  }
  location.hash = parametre.toString();
}

function platnyTyp(typ) {
  return meta.typy.includes(typ) ? typ : meta.typy[0];
}

function okresPodlaKodu(kod) {
  return okresy.features.find((feature) => feature.properties.kod === kod) || null;
}

function indexObci() {
  if (!indexPromise) {
    indexPromise = nacitajJson("data/obce.json").then((data) => {
      const nazvy = new Map(okresy.features.map((f) => [f.properties.kod, f.properties.nazov]));
      return data.obce.map((obec) => ({ ...obec, kluc: bezDiakritiky(obec.nazov), okresNazov: nazvy.get(obec.okres_kod) || "" }));
    });
  }
  return indexPromise;
}

function zobrazZastarane() {
  const den = 24 * 60 * 60 * 1000;
  const vek = (Date.now() - Date.parse(`${meta.stav_registra}T00:00:00Z`)) / den;
  if (vek > meta.zastarane_po_dnoch) document.getElementById("zastarane").hidden = false;
}

function synchronizujPrepinac() {
  document.querySelectorAll('input[name="typ"]').forEach((radio) => {
    radio.checked = radio.value === stav.typ;
  });
  document.querySelectorAll('input[name="vrstva"]').forEach((radio) => {
    radio.checked = radio.value === stav.vrstva;
  });
}

async function obnovVrstvy() {
  const prefix = stav.typ.toLowerCase();
  const nazovTypu = meta.nazvy_typov[stav.typ].toLowerCase();
  if (stav.vrstva === "obce") {
    const obce = await indexObci();
    vrstvaObci.zobraz(obce, stav.typ, meta.legenda.vzdialenost_km);
    vykresliLegendu(
      legenda,
      `Vzdušná vzdialenosť zo stredu obce k najbližšej ambulancii v km: ${nazovTypu}`,
      meta.legenda.vzdialenost_km,
      obce.map((obec) => obec[`${prefix}_km`]),
      { paleta: PALETA_VZDIALENOST, format: formatCislo, poznamka: "Tmavšia farba = ďalej od ambulancie. V zátvorke je počet obcí." },
    );
    return;
  }
  vrstvaObci.skry();
  vykresliLegendu(
    legenda,
    `Ambulancie na 10 000 ${meta.menovatele[stav.typ]}: ${nazovTypu}`,
    meta.legenda[stav.typ],
    okresy.features.map((feature) => feature.properties[`${prefix}_na10k`]),
  );
}

async function zobrazObec(obec) {
  const data = await nacitajJson("data/ambulancie.json");
  const vsetky = data.ambulancie
    .map((ambulancia) => ({ ambulancia, km: haversineKm(obec.lat, obec.lon, ambulancia.lat, ambulancia.lon) }))
    .filter((zaznam) => zaznam.km <= meta.max_zoznam_km)
    .sort((x, y) => x.km - y.km || x.ambulancia.nazov.localeCompare(y.ambulancia.nazov, "sk"));
  const pocitadla = {};
  for (const zaznam of vsetky) {
    const typ = zaznam.ambulancia.typ;
    zaznam.index = pocitadla[typ] || 0;
    pocitadla[typ] = zaznam.index + 1;
  }
  const zoznamTypu = vsetky.filter((zaznam) => zaznam.ambulancia.typ === stav.typ);
  vrstvaOkresov.obnov({ vybrany: obec.okres_kod, priehladne: true, lenObrys: stav.vrstva === "obce" });
  const vyber = (index) => {
    vrstvaOkolia.zvyrazni(index);
    if (zvyrazniKartu) zvyrazniKartu(index);
  };
  vrstvaOkolia.zobraz(obec, zoznamTypu, meta.polomery_km, vyber);
  zvyrazniKartu = vykresliObec(panel, obec, okresPodlaKodu(obec.okres_kod), stav.typ, meta, vsetky, vyber);
  vstup.value = obec.nazov;
}

async function aplikujStav() {
  const hash = citajHash();
  stav.typ = platnyTyp(hash.typ);
  stav.vrstva = hash.vrstva === "obce" ? "obce" : "okresy";
  synchronizujPrepinac();
  await obnovVrstvy();
  if (hash.obec) {
    const obec = (await indexObci()).find((o) => o.kod === hash.obec);
    if (obec) {
      await zobrazObec(obec);
      return;
    }
  }
  vrstvaOkolia.vycisti();
  zvyrazniKartu = null;
  const okres = hash.okres ? okresPodlaKodu(hash.okres) : null;
  vrstvaOkresov.obnov({ vybrany: okres ? okres.properties.kod : null, priehladne: false, lenObrys: stav.vrstva === "obce" });
  if (okres) {
    vykresliOkres(panel, okres, stav.typ, meta, okresy.features.length);
  } else {
    panel.replaceChildren(...uvodPanela.map((uzol) => uzol.cloneNode(true)));
  }
}

function zobrazChybu(chyba) {
  vykresliChybu(panel, `Skúste stránku obnoviť. Podrobnosti: ${chyba.message}`);
}

async function start() {
  [meta, okresy] = await Promise.all([nacitajJson("data/meta.json"), nacitajJson("data/okresy.geojson")]);
  stav.typ = platnyTyp(citajHash().typ);
  zobrazZastarane();
  const mapa = vytvorMapu("mapa", meta);
  vrstvaOkresov = new VrstvaOkresov(mapa, okresy, {
    typ: () => stav.typ,
    hranice: () => meta.legenda[stav.typ],
    priKliknuti: (feature) => zapisHash({ okres: feature.properties.kod, obec: null }),
  });
  vrstvaObci = new VrstvaObci(mapa, (obec) => zapisHash({ obec: obec.kod, okres: null }));
  vrstvaOkolia = new VrstvaOkolia(mapa);
  document.querySelectorAll('input[name="typ"]').forEach((radio) => {
    radio.addEventListener("change", () => zapisHash({ typ: radio.value }));
  });
  document.querySelectorAll('input[name="vrstva"]').forEach((radio) => {
    radio.addEventListener("change", () => zapisHash({ vrstva: radio.value === "obce" ? "obce" : null }));
  });
  nastavHladanie(vstup, document.getElementById("navrhy"), indexObci, (obec) => zapisHash({ obec: obec.kod, okres: null }));
  window.addEventListener("hashchange", () => aplikujStav().catch(zobrazChybu));
  await aplikujStav();
}

start().catch(zobrazChybu);
