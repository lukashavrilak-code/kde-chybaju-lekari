# Zdroje dát a licencie

| Zdroj | Použitie | Licencia / podmienky | Stav overenia |
|---|---|---|---|
| ÚDZS – Kódy poskytovateľov zdravotnej starostlivosti (XLSX) | ambulancie: odbornosť, adresa, platnosť; názov iba lokálne, na web nejde | licencia neuvedená | e-mail ÚDZS sa neposiela (rozhodnutie autora, 27. 10. 2026); odkaz na súbor sa hľadá na stránke ÚDZS raz mesačne (O4) |
| Štatistický úrad SR – STATdata, tabuľka om7006rr | obyvatelia obcí 0 – 17 a 18+ (menovateľ) | CC BY 4.0, atribúcia „Zdroj: Štatistický úrad SR, CC BY 4.0, www.statistics.sk“ | automatické sťahovanie zo STATdata je podľa podmienok zakázané, súbory sa exportujú ručne a pipeline ich iba číta (O5) |
| ÚGKK SR – ZBGIS, hranice územných jednotiek | hranice obcí a okresov, katastrálne územia na priradenie miestnych častí | CC BY 4.0 | atribúcia „© ÚGKK SR, ZBGIS, CC BY 4.0, zjednodušené“ |
| ÚGKK SR – ZBGIS, Geografické názvy (vrstva GNO) | bod sídla každej obce = referenčný bod obce pre vzdialenosti (U3, U4, U7) | CC BY 4.0, autor GKÚ Bratislava | `https://opendata.skgeodesy.sk/static/ZBGIS/gn/gn_gpkg.zip`, ručne stiahnuté do `data/raw/zbgis/gn/`; atribúcia v pätičke webu spolu s hranicami (O18) |
| OpenStreetMap – Nominatim | súradnice adries ambulancií | ODbL, Nominatim Usage Policy, OSMF Geocoding Guideline | overené (O10); atribúcia ODbL v `ambulancie.json`, v pätičke a na stránke Dáta |
| OpenStreetMap – mapové dlaždice | podkladová mapa | Tile Usage Policy | overené (O10); atribúcia na mape, prehliadač posiela Referer |
| NCZI – výstup S01 o sieti poskytovateľov 2024, tabuľky T2 | kontrola počtov po krajoch, úväzky lekárov po krajoch (U9) | citovať zdroj | stĺpce „Počet útvarov“ a „Počet pracovných miest – Lekári“, stav k 31. 12. 2024; OVERIŤ, či útvar = jeden kód PZS (O8) |
| Leaflet 1.9.4 | mapová knižnica | BSD-2-Clause | text licencie v `web/static/vendor/leaflet-1.9.4/LICENSE` |

## Naše výstupy

- Kód: MIT.
- Vypočítané ukazovatele (CSV): navrhujeme CC BY 4.0. OVERIŤ zlučiteľnosť s podmienkami ÚDZS (licencia neuvedená).
- Súradnice ambulancií sú odvodené z OSM, preto ich šírime s atribúciou ODbL. Zverejňujeme ich iba na webe (`ambulancie.json`), do Gitu nejdú ani pri nasadení (GitHub Actions, bez vetvy `gh-pages`). Cache geokódovania (`data/cache/`, dotazy a súradnice z Nominatimu) sa do repozitára nedáva (rozhodnutie autora, 27. 10. 2026).
- Ručné opravy polohy (`data/manual/geocode_overrides.csv`, v Gite) majú súradnice z vlastného overenia alebo z mapy ZBGIS, nie z OSM.
