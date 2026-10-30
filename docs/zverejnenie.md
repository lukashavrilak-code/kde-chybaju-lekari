# Zverejnenie – možnosti a otvorené témy

Stav: **nič nie je zverejnené.** Repozitár nemá vzdialený repozitár (`git remote` je prázdny) a `pipeline deploy` sa nespúšťal. Tento súbor iba zapisuje možnosti, aby sa dalo rozhodnúť neskôr. Rozhodnutia sa zapisujú sem alebo do `docs/overenia.md` (dátum, čo a prečo).

## 1. Cieľ

- Funkčný verejný odkaz na web s reálnymi dátami, bez platby a bez vlastnej domény.
- Odkaz má slúžiť aj ako ukážka práce, autorstvo sa preukáže GitHub účtom.

## 2. Možnosti hostingu

Web je statický (HTML, JSON, CSV), takže stačí ľubovoľný statický hosting. Podmienky bezplatných plánov treba pred výberom OVERIŤ.

| Možnosť | Adresa | Výhody | Nevýhody |
|---|---|---|---|
| **GitHub Pages** (odporúčané) | `<ucet>.github.io/<repozitar>/` | už pripravené (`python -m pipeline deploy`, `ghp-import`, vetva `gh-pages`), CI zadarmo, kód aj web na jednom mieste | verejný repozitár, servery v USA (O12), HTTP hlavičky sa nedajú nastaviť, CSP je iba v `<meta>` |
| Cloudflare Pages | `<projekt>.pages.dev` | vlastné HTTP hlavičky (`_headers`), rýchla sieť | ďalší účet, iný postup nasadenia |
| Netlify | `<projekt>.netlify.app` | `_headers`, jednoduché nahratie priečinka | limity bezplatného plánu, ďalší účet |
| Codeberg Pages | `<ucet>.codeberg.page` | nezisková organizácia, servery v EÚ (lepšie pre O12) | menej známe, iný postup nasadenia |

Odporúčanie: GitHub Pages. Ostatné možnosti sú záloha, ak by bol problém s O12 alebo s hlavičkami.

## 3. Čo treba pred prvým `git push`

- **E-mail autora commitov** je projektový e-mail (rozhodnutie autora z 28. 10. 2026). Nesmie obsahovať meno.
- **`LICENSE`:** riadok `[DOPLŇ MENO AUTORA]` nahradiť menom autora.
- **`config.toml [projekt]`:** `prevadzkovatel`, `web_url`, `repozitar_url`.
- **Projektový e-mail** bude viditeľný na webe (Súkromie, Metodika).
- `pipeline deploy` odmietne nasadiť web, ak niektorá stránka obsahuje `[DOPLŇ …]`.

## 4. Kroky zverejnenia (keď autor rozhodne)

1. Kontrola histórie: `git log --all -p` neobsahuje názvy poskytovateľov z databázy ani meno autora. Spustiť `python scripts/check_repo.py`, `ruff check .` a `python -m pytest -q`.
2. Vytvoriť verejný repozitár na GitHube a `git push`.
3. Reálny beh pipeline podľa `docs/runbook.md` a `python -m pipeline deploy`.
4. GitHub: Settings → Pages → vetva `gh-pages`, priečinok root.
5. Prejsť kontrolný zoznam v `docs/sprievodca.md` (počítač aj telefón) na verejnej adrese.

Vytvorenie verejného repozitára a nasadenie sa robí iba po výslovnom súhlase autora (`CLAUDE.md`).

## 5. Otvorené témy

| Téma | Čo riešiť | Kde |
|---|---|---|
| Funkčnosť | kontrolný zoznam prehliadky (počítač a telefón) je celý nezaškrtnutý; 404 pri vnorenej ceste | `docs/sprievodca.md`, časť 1 |
| Praktickosť | mesačná aktualizácia, upozornenie na staré dáta po 60 dňoch; adresy s presnosťou iba obec (`data/manual/geocode_overrides.csv` je prázdny); Plánovač úloh a cieľ zálohy | `docs/runbook.md`, O17 |
| Legálnosť | O10 (podmienky OSM: dlaždice, Nominatim, ODbL), O12 (IP adresy do USA), O19 (uvedenie prevádzkovateľa), licencia CSV vs. podmienky ÚDZS, LIA na kontrolu právnikom | `docs/overenia.md`, `docs/zdroje-a-licencie.md`, `docs/lia.md` |
| Architektúra | voľba hostingu (časť 2), CSP v `<meta>` vs. HTTP hlavičky, nasadenie cez `ghp-import` vs. GitHub Actions, záložný geokóder (O13) | `pipeline/deploy.py`, `pipeline/site.py` |
| Optimalizácia | `okresy.geojson` má 249 KB pri limite 250 KB (V6.2). Pred ďalším údajom o okresoch napr. `zjednodusenie_okresy_m` 250 → 300 | `config.toml` |
