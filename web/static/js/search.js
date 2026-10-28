import { bezDiakritiky, el } from "./util.js";

const MAX_NAVRHOV = 8;

export function nastavHladanie(vstup, zoznam, nacitajIndex, priVybere) {
  let index = null;
  let navrhy = [];
  let aktivny = -1;

  async function zabezpecIndex() {
    if (!index) index = await nacitajIndex();
    return index;
  }

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
    priVybere(obec);
  }

  function vykresli() {
    if (!navrhy.length) {
      zoznam.replaceChildren(el("li", { text: "Žiadna obec sa nenašla.", atributy: { "aria-disabled": "true" } }));
    } else {
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
    }
    zoznam.hidden = false;
    vstup.setAttribute("aria-expanded", "true");
    if (aktivny >= 0) vstup.setAttribute("aria-activedescendant", `navrh-${aktivny}`);
  }

  vstup.addEventListener("focus", () => zabezpecIndex(), { once: true });

  vstup.addEventListener("input", async () => {
    const data = await zabezpecIndex();
    const dotaz = bezDiakritiky(vstup.value);
    if (dotaz.length < 2) {
      zatvor();
      return;
    }
    const zaciatok = data.filter((obec) => obec.kluc.startsWith(dotaz));
    const obsahuje = data.filter((obec) => !obec.kluc.startsWith(dotaz) && obec.kluc.includes(dotaz));
    navrhy = zaciatok.concat(obsahuje).slice(0, MAX_NAVRHOV);
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
