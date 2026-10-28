# Runbook

Všetky príkazy spúšťaj v priečinku projektu s aktivovaným prostredím (`.venv\Scripts\Activate.ps1`).

## Prvé nastavenie

1. V `config.toml` doplň `[projekt]` prevádzkovateľa a URL repozitára. Odkazy poisťovní (`[[web.poistovne]]`) sú vyplnené (O9).
2. Vytvor `config.local.toml` (nie je v Gite) s projektovým e-mailom. Používa ho Nominatim aj web:
   ```toml
   [projekt]
   kontakt_email = "..."
   ```
3. Stiahni hranice obcí ZBGIS do `data/raw/zbgis/` (O7).
4. Ručne exportuj zo STATdata tabuľku om7006rr (pohlavie Spolu, všetky obce, rok podľa `[obyvatelia] rok`) do dvoch súborov: `data/raw/statdata/om7006rr_0-17.csv` a `data/raw/statdata/om7006rr_18plus.csv`. Automatické sťahovanie je podľa podmienok STATdata zakázané. Pri novom roku uprav v `config.toml` `rok`, `stav_k` a kontrolné súčty `kontrola_deti_sr` a `kontrola_spolu_sr`. Windows niekedy skryje príponu a vznikne `.csv.csv`, vtedy súbor premenuj.
5. Súbor NCZI (`[nczi] url`) si pipeline stiahne sama pri prvom `python -m pipeline nczi` do `data/raw/nczi/`. Keď NCZI zverejní nový rok, uprav `url`, `rok`, `referencny_datum` a `kontrola_sr` a spusti `python -m pipeline nczi --force`.

## Pripomienka mesačnej aktualizácie (Plánovač úloh Windows)

Príkaz `python -m pipeline skontroluj` iba pozrie stránku ÚDZS (1 požiadavka, nič nesťahuje) a porovná odkaz s posledným snapshotom. Návratový kód: 0 = bez zmeny, 10 = nový register, 1 = chyba. Skript `scripts\skontroluj_register.ps1` pri kóde 10 alebo 1 zobrazí okno. Potom spustí zálohu (`python -m pipeline zaloha`) a pri jej chybe tiež zobrazí okno.

Úlohu vytvoríš raz v PowerShelli (spúšťa sa 3. deň v mesiaci o 9:00, ak si prihlásený):

```powershell
schtasks /Create /SC MONTHLY /D 3 /ST 09:00 /TN "Lekari - kontrola registra" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File D:\Lekari_data\scripts\skontroluj_register.ps1"
```

Zrušenie: `schtasks /Delete /TN "Lekari - kontrola registra"`.

## Mesačná aktualizácia (30 – 60 min)

