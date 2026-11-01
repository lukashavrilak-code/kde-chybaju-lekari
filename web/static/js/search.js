import { bezDiakritiky, el } from "./util.js";

const MAX_NAVRHOV = 30;

function porovnajObce(x, y) {
  return x.nazov.localeCompare(y.nazov, "sk") || (x.okresNazov || "").localeCompare(y.okresNazov || "", "sk");
}

export function zoradNavrhy(obce, dotaz, max = MAX_NAVRHOV) {
  const presne = obce.filter((obec) => obec.kluc === dotaz);
  const zaciatok = obce.filter((obec) => obec.kluc !== dotaz && obec.kluc.startsWith(dotaz));
  const obsahuje = obce.filter((obec) => !obec.kluc.startsWith(dotaz) && obec.kluc.includes(dotaz));
  return [presne, zaciatok, obsahuje].flatMap((skupina) => skupina.sort(porovnajObce)).slice(0, max);
}

export function nastavHladanie(vstup, zoznam, nacitajIndex, priVybere) {
  let navrhy = [];
  let aktivny = -1;

  function zatvor() {
    zoznam.hidden = true;
    zoznam.replaceChildren();
    vstup.setAttribute("aria-expanded", "false");
    vstup.removeAttribute("aria-activedescendant");
    aktivny = -1;
  }

  function vyber(obec) {
    vstup.value = obec.nazov;
    zatvor();
    vstup.blur();
    priVybere(obec);
  }

  function zobrazSpravu(text) {
    navrhy = [];
    zoznam.replaceChildren(el("li", { text, atributy: { "aria-disabled": "true" } }));
    zoznam.hidden = false;
    vstup.setAttribute("aria-expanded", "true");
  }

  function vykresli() {
    if (!navrhy.length) {
      zobrazSpravu("Žiadna obec sa nenašla.");
      return;
    }
    zoznam.replaceChildren(
      ...navrhy.map((obec, i) => {
        const polozka = el(
          "li",
          { atributy: { role: "option", id: `navrh-${i}`, "aria-selected": String(i === aktivny) } },
          el("span", { text: obec.nazov }),
          el("span", { trieda: "okres", text: `okres ${obec.okresNazov}` }),
        );
        polozka.addEventListener("mousedown", (udalost) => {
          udalost.preventDefault();
          vyber(obec);
        });
        return polozka;
      }),
    );
    zoznam.hidden = false;
    vstup.setAttribute("aria-expanded", "true");
    if (aktivny >= 0) {
      vstup.setAttribute("aria-activedescendant", `navrh-${aktivny}`);
      document.getElementById(`navrh-${aktivny}`).scrollIntoView({ block: "nearest" });
    }
  }

  vstup.addEventListener("focus", () => nacitajIndex().catch(() => {}), { once: true });

  vstup.addEventListener("input", async () => {
    let data;
    try {
      data = await nacitajIndex();
    } catch {
      zobrazSpravu("Zoznam obcí sa nepodarilo načítať. Skúste stránku obnoviť.");
      return;
    }
    const dotaz = bezDiakritiky(vstup.value);
    if (dotaz.length < 2) {
      zatvor();
      return;
    }
    navrhy = zoradNavrhy(data, dotaz);
    aktivny = navrhy.length ? 0 : -1;
    vykresli();
  });

  vstup.addEventListener("keydown", (udalost) => {
    if (zoznam.hidden) return;
    if (udalost.key === "Escape") {
      zatvor();
      return;
    }
    if (!navrhy.length) return;
    if (udalost.key === "ArrowDown" || udalost.key === "ArrowUp") {
      udalost.preventDefault();
      const krok = udalost.key === "ArrowDown" ? 1 : -1;
      aktivny = (aktivny + krok + navrhy.length) % navrhy.length;
      vykresli();
    } else if (udalost.key === "Enter" && aktivny >= 0) {
      udalost.preventDefault();
      vyber(navrhy[aktivny]);
    }
  });

  vstup.addEventListener("blur", () => setTimeout(zatvor, 100));
}
