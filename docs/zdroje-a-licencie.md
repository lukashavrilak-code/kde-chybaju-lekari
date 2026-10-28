# Zdroje dát a licencie

| Zdroj | Použitie | Licencia / podmienky | Stav overenia |
|---|---|---|---|
| ÚDZS – Kódy poskytovateľov zdravotnej starostlivosti (XLSX) | ambulancie: názov, odbornosť, adresa, platnosť | licencia neuvedená | e-mail ÚDZS sa neposiela (rozhodnutie autora, 27. 10. 2026); odkaz na súbor sa hľadá na stránke ÚDZS raz mesačne (O4) |
| Štatistický úrad SR – STATdata, tabuľka om7006rr | obyvatelia obcí 0 – 17 a 18+ (menovateľ) | CC BY 4.0, atribúcia „Zdroj: Štatistický úrad SR, CC BY 4.0, www.statistics.sk“ | automatické sťahovanie zo STATdata je podľa podmienok zakázané, súbory sa exportujú ručne a pipeline ich iba číta (O5) |
| ÚGKK SR – ZBGIS, hranice územných jednotiek | hranice obcí a okresov, katastrálne územia na priradenie miestnych častí | CC BY 4.0 | atribúcia „© ÚGKK SR, ZBGIS, CC BY 4.0, zjednodušené“ |
| OpenStreetMap – Nominatim | súradnice adries ambulancií | ODbL, Nominatim Usage Policy | OVERIŤ OSMF Geocoding Guideline; atribúcia ODbL v `ambulancie.json` a na stránke Dáta |
| OpenStreetMap – mapové dlaždice | podkladová mapa | Tile Usage Policy | atribúcia na mape; OVERIŤ požiadavku na Referer |
| NCZI – výstup S01 o sieti poskytovateľov 2024, tabuľky T2 | iba kontrola počtov po krajoch | citovať zdroj | jednotka „Počet útvarov“, stav k 31. 12. 2024; OVERIŤ, či útvar = jeden kód PZS (O8) |
| Leaflet 1.9.4 | mapová knižnica | BSD-2-Clause | text licencie v `web/static/vendor/leaflet-1.9.4/LICENSE` |

## Naše výstupy

- Kód: MIT.
- Vypočítané ukazovatele (CSV): navrhujeme CC BY 4.0. OVERIŤ zlučiteľnosť s podmienkami ÚDZS (licencia neuvedená).
- Súradnice ambulancií sú odvodené z OSM, preto ich šírime s atribúciou ODbL. Zverejňujeme ich iba na webe (`ambulancie.json`). Cache geokódovania (`data/cache/`, dotazy a súradnice z Nominatimu) sa do repozitára nedáva (rozhodnutie autora, 27. 10. 2026).
- Ručné opravy polohy (`data/manual/geocode_overrides.csv`, v Gite) majú súradnice z vlastného overenia alebo z mapy ZBGIS, nie z OSM.