1. `python -m pipeline download`. Pipeline nájde odkaz `VyberKpWeb_*.xlsx` na stránke ÚDZS, dátum stavu vezme z názvu súboru a snapshot uloží do `data/snapshots/udzs/RRRR-MM-DD.xlsx` s `.sha256`. Rovnaký súbor sa druhýkrát neuloží. Ak sa odkaz nenájde, použije sa záložná `[register] url` (WARN V1.0). Ak web ÚDZS sťahovanie blokuje, stiahni súbor ručne a pridaj `--subor cesta\k\suboru.xlsx`.
2. `python -m pipeline areas`, `validate`, `clean` a `nczi`. Skontroluj V3.8 (adresy bez obce, oprava v `data/manual/obec_mapping.csv`) a pomery NCZI (iba upozornenie).
3. `python -m pipeline geocode --nominatim`. Bez `--nominatim` geokódovanie číta iba cache. Nominatim dostane najviac 1 požiadavku za 1,1 s a tú istú adresu sa nepýta dvakrát. Prerušený beh môžeš spustiť znova. Prepínač `--max-dotazov N` obmedzí počet nových dotazov v jednom behu.
4. `python -m pipeline compute` a `export`.
5. Otvor `data/local/reports/validacia_RRRR-MM-DD.md`. Každý FAIL vyrieš, každý WARN vysvetli v `docs/overenia.md` alebo v metodike.
6. Otvor `data/local/reports/geokod_mimo_obce_RRRR-MM-DD.csv`. Stĺpec `riesenie` hovorí, čo pipeline urobila, keď prvý bod nepadol do obce z registra: „tolerancia pri hranici obce“, „iný kandidát v obci“, „stred obce“ (správna obec, nepresný bod) alebo „na ručnú kontrolu“. Pozri aj `geokod_kontrola_RRRR-MM-DD.csv` (adresy s presnosťou iba na obec). Sporné adresy dohľadaj ručne a zapíš do `data/manual/geocode_overrides.csv`. Súradnice ber z vlastného overenia alebo z mapy ZBGIS (https://zbgis.skgeodesy.sk), nie kopírovaním z OpenStreetMap, lebo súbor je v Gite. Potom spusti `geocode`, `compute` a `export`.
7. `python -m pipeline serve` a skontroluj web v prehliadači.
8. Commitni zmeny: história, ručné opravy, CHANGELOG. Cache geokódovania (`data/cache/`) do Gitu nepatrí. Potom `python -m pipeline export` (verzia sa zhoduje s commitom) a `python -m pipeline deploy`.
9. Po väčšej zmene (napr. po geokódovaní) môžeš hneď spustiť `python -m pipeline zaloha`. Inak sa záloha urobí sama raz mesačne.

## Záloha (automaticky)

Tieto súbory nie sú v Gite a bez nich sa práca nedá zopakovať bez nového sťahovania a geokódovania:

- `data/cache/` – cache geokódovania (súradnice z OpenStreetMap, ODbL),
- `data/snapshots/` – archív registra ÚDZS so SHA256,
- `data/raw/statdata/` a `data/raw/nczi/` – ručne exportované a stiahnuté zdroje,
- `data/local/blocklist.csv` a `data/local/ziadosti_log.csv` – žiadosti o skrytie,
- `config.local.toml` – projektový e-mail a cieľ zálohy.

Zoznam je v `config.toml [zaloha] polozky`. Cieľ je v `config.local.toml`:

```toml
[zaloha]
ciel = 'C:\Users\<používateľ>\OneDrive\Lekari_zaloha'
```

Na externý disk zmeň cestu, napr. `ciel = 'E:\Lekari_zaloha'`.

Príkaz `python -m pipeline zaloha` skopíruje nové a zmenené súbory. V cieli nič nemaže, takže tam ostanú aj staršie snapshoty. Úloha Plánovača úloh (pozri vyššie) ho spúšťa automaticky raz mesačne po kontrole registra. Ak cieľ nie je dostupný, napríklad keď nie je pripojený disk, zobrazí sa okno „Lekári – chyba zálohy“. Ručne kopírovať netreba.

Obnova: skopíruj priečinky zo zálohy späť do projektu (rovnaké cesty).

## Žiadosť o opravu alebo skrytie záznamu

Postup pre verejnosť je v metodike (časť „Oprava alebo odstránenie záznamu“). Žiadosti prichádzajú na projektový e-mail z `config.local.toml`.

1. Do 2 pracovných dní potvrď prijatie. Žiadosť zapíš do `data/local/ziadosti_log.csv` (dátum, typ, čo sa urobilo, dátum vybavenia).
2. Nájdi záznam: otvor `data/local/lekari.sqlite` (napr. v DB Browser for SQLite, keď pipeline nebeží) a vyhľadaj ho v pohľade `v_ambulancia` podľa názvu a adresy.
3. **Skrytie:** pridaj `pzs_kod` do `data/local/blocklist.csv` (stĺpce `pzs_kod,datum,typ_ziadosti`). **Chybná poloha:** pridaj riadok do `data/manual/geocode_overrides.csv`.
4. Spusti `python -m pipeline clean`, `geocode`, `compute` a `export`, skontroluj web a nasaď (`deploy`). Netreba nič sťahovať.
5. Odpovedz žiadateľovi do 5 pracovných dní. Ak je chyba v samotnom registri, uveď, že opravu treba žiadať aj u ÚDZS.

## Uchovávanie

Snapshoty registra v `data/snapshots/udzs/` sú archív (mimo Gitu). Raz za štvrťrok zmaž snapshoty staršie ako 12 mesiacov aj s ich `.sha256`. V SQLite zmaž riadky tabuľky `ambulancia` pre staré snapshoty. Agregovaná história v `data/history/` (vrátane hashov snapshotov) ostáva.
