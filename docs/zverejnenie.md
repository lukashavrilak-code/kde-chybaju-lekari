# Zverejnenie

Stav: **pripravené, zatiaľ nezverejnené.** Vzdialený repozitár sa vytvára až po výslovnom súhlase autora (`CLAUDE.md`).

## 1. Rozhodnutia autora (1. 11. 2026)

| Téma | Rozhodnutie | Prečo |
|---|---|---|
| Hosting | GitHub Pages, nasadenie cez GitHub Actions, bez vetvy `gh-pages` | V balíku sú adresy a súradnice odvodené z OSM, ktoré nemajú ísť do Gitu. Staré verzie po force-pushi by v Gite ostali dostupné. |
| Názvy poskytovateľov | prvá verzia bez názvov (`[zverejnit] nazvy = false`) | LIA a informácia podľa čl. 14 GDPR nemajú právnu kontrolu (O12, O19, O21). Názvy sa zapnú až po nej. |
| Interné texty | `CLAUDE.md` a Co-Authored-By ostávajú, v README je veta o vzniku s AI, história sa neprepisuje | otvorenosť |
| Adresa | `https://lukashavrilak-code.github.io/kde-chybaju-lekari/` | účet autora, názov zodpovedá webu |

Autor vystupuje pod vlastným menom (O19), e-mail v commitoch je projektový (rozhodnutie z 28. 10. 2026).

## 2. Ako funguje nasadenie

1. `python -m pipeline deploy` skontroluje `deploy_problems` (žiadne umelé dáta ani FAIL, čistý Git, commit odoslaný do `origin/main`, žiadne názvy) a zabalí `site/` do `build/site.tar.gz`.
2. Balík nahrá do vydania `web-balik`, ktoré je vždy **draft**. Draft vidia iba ľudia s právom zápisu. Ak by `web-balik` nebol draft, nasadenie sa zastaví.
3. Spustí workflow `.github/workflows/nasadenie.yml`, ktorý balík stiahne a nasadí na Pages. Artefakt workflow sa uchováva 1 deň.

V repozitári nie je žiadny token. `gh` sa prihlasuje cez `gh auth login`, workflow používa krátkodobý `GITHUB_TOKEN`.

## 3. Prvé zverejnenie

Jednorazovo:

1. GitHub: zapnúť dvojfaktorové overenie. V Settings → Emails pridať a overiť projektový e-mail, aby sa commity priradili k profilu. Voľbu „Block command line pushes that expose my email“ nechať vypnutú.
2. `winget install GitHub.cli` a `gh auth login`.

Postup:

3. `python -m pytest -q`, `ruff check .`, `python scripts/check_repo.py`.
4. `python -m pipeline skontroluj`. Ak je nový register, mesačná aktualizácia podľa runbooku.
5. `gh repo create lukashavrilak-code/kde-chybaju-lekari --public --source . --push`.
6. Počkať na zelené CI.
7. Nastavenia repozitára:
   - Pages: zdroj GitHub Actions,
   - Actions: iba akcie od GitHubu, token iba na čítanie,
   - Dependabot alerts, secret scanning, push protection, súkromné hlásenie zraniteľností,
   - pravidlo pre `main`: zákaz force-push a zmazania,
   - vypnúť Wiki a Projects.
8. `python -m pipeline export` a kontrola náhľadu na počítači aj telefóne.
9. `python -m pipeline deploy` a `gh run watch`.
10. Kontrolný zoznam v `docs/runbook.md` na verejnej adrese.

**Návrat späť:** Pages sa dajú vypnúť v nastaveniach repozitára a repozitár sa dá zmeniť na súkromný.

## 4. Čo čakať

- Web beží na HTTPS s platným certifikátom bez nastavovania. Nič nenačítava cez `http://`, nemá formuláre ani spustiteľné súbory.
- GitHub Pages neumožňuje vlastné HTTP hlavičky, preto CSP je v `<meta>` a nástroje ako securityheaders.com dajú nízke hodnotenie. Návštevník to nevidí.
- Limity: web najviac 1 GB (má asi 2 MB), mäkký limit 100 GB prenosu mesačne, nie na komerčné použitie.

## 5. Otvorené témy

| Téma | Čo riešiť | Kde |
|---|---|---|
| Právo | kontrola textov právnikom pred zapnutím názvov | O12, O19, O21, O22, O23, `docs/lia.md` |
| Dáta | adresy s presnosťou iba obec, overenie významu útvaru NCZI a menovateľa T2.9 | `data/manual/geocode_overrides.csv`, O8, O13, O20 |
| Údržba | mesačná aktualizácia, inak web po 60 dňoch ukáže upozornenie na staré dáta | `docs/runbook.md` |
