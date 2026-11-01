import { el, formatCislo, formatDatum, formatKm, formatNa10k, formatPercento } from "./util.js";

const PRESNOST = {
  adresa: "presná adresa",
  ulica: "približná (ulica)",
  obec: "približná (stred obce)",
  rucne: "ručne overená",
};
const NA_STRANU = 20;

function info(kotva, popis) {
  return el("a", { text: "ⓘ", atributy: { href: `metodika.html#${kotva}`, title: popis, "aria-label": popis } });
}

function riadok(nazov, hodnota, kotva) {
  const dt = el("dt", { text: nazov + " " });
  if (kotva) dt.append(info(kotva, `Definícia: ${nazov}`));
  return [dt, el("dd", { text: hodnota })];
}

export function vykresliOkres(panel, okres, typ, meta, pocetOkresov) {
  const p = okres.properties;
  const prefix = typ.toLowerCase();
  const pocet = p[`${prefix}_pocet`];
  const suhrn = el(
    "dl",
    { trieda: "suhrn" },
    ...riadok("Ambulancie v okrese", formatCislo(pocet), "u1"),
    ...riadok("Pracoviská (rovnaké IČO a adresa)", formatCislo(p[`${prefix}_pracoviska`]), "u6"),
    ...riadok(`Na 10 000 ${meta.menovatele[typ]}`, formatNa10k(p[`${prefix}_na10k`]), "u2"),
    ...riadok("Poradie (1 = najmenej)", `${p[`${prefix}_poradie`]}. z ${pocetOkresov}`, "u5"),
    ...riadok(
      `V okolí ${meta.spadova_oblast_km} km: na 10 000 ${meta.menovatele[typ]}`,
      `${formatNa10k(p[`${prefix}_okolie`])} (${p[`${prefix}_poradie_okolie`]}. z ${pocetOkresov})`,
      "u8",
    ),
    ...meta.podiel_nad_km.flatMap((km) =>
      riadok(`Podiel ${meta.menovatele[typ]} ďalej ako ${km} km`, formatPercento(p[`${prefix}_nad${km}`]), "u7"),
    ),
  );
  const casti = [
    el("h2", { text: `Okres ${p.nazov}` }),
    el("p", { trieda: "poznamka", text: `${p.kraj} · ${meta.nazvy_typov[typ]}` }),
    suhrn,
  ];
  if (meta.mestske_okresy.includes(p.kod)) {
    casti.push(el(
      "p",
      {
        trieda: "poznamka",
        text: `Mestský okres: ľudia môžu chodiť k lekárovi aj do iného okresu mesta, výstižnejší je preto ukazovateľ v okolí ${meta.spadova_oblast_km} km. `,
      },
      el("a", { text: "Viac o mestských okresoch", atributy: { href: "rebricky.html#mestske-okresy" } }),
    ));
  }
  if (pocet < 10) {
    casti.push(el("p", { trieda: "poznamka", text: "Malé čísla: jedna ambulancia navyše alebo menej mení hodnotu výrazne." }));
  }
  casti.push(el("p", null, el("a", { text: "Poradie všetkých okresov", atributy: { href: "rebricky.html" } })));
  casti.push(el("p", { trieda: "poznamka", text: "Vyhľadajte obec a uvidíte najbližšie ambulancie." }));
  panel.replaceChildren(...casti);
}

function nazovKarty(a) {
  return a.nazov || a.adresa || "Adresa ambulancie v registri chýba.";
}

function karta(zaznam, meta) {
  const a = zaznam.ambulancia;
  const casti = [el("h3", { text: nazovKarty(a) })];
  if (a.nazov) casti.push(el("p", { text: a.adresa || "Adresa ambulancie v registri chýba." }));
  casti.push(el("p", { text: `${formatKm(zaznam.km)} vzdušnou čiarou` }));
  if (a.pocet > 1) casti.push(el("p", { text: `Ambulancií v registri na tejto adrese: ${formatCislo(a.pocet)}` }));
  casti.push(el("p", { trieda: "tlmene", text: `Poloha: ${PRESNOST[a.presnost] || a.presnost}` }));
  casti.push(el("p", null, el("a", {
    text: "Otvoriť v mape ↗",
    atributy: {
      href: `https://www.openstreetmap.org/?mlat=${a.lat}&mlon=${a.lon}#map=17/${a.lat}/${a.lon}`,
      target: "_blank",
      rel: "noopener noreferrer",
    },
  })));
  if (meta.poistovne.length) {
    const odkazy = meta.poistovne.map((poistovna) =>
      el("li", null, el("a", {
        text: `${poistovna.nazov} ↗`,
        atributy: { href: poistovna.url, target: "_blank", rel: "noopener noreferrer" },
      })),
    );
    casti.push(el(
      "details",
      null,
      el("summary", { text: a.nazov ? "Kontakt a ordinačné hodiny" : "Názov, kontakt a ordinačné hodiny" }),
      el("p", { trieda: "tlmene", text: "Oficiálne vyhľadávanie lekárov zdravotných poisťovní:" }),
      el("ul", { trieda: "poistovne" }, ...odkazy),
    ));
  }
  if (meta.kontakt_email) {
    const predmet = encodeURIComponent(`Oprava záznamu: ${[a.nazov, a.adresa].filter(Boolean).join(", ")}`);
    casti.push(el("p", null, el("a", {
      text: "Nahlásiť chybu v zázname",
      atributy: { href: `mailto:${meta.kontakt_email}?subject=${predmet}` },
    })));
  }
  return el("article", { trieda: "karta" }, ...casti);
}

