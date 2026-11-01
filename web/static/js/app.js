import { SpodnaLista } from "./lista.js";
import { PALETA_VZDIALENOST, VrstvaObci, VrstvaOkolia, VrstvaOkresov, pridajTlacidloSlovensko, vykresliLegendu, vytvorMapu, zobrazSlovensko } from "./map.js";
import { vykresliChybu, vykresliObec, vykresliOkres } from "./panel.js";
import { nastavHladanie } from "./search.js";
import { bezDiakritiky, el, formatCislo, formatKm, formatNa10k, haversineKm, nacitajJson } from "./util.js";

const panel = document.getElementById("panel");
const legenda = document.getElementById("legenda");
const vstup = document.getElementById("hladat");
const uvodPanela = Array.from(panel.childNodes, (uzol) => uzol.cloneNode(true));
const stav = { typ: null, vrstva: "okresy", priblizene: false };
let meta = null;
let okresy = null;
let mapa = null;
let lista = null;
let vrstvaOkresov = null;
let vrstvaObci = null;
let vrstvaOkolia = null;
let indexPromise = null;
let poslednyBeh = 0;

function jeMobil() {
  return window.matchMedia("(max-width: 800px)").matches;
}

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

function zobrazNacitavanie() {
  panel.setAttribute("aria-busy", "true");
  panel.replaceChildren(el("p", { text: "Načítavam údaje…" }));
}

function ukazovatelOkresov() {
  return stav.vrstva === "okolie" ? "okolie" : "na10k";
}

function popisUkazovatela() {
  return stav.vrstva === "okolie" ? `na 10 000 v okolí ${meta.spadova_oblast_km} km` : "na 10 000";
}

async function obnovVrstvy(aktualny) {
  const prefix = stav.typ.toLowerCase();
  const nazovTypu = meta.nazvy_typov[stav.typ].toLowerCase();
  if (stav.vrstva === "obce") {
    legenda.replaceChildren(el("span", { trieda: "titulok", text: "Načítavam obce…" }));
    const obce = await indexObci();
    if (!aktualny()) return;
    vrstvaObci.zobraz(obce, stav.typ, meta.legenda.vzdialenost_km);
    vykresliLegendu(
      legenda,
      `Vzdušná vzdialenosť zo stredu obce k najbližšej ambulancii v km: ${nazovTypu}`,
      meta.legenda.vzdialenost_km,
      obce.map((obec) => obec[`${prefix}_km`]),
      { paleta: PALETA_VZDIALENOST, format: formatCislo, poznamka: "Tmavšia farba = bližšie k ambulancii. V zátvorke je počet obcí." },
    );
    return;
  }
  vrstvaObci.skry();
  const okolie = stav.vrstva === "okolie" ? ` v okolí ${meta.spadova_oblast_km} km` : "";
  vykresliLegendu(
    legenda,
    `Ambulancie na 10 000 ${meta.menovatele[stav.typ]}${okolie}: ${nazovTypu}`,
    meta.legenda[stav.typ],
    okresy.features.map((feature) => feature.properties[`${prefix}_${ukazovatelOkresov()}`]),
  );
}

function popisVyberu(zoznam, indexy) {
  const prvy = zoznam[indexy[0]];
  const casti = [formatKm(prvy.km)];
  if (indexy.length > 1) casti.push(`adries na tomto bode: ${indexy.length}`);
  else if (prvy.ambulancia.pocet > 1) casti.push(`ambulancií: ${prvy.ambulancia.pocet}`);
  return { nadpis: prvy.ambulancia.nazov || prvy.ambulancia.adresa || "Adresa v registri chýba", riadok: casti.join(" · ") };
}

async function zobrazObec(obec, aktualny) {
  const data = await nacitajJson("data/ambulancie.json");
  if (!aktualny()) return;
  panel.removeAttribute("aria-busy");
  stav.priblizene = true;
  const vsetky = data.ambulancie
    .map((ambulancia) => ({ ambulancia, km: haversineKm(obec.lat, obec.lon, ambulancia.lat, ambulancia.lon) }))
    .filter((zaznam) => zaznam.km <= meta.max_zoznam_km)
    .sort((x, y) => x.km - y.km || x.ambulancia.adresa.localeCompare(y.ambulancia.adresa, "sk"));
  const pocitadla = {};
  for (const zaznam of vsetky) {
    const typ = zaznam.ambulancia.typ;
    zaznam.index = pocitadla[typ] || 0;
    pocitadla[typ] = zaznam.index + 1;
  }
  const zoznamTypu = vsetky.filter((zaznam) => zaznam.ambulancia.typ === stav.typ);
  vrstvaOkresov.obnov({ vybrany: obec.okres_kod, priehladne: true, lenObrys: stav.vrstva === "obce" });
  let zvyrazniKartu = null;
  const vyber = (indexy, zMapy) => {
    vrstvaOkolia.zvyrazni(indexy);
    const karta = zvyrazniKartu(indexy, zMapy && !jeMobil());
    const { nadpis, riadok } = popisVyberu(zoznamTypu, indexy);
    lista.zobraz(nadpis, riadok, () => karta.scrollIntoView());
  };
  vrstvaOkolia.zobraz(obec, zoznamTypu, meta.polomery_km, (indexy) => vyber(indexy, true));
  zvyrazniKartu = vykresliObec(panel, obec, okresPodlaKodu(obec.okres_kod), stav.typ, meta, vsetky, (index) => vyber([index], false));
  vstup.value = obec.nazov;
  const prefix = stav.typ.toLowerCase();
  const polomer = meta.polomery_km[0];
  lista.zobraz(
    obec.nazov,
    `Najbližšia ${formatKm(obec[`${prefix}_km`])} · do ${polomer} km: ${formatCislo(obec[`${prefix}_${polomer}`])}`,
    () => panel.scrollIntoView(),
  );
}

