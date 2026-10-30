# Zmeny

Verzia pipeline: MAJOR.MINOR.PATCH. Zmena definície ukazovateľa zvyšuje MINOR a zapisuje sa aj do histórie zmien v metodike.

## 0.1.0 – 2026-10 (nevydané)

- Prvá verzia: kroky download, validate, clean, areas, nczi, geocode, compute, export, deploy.
- Ukazovatele U1 až U5 (okresy na 10 000 obyvateľov, vzdialenosti a počty v okolí obcí, poradie okresov).
- Statický web: mapa okresov, vyhľadanie obce, zoznam ambulancií, rebríčky, dáta, metodika, súkromie.
- Umelé testovacie dáta a testy.
- Register ÚDZS: odkaz na súbor sa hľadá na stránke ÚDZS, snapshoty v `data/snapshots/udzs/` so SHA256, rovnaký súbor sa neuloží dvakrát. Príkaz `skontroluj` na mesačnú pripomienku.
- Obyvatelia zo STATdata (om7006rr, 2025, ručný export 0–17 a 18+), spojenie so ZBGIS podľa okresu a názvu, kontrolné súčty za SR, desatinné menovatele.
- Kontrola s NCZI S01 2024 priamo z XLSX (počet útvarov, kraje), iba WARN; report rozdielu register vs. NCZI.
- Obec z adresy v registri (`adresa_obec`): kraj pre porovnanie s NCZI a prísna kontrola, či bod leží v obci z registra.
- Geokódovanie cez Nominatim iba s prepínačom `--nominatim`.
- Projektový e-mail v `config.local.toml` mimo Gitu; odkazy na vyhľadávanie lekárov poisťovní.
- Doplnkový ukazovateľ U6 „počet pracovísk“ (rovnaké IČO + adresa) v paneli okresu, rebríčkoch, CSV a metodike.
- Geokódovanie: bod musí ležať v obci z registra (tolerancia 300 m), inak sa skúša dotaz obmedzený na obec, obec + PSČ a stred obce; upravené znenia adries (bez „ul.“ a „č.“, prehodené číslo, obce bez ulíc); limit `--max-dotazov`; report s riešením nezhody.
- Ulica „null“ z registra sa berie ako prázdna. Myslenice → Pezinok.
- Cache geokódovania mimo Gitu. Príkaz `zaloha` (cache, snapshoty, ručné zdroje do OneDrive/na disk) spúšťaný mesačne z Plánovača úloh. Upozornenie NCZI iba pri pomere mimo 0,8 – 1,6. Text „stredný stav 2025“ pri obyvateľoch.
- `serve --host 0.0.0.0`: náhľad webu z telefónu v domácej sieti. Sprievodca projektom (`docs/sprievodca.md`). Úloha Plánovača úloh sa spustí aj na batérii a dobehne zmeškaný termín.
- Referenčný bod obce je bod sídla zo ZBGIS (Geografické názvy, vrstva GNO), nie geometrický stred územia (O18). Nový ukazovateľ U7: podiel obyvateľov okresu ďalej ako 5 a 10 km od ambulancie (panel okresu, CSV, metodika). Na mape prepínač „Obce podľa vzdialenosti“. Kontroly V3.9 a V5.6.
- Ukazovateľ U8: ambulancie v okolí 10 km na 10 000 obyvateľov (2SFCA) na mape, v paneli okresu, v rebríčkoch a v CSV; kontrola V5.7 (všetky ambulancie sa rozdelia presne raz). Poznámka k mestským okresom Bratislavy a Košíc v rebríčkoch a v paneli. Tabuľky rebríčkov sa na úzkej obrazovke posúvajú vodorovne.
- Farby mapy: tmavšia farba = viac ambulancií (okresy), resp. bližšie k ambulancii (obce). Mapa sa kreslí na canvas, takže vrstva obcí je plynulejšia a body sa ľahšie trafia na telefóne. Body obcí sa dajú vybrať aj v okrese vybranej obce.
