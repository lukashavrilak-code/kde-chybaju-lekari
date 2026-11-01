import { el } from "./util.js";

export class SpodnaLista {
  constructor(kontajner, mapa) {
    this.kontajner = kontajner;
    this.mapa = mapa;
    this.mapaViditelna = true;
    this.priDetaile = null;
    this.nadpis = el("strong");
    this.riadok = el("span");
    this.tlacidlo = el("button", { trieda: "tlacidlo", atributy: { type: "button" } });
    this.tlacidlo.addEventListener("click", () => this.stlacene());
    kontajner.replaceChildren(el("div", { trieda: "lista-text" }, this.nadpis, this.riadok), this.tlacidlo);
    this.obnovTlacidlo();
    new IntersectionObserver((zaznamy) => {
      this.mapaViditelna = zaznamy[zaznamy.length - 1].isIntersecting;
      this.obnovTlacidlo();
    }, { threshold: 0.25 }).observe(mapa);
  }

  obnovTlacidlo() {
    this.tlacidlo.textContent = this.mapaViditelna ? "Detail ↓" : "↑ Mapa";
  }

  stlacene() {
    if (this.mapaViditelna) this.priDetaile();
    else this.mapa.scrollIntoView({ block: "start" });
  }

  zobraz(nadpis, riadok, priDetaile) {
    this.nadpis.textContent = nadpis;
    this.riadok.textContent = riadok;
    this.priDetaile = priDetaile;
    this.kontajner.hidden = false;
    document.body.classList.add("ma-listu");
  }

  skry() {
    this.kontajner.hidden = true;
    document.body.classList.remove("ma-listu");
  }
}