async function aplikujStav() {
  poslednyBeh += 1;
  const beh = poslednyBeh;
  const aktualny = () => beh === poslednyBeh;
  const hash = citajHash();
  stav.typ = platnyTyp(hash.typ);
  stav.vrstva = ["okolie", "obce"].includes(hash.vrstva) ? hash.vrstva : "okresy";
  synchronizujPrepinac();
  panel.removeAttribute("aria-busy");
  if (hash.obec) zobrazNacitavanie();
  await obnovVrstvy(aktualny);
  if (!aktualny()) return;
  if (hash.obec) {
    const obec = (await indexObci()).find((o) => o.kod === hash.obec);
    if (!aktualny()) return;
    if (obec) {
      await zobrazObec(obec, aktualny);
      return;
    }
    panel.removeAttribute("aria-busy");
  }
  vrstvaOkolia.vycisti();
  if (document.activeElement !== vstup) vstup.value = "";
  const okres = hash.okres ? okresPodlaKodu(hash.okres) : null;
  if (!okres && stav.priblizene) {
    zobrazSlovensko(mapa);
    stav.priblizene = false;
  }
  vrstvaOkresov.obnov({ vybrany: okres ? okres.properties.kod : null, priehladne: false, lenObrys: stav.vrstva === "obce" });
  if (okres) {
    vykresliOkres(panel, okres, stav.typ, meta, okresy.features.length);
    const hodnota = okres.properties[`${stav.typ.toLowerCase()}_${ukazovatelOkresov()}`];
    lista.zobraz(`Okres ${okres.properties.nazov}`, `${formatNa10k(hodnota)} ${popisUkazovatela()}`, () => panel.scrollIntoView());
  } else {
    panel.replaceChildren(...uvodPanela.map((uzol) => uzol.cloneNode(true)));
    lista.skry();
  }
}

function zobrazChybu(chyba) {
  panel.removeAttribute("aria-busy");
  legenda.replaceChildren();
  vykresliChybu(panel, `Skúste stránku obnoviť. Podrobnosti: ${chyba.message}`);
}

async function start() {
  [meta, okresy] = await Promise.all([nacitajJson("data/meta.json"), nacitajJson("data/okresy.geojson")]);
  stav.typ = platnyTyp(citajHash().typ);
  zobrazZastarane();
  mapa = vytvorMapu("mapa", meta);
  lista = new SpodnaLista(document.getElementById("lista"), document.getElementById("mapa"));
  pridajTlacidloSlovensko(mapa, () => {
    zobrazSlovensko(mapa);
    stav.priblizene = false;
    zapisHash({ obec: null, okres: null });
  });
  vrstvaOkresov = new VrstvaOkresov(mapa, okresy, {
    typ: () => stav.typ,
    ukazovatel: ukazovatelOkresov,
    popis: popisUkazovatela,
    hranice: () => meta.legenda[stav.typ],
    priKliknuti: (feature) => zapisHash({ okres: feature.properties.kod, obec: null }),
  });
  vrstvaObci = new VrstvaObci(mapa, (obec) => zapisHash({ obec: obec.kod, okres: null }));
  vrstvaOkolia = new VrstvaOkolia(mapa);
  document.querySelectorAll('input[name="typ"]').forEach((radio) => {
    radio.addEventListener("change", () => zapisHash({ typ: radio.value }));
  });
  document.querySelectorAll('input[name="vrstva"]').forEach((radio) => {
    radio.addEventListener("change", () => zapisHash({ vrstva: radio.value === "okresy" ? null : radio.value }));
  });
  nastavHladanie(vstup, document.getElementById("navrhy"), indexObci, (obec) => zapisHash({ obec: obec.kod, okres: null }));
  window.addEventListener("hashchange", () => aplikujStav().catch(zobrazChybu));
  await aplikujStav();
}

start().catch(zobrazChybu);