export function najblizsia(zoznam, typ) {
  return zoznam.find((zaznam) => zaznam.ambulancia.typ === typ) || null;
}

export function vykresliObec(panel, obec, okres, typ, meta, vsetkyVOkoli, priVybereKarty) {
  const [r1, r2] = meta.polomery_km;
  const casti = [
    el("h2", { text: obec.nazov }),
    el("p", { trieda: "poznamka", text: okres ? `okres ${okres.properties.nazov}` : "" }),
  ];
  for (const t of meta.typy) {
    const prva = najblizsia(vsetkyVOkoli, t);
    const prefix = t.toLowerCase();
    const vObci = obec[`${prefix}_v_obci`] || 0;
    casti.push(el("h3", { text: meta.nazvy_typov[t] }));
    casti.push(el(
      "dl",
      { trieda: "suhrn" },
      ...riadok("Najbližšia ambulancia", formatKm(prva ? prva.km : obec[`${prefix}_km`]), "u3"),
      ...riadok(`Do ${r1} km`, formatCislo(obec[`${prefix}_${r1}`]), "u4"),
      ...riadok(`Do ${r2} km`, formatCislo(obec[`${prefix}_${r2}`]), "u4"),
      ...(okres ? riadok(`Okres: na 10 000 ${meta.menovatele[t]}`, formatNa10k(okres.properties[`${prefix}_na10k`]), "u2") : []),
    ));
    if (prva) {
      const nazov = [prva.ambulancia.nazov, prva.ambulancia.adresa].filter(Boolean).join(", ");
      casti.push(el("p", { trieda: "poznamka", text: `Najbližšia: ${nazov}` }));
    }
    if (vObci) casti.push(el("p", { trieda: "poznamka", text: `Priamo v obci: ${formatCislo(vObci)}` }));
  }

  const zoznam = vsetkyVOkoli.filter((zaznam) => zaznam.ambulancia.typ === typ);
  casti.push(el("h3", { text: `Ambulancie do ${meta.max_zoznam_km} km: ${meta.nazvy_typov[typ].toLowerCase()}` }));
  casti.push(el("p", {
    trieda: "poznamka",
    text: `Údaje z registra ÚDZS, stav k ${formatDatum(meta.stav_registra)}. Register neuvádza, či ambulancia prijíma nových pacientov, ordinačné hodiny ani počet lekárov. Overte si to u svojej zdravotnej poisťovne.`,
  }));
  if (!meta.nazvy) {
    casti.push(el("p", { trieda: "poznamka", text: "Názvy poskytovateľov nezobrazujeme. Nájdete ich vo vyhľadávaní lekárov zdravotných poisťovní." }));
  }
  const kontajner = el("div");
  casti.push(kontajner);
  let zobrazene = 0;
  const tlacidlo = el("button", { trieda: "tlacidlo", text: "Zobraziť ďalšie", atributy: { type: "button" } });
  const karty = [];

  function pridaj() {
    const dalsie = zoznam.slice(zobrazene, zobrazene + NA_STRANU);
    dalsie.forEach((zaznam) => {
      const k = karta(zaznam, meta);
      k.addEventListener("click", () => priVybereKarty(zaznam.index));
      karty[zaznam.index] = k;
      kontajner.append(k);
    });
    zobrazene += dalsie.length;
    tlacidlo.hidden = zobrazene >= zoznam.length;
  }

  if (!zoznam.length) kontajner.append(el("p", { text: `Do ${meta.max_zoznam_km} km nie je v registri žiadna takáto ambulancia.` }));
  tlacidlo.addEventListener("click", pridaj);
  casti.push(tlacidlo);
  pridaj();
  panel.replaceChildren(...casti);
  panel.scrollTop = 0;

  return function zvyrazniKartu(indexy, posunut) {
    while (Math.max(...indexy) >= zobrazene && zobrazene < zoznam.length) pridaj();
    karty.forEach((k, i) => {
      if (k) k.classList.toggle("aktivna", indexy.includes(i));
    });
    const prva = karty[indexy[0]];
    if (posunut) prva.scrollIntoView({ block: "nearest", behavior: "smooth" });
    return prva;
  };
}

export function vykresliChybu(panel, sprava) {
  panel.replaceChildren(el("h2", { text: "Údaje sa nepodarilo načítať" }), el("p", { text: sprava }));
}
