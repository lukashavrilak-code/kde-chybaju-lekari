# Pokyny pre Claude Code

Projekt: neoficiálna mapa dostupnosti lekárov prvého kontaktu na Slovensku.

## Štýl
- Komunikácia po slovensky, technické termíny môžu byť po anglicky.
- Moduly a funkcie po anglicky, dátové kľúče, stĺpce a texty webu po slovensky.
- Jednoduchosť a čitateľnosť pred eleganciou. Bez zbytočných komentárov v kóde, vysvetlenia patria do `docs/`.
- Súbory vždy otvárať s `encoding="utf-8"`.

## Pravidlá (záväzné)
- Do Gitu nikdy nesmú ísť mená poskytovateľov: `data/raw`, `data/local`, `data/snapshots`, `site`, `build` sú mimo Gitu. Mimo Gitu je aj `data/cache` (súradnice z OpenStreetMap, rozhodnutie autora). Testy používajú iba vymyslené názvy (`pipeline/fixtures.py`).
- Projektový e-mail je iba v `config.local.toml` (mimo Gitu), nikdy ho nepíš do súborov v Gite. Výnimka: je autorom commitov (lokálny `git config user.email` tohto repozitára, rozhodnutie autora 28. 10. 2026).
- Zobrazovať iba názov poskytovateľa, adresu a odbornosť z registra. Netvrdiť nič, čo register neobsahuje.
- Nescrapovať weby poisťovní ani iné weby. Kontakty riešiť iba odkazom. Výnimka: zo stránky ÚDZS s kódmi poskytovateľov sa raz mesačne načíta iba zoznam odkazov a vyberie sa odkaz VyberKpWeb_*.xlsx.
- STATdata sa nesmie sťahovať automaticky (podmienky ŠÚ SR), pipeline iba číta ručne exportované súbory.
- Nominatim: pri mesačných (pravidelných) behoch najviac 4 požiadavky za minútu (`interval_s = 15`, podmienky OSM), nikdy viac ako 1 za sekundu, cache, tú istú adresu nikdy dvakrát. Hromadné geokódovanie, vytvorenie verejného repozitára a nasadenie robiť iba po výslovnom súhlase autora.
- Na webe žiadne `innerHTML` a pod. (kontroluje `scripts/check_repo.py`), žiadne inline skripty ani štýly (CSP v `pipeline/site.py`).
- Neoverené fakty označovať „OVERIŤ“ a zapisovať do `docs/overenia.md`.

## Príkazy
- `python -m pipeline all --fixtures` – celý beh na umelých dátach
- `python -m pipeline download | areas | validate | clean | nczi` – reálne kroky bez geokódovania
- `python -m pipeline geocode --nominatim [--max-dotazov N]` – geokódovanie cez Nominatim (iba po súhlase autora; bez prepínača iba z cache)
- `python -m pipeline skontroluj` – je na stránke ÚDZS nový register? (0 = nie, 10 = áno)
- `python -m pipeline zaloha` – kópia dát mimo Gitu (cache, snapshoty…) do cieľa z `config.local.toml`
- `python -m pytest -q` – testy
- `python scripts/check_repo.py` a `ruff check .` – kontroly
- Plán architektúry: `docs/` + README; prahy a nastavenia v `config.toml`
