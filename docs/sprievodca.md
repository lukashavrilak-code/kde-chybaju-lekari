# Sprievodca projektom

Tento text vysvetľuje, ako web funguje, čo robí pipeline a ako sa počítajú ukazovatele. Presné definície ukazovateľov sú v [metodike](metodika.md), postup mesačnej aktualizácie v [runbooku](runbook.md). Tu je to isté vysvetlené jednoduchšie a s odkazmi do kódu.

Odporúčané poradie: najprv si pozri web (časť 1), potom spusti pipeline na umelých dátach (časť 2) a až potom čítaj ostatné časti.

## 1. Prehliadka webu

### Spustenie náhľadu

```powershell
python -m pipeline serve                    # reálne dáta na http://127.0.0.1:8000
python -m pipeline serve --fixtures         # umelé dáta (časť 2)
python -m pipeline serve --host 0.0.0.0     # náhľad aj z telefónu v domácej Wi-Fi
```

Pri `--host 0.0.0.0` príkaz vypíše adresu, ktorú otvoríš v telefóne (napr. `http://192.168.1.20:8000/`). Treba pri tom:

- pri prvom spustení povoliť Python vo Windows Firewall iba pre **súkromné siete**,
- mať domácu Wi-Fi vo Windows nastavenú ako súkromnú sieť,
- mať telefón v tej istej Wi-Fi.

Náhľad používaj iba doma a po skončení ho zastav klávesmi Ctrl+C. Nič sa tým nezverejňuje.

### Čo je na ktorej stránke

| Stránka | Čo ukazuje | Šablóna | JavaScript | Dáta |
|---|---|---|---|---|
| Mapa | okresy zafarbené podľa U2 alebo U8, obce podľa vzdialenosti (U3), legenda, panel okresu a obce, vyhľadanie obce | `index.html` | všetky moduly | `meta.json`, `okresy.geojson`, neskôr `obce.json` a `ambulancie.json` |
| Rebríčky | 10 najhorších okresov podľa U2 a podľa U8, 10 najlepších podľa U2, celé poradie s pracoviskami a U8, poznámka k mestským okresom | `rebricky.html` | žiadny | vypočítané v Pythone pri exporte |
| Dáta | CSV na stiahnutie a popis stĺpcov | `data.html` | žiadny | `downloads/*.csv` |
| Metodika | text z `docs/metodika.md` a tabuľka „Aktuálny stav dát“ | `metodika.html` | žiadny | – |
| Súkromie | text z `docs/sukromie.md`, prevádzkovateľ a kontakt | `sukromie.html` | žiadny | – |
| 404 | stránka pre neexistujúcu adresu | `404.html` | žiadny | – |

Šablóny sú vo `web/templates/`. Všetky dedia z `base.html`: hlavička, menu, upozornenie „neoficiálna analýza“, pätička so zdrojmi a verziou pipeline. HTML z nich vyrába `pipeline/site.py` pri príkaze `export`. Kým v `config.toml` chýba prevádzkovateľ, stránka Súkromie ukazuje text „[DOPLŇ MENO PREVÁDZKOVATEĽA]“. Pred zverejnením je to tak v poriadku.

### JavaScript mapy (`web/static/js/`)

| Súbor | Úloha |
|---|---|
| `app.js` | riadi stránku: načíta dáta, číta a zapisuje stav v adrese a reaguje na kliknutia |
| `map.js` | mapa Leaflet, farby okresov, vrstva obcí podľa vzdialenosti, legenda, okruhy 10 a 20 km a body ambulancií |
| `panel.js` | obsah panela vpravo (na mobile pod mapou): okres, obec, karty ambulancií |
| `search.js` | vyhľadávanie obce s návrhmi (funguje aj bez diakritiky) |
| `util.js` | pomocné funkcie: vzdialenosť (haversine), formát čísel, `el()` na tvorbu prvkov, načítanie JSON |

Pri otvorení mapy sa načítajú iba `meta.json` a `okresy.geojson`. Zoznam obcí (`obce.json`) sa načíta až pri kliknutí do vyhľadávania. Zoznam ambulancií (`ambulancie.json`) sa načíta až po výbere obce. Prvé načítanie je tak menšie.

**Stav v adrese.** Výber sa zapisuje za znak `#`, napr. `index.html#typ=VLDD&obec=<kód obce>`, `#okres=<kód okresu>`, `#vrstva=okolie` (okresy podľa U8) alebo `#vrstva=obce` (mapa obcí podľa vzdialenosti). Takýto odkaz sa dá poslať a tlačidlo Späť v prehliadači funguje (udalosť `hashchange` v `app.js`).

**Prečo nikde nie je `innerHTML`.** Názvy a adresy z registra sa do stránky vkladajú iba ako text, cez funkciu `el()` (vlastnosť `textContent`). Aj keby register obsahoval kód HTML, zobrazí sa ako obyčajný text. Umelé dáta preto zámerne obsahujú názov `<img src=x onerror=alert(1)>`. `scripts/check_repo.py` zakázané vzory v JS kontroluje.

**CSP (Content Security Policy).** Riadok `<meta http-equiv="Content-Security-Policy">` v `base.html` povie prehliadaču, odkiaľ smie stránka niečo načítať: skripty a štýly iba z vlastného webu, obrázky aj z `tile.openstreetmap.org` (mapové dlaždice). Inline skripty a štýly sú zakázané. Pravidlo je v `pipeline/site.py` (konštanta `CSP`).

**SRI (Subresource Integrity).** Leaflet sa načítava s kontrolným súčtom (atribút `integrity`). Ak by sa súbor zmenil, prehliadač ho nespustí. Pipeline súbory Leafletu pri každom exporte overí oproti `SHA384SUMS`.

**Upozornenie na staré dáta.** Ak je register starší ako 60 dní (`[web] zastarane_po_dnoch`), web zobrazí upozornenie.

### Kontrolný zoznam na prehliadku

Na počítači:
- [ ] Mapa: farby okresov a legenda. Sedí počet okresov v zátvorkách v legende?
- [ ] Prepínač „Lekári pre dospelých / Pediatri“: zmenia sa farby aj legenda?
- [ ] Klik na okres: panel s ukazovateľmi U1, U6, U2, U5, U8 a U7. Ikona ⓘ vedie do metodiky. Pri mestských okresoch Bratislavy a Košíc je navyše poznámka.
- [ ] Prepínač „Mapa: Okresy – okolie 10 km“: farby podľa U8. Porovnaj Košice III a Bratislavu I s režimom „Okresy“.
- [ ] Prepínač „Mapa: Obce podľa vzdialenosti“: každá obec je bod, tmavší bod = ďalej od ambulancie. Klik na bod vyberie obec.
- [ ] Vyhľadanie obce (skús aj bez diakritiky): okruhy 10 a 20 km, body ambulancií, panel obce.
- [ ] Karty ambulancií: „Zobraziť ďalšie“, „Kontakt a ordinačné hodiny“, „Nahlásiť chybu v zázname“.
- [ ] Klik na bod na mape zvýrazní kartu a klik na kartu zvýrazní bod.
- [ ] Skopíruj adresu stránky s vybranou obcou a otvor ju v novom okne. Ukáže sa to isté?
- [ ] Rebríčky, Dáta (stiahni CSV), Metodika, Súkromie, neexistujúca adresa (404).

Na telefóne:
- [ ] posun a zoom mapy prstami, ťuknutie na okres. Všimneš si, že sa zmenil panel pod mapou?
- [ ] vyhľadávanie: neschovajú sa návrhy pod klávesnicu? Vyberie ťuknutie na návrh obec?
- [ ] tabuľka „Celé poradie“ na stránke Rebríčky: nepretečie doprava?
- [ ] je vidieť legenda a atribúcia OpenStreetMap?

Postrehy a nápady zapisuj (alebo hovor AI), čo by si zmenil, pridal alebo zlepšil.

## 2. Ako začať: umelé dáta

```powershell
python -m pipeline all --fixtures
python -m pipeline serve --fixtures
```

Prvý príkaz spustí celú pipeline na umelých dátach z `pipeline/fixtures.py` a všetko uloží do `build/fixtures/`. Je to malé a dá sa to prepočítať ručne:

- 6 obcí v 3 okresoch a 2 krajoch,
- 24 riadkov registra, z ktorých na web prejde 16 ambulancií (12 VLD a 4 VLDD),
- zámerne chybné záznamy. Každý preverí jednu kontrolu: chybný kód, ukončená a budúca platnosť, stacionár, dve verzie toho istého kódu, záznam skrytý na žiadosť, záznam bez adresy, poloha mimo obce, škodlivý názov.

Čo kde nájdeš:

| Cesta v `build/fixtures/` | Obsah |
|---|---|
| `raw/` | vstupy: register (XLSX), hranice obcí, počty obyvateľov, súbor NCZI |
| `snapshots/udzs/` | archív registra s odtlačkom SHA-256 |
| `local/lekari.sqlite` | databáza so všetkými medzivýsledkami (časť 4) |
| `local/reports/` | reporty: validácia, geokódovanie, rozdiel oproti NCZI |
| `history/` | agregovaná história počtov |
| `site/` | hotový web |

Dobré cvičenie: otvor `pipeline/fixtures.py`, nájdi zoznam `AMBULANCIE` a pri každom chybnom zázname zisti, prečo sa nedostal na web. Pomôžu ti `local/reports/validacia_2026-10-01.md` a tabuľky `ambulancia` a `validacia`.

## 3. Kroky pipeline

Príkaz `python -m pipeline all` spustí kroky v tomto poradí. Každý krok sa dá spustiť aj samostatne, napr. `python -m pipeline compute`.

| # | Krok | Modul | Vstup | Výstup | Hlavné kontroly |
|---|---|---|---|---|---|
| 1 | `download` | `download.py` | stránka ÚDZS: nájde najnovší odkaz `VyberKpWeb_*.xlsx` | `data/snapshots/udzs/RRRR-MM-DD.xlsx` s `.sha256`, tabuľka `snapshot`, `data/history/snapshoty.csv` | V1.0 odkaz, V1.1 HTTPS a doména, V1.2 veľkosť, V1.3 XLSX bez makier, V1.4 rovnaký súbor sa druhýkrát neuloží |
| 2 | `areas` | `areas.py` | hranice obcí ZBGIS, body sídiel ZBGIS (geografické názvy), dva súbory STATdata (0–17 a 18+) | tabuľky `obec` a `okres`, `data/local/uzemia/` | V1.5 súradnicový systém a stĺpce, V3.4 geometrie a 79 okresov, V3.5 obyvatelia (súčet = SR), V3.6 zjednodušenie hraníc, V3.9 bod sídla každej obce |
| 3 | `validate` | `validate.py` | snapshot registra | tabuľka `odbornost_pocet` | V2.1 stĺpce, V2.2 zmena počtu riadkov, V2.3 formát kódu, V2.4 počty 020 a 008, V2.5 dátumy, V2.6 jedinečnosť kódov, V2.7 texty |
| 4 | `clean` | `clean.py` | snapshot, `data/local/blocklist.csv`, `data/manual/obec_mapping.csv` | tabuľky `ambulancia` a `adresa_obec` | V3.0 výber, V3.1 blocklist, V3.2 adresa, V3.3 možné duplicity, V3.8 obec z adresy |
| 5 | `nczi` | `nczi.py` | súbor NCZI (stiahne sa raz) | tabuľka `nczi_porovnanie`, report `nczi_rozdiel_*.md` | V3.7 pomer register / NCZI (iba upozornenie) |
| 6 | `geocode` | `geocode.py` | adresy ambulancií, cache, `data/manual/geocode_overrides.csv` | tabuľka `geokod`, `data/cache/geocode_cache.csv`, reporty `geokod_*.csv` | V4.1 až V4.6 poloha, obec, presnosť, zhluky |
| 7 | `compute` | `compute.py` | ambulancie s polohou, obce, okresy | tabuľky `ukazovatel_okres` a `ukazovatel_obec`, `data/history/pocty_okresy.csv` | V5.1 súčty, V5.2 menovateľ a odľahlé hodnoty, V5.4 zmeny v čase, V5.5 konzistentnosť, V5.6 obce s ambulanciou, no s referenčným bodom ďaleko od nej, V5.7 U8 rozdelí všetky ambulancie presne raz |
| 8 | `export` | `export.py`, `site.py` | všetky tabuľky | `site/` (HTML, `data/*.json`, `downloads/*.csv`), report validácie | V6.1 až V6.6 povolené kľúče, veľkosti súborov, súradnice, upozornenie, typy súborov, CSV bez vzorcov |

`areas` beží hneď po `download`, lebo `clean` potrebuje tabuľku obcí na priradenie obce k adrese. Diagram v README ukazuje tie isté kroky zjednodušene.

**Čo robí `clean` (výber ambulancií).** Kód poskytovateľa má 12 znakov. Znaky 7 až 9 sú odbornosť (020 = VLD, 008 = VLDD) a znak 10 je druh činnosti (2 = ambulancia). Ostanú iba záznamy platné k dátumu stavu registra. Pri viacerých verziách toho istého kódu sa ponechá tá s najneskorším začiatkom platnosti. Adresa sa zjednotí do kľúča `adresa_kluc` v tvare `ulica|obec|psč` malými písmenami.

**Čo robí `geocode`.** Pre každú adresu skúša polohy v poradí, ktoré popisuje metodika (časť „Poloha ambulancií“). Prijme prvý bod, ktorý leží v obci z registra alebo najviac 300 m za jej hranicou. Bez prepínača `--nominatim` číta iba z cache a na internet sa nepýta.

**Ako funguje kontrola.** Každá kontrola zapíše riadok do tabuľky `validacia` s výsledkom OK, INFO, WARN alebo FAIL (trieda `Checks` v `pipeline/checks.py`). FAIL krok zastaví a nič sa nezverejní. WARN treba pri mesačnej aktualizácii vysvetliť (runbook, krok 5). Prehľad všetkých výsledkov je v `data/local/reports/validacia_RRRR-MM-DD.md`.

## 4. Databáza

Všetky medzivýsledky sú v SQLite súbore `data/local/lekari.sqlite`. Schéma je v `pipeline/db.py`. **Databáza obsahuje mená poskytovateľov, preto je mimo Gitu.**

| Tabuľka | Čo obsahuje | Kľúč |
|---|---|---|
| `snapshot` | jeden riadok = jeden stiahnutý súbor registra (dátum stavu, URL, SHA-256) | `snapshot_id` |
| `odbornost_pocet` | počty kódov podľa odbornosti v celom registri | `snapshot_id`, `odbornost_kod` |
| `ambulancia` | vyčistené platné ambulancie VLD a VLDD: názov, IČO, adresa, platnosť | `snapshot_id`, `pzs_kod` |
| `geokod` | poloha každej adresy: súradnice, presnosť, zdroj, obec | `adresa_kluc` |
| `adresa_obec` | ku ktorej obci (obciam) patrí názov obce z adresy | `adresa_kluc`, `obec_kod` |
| `obec` | 2 927 obcí: názov, okres, kraj, referenčný bod a jeho zdroj (`ref_zdroj`: `sidlo` alebo `stred`), obyvatelia | `obec_kod` |
| `okres` | 79 okresov: názov, kraj, súčty obyvateľov | `okres_kod` |
| `nczi_porovnanie` | naše počty a počty NCZI po krajoch | `snapshot_id`, `typ`, `kraj_kod` |
| `ukazovatel_okres` | U1, U2, U5, U6, U7, U8 pre každý okres a typ | `snapshot_id`, `okres_kod`, `typ` |
| `ukazovatel_obec` | U3, U4, U8 pre každú obec a typ | `snapshot_id`, `obec_kod`, `typ` |
| `zdroj` | odtlačky vstupných súborov ZBGIS a STATdata | `zdroj_id` |
| `validacia` | výsledky všetkých kontrol | – |
| `v_ambulancia` (pohľad) | ambulancia + poloha z `geokod` + obec, okres a kraj | – |

Cesta od ambulancie k okresu: `ambulancia.adresa_kluc` → `geokod.adresa_kluc` → `geokod.obec_kod` → `obec.obec_kod` → `obec.okres_kod` → `okres.okres_kod`. Pohľad `v_ambulancia` tieto spojenia robí za teba.

## 5. Štatistika jednoducho

### U1 a U2: ambulancie na 10 000 obyvateľov

- **U1** je počet ambulancií daného typu, ktorých poloha leží v okrese.
- **U2 = U1 / menovateľ × 10 000**, zaokrúhlené na dve desatinné miesta (funkcia `okres_indicators` v `compute.py`).

Prepočet na 10 000 obyvateľov umožní porovnať veľký a malý okres. Príklad z `tests/test_compute.py`:

| Okres | Ambulancie | Dospelí | U2 |
|---|---:|---:|---:|
| A | 4 | 20 000 | 4 / 20 000 × 10 000 = 2,0 |
| B | 2 | 10 000 | 2,0 |
| C | 1 | 5 000 | 2,0 |

Počty sú rôzne, no dostupnosť na obyvateľa je rovnaká.

**Menovateľ.** Pre všeobecných lekárov sú to obyvatelia vo veku 18 a viac, pre pediatrov 0 až 17 (rovnako ako NCZI). Je to „stredný stav“ za rok 2025. Štatistický úrad ho počíta ako priemer stavov k 1. 1. a 31. 12., preto majú niektoré obce polovičné hodnoty (napr. 171,5).

**Prečo nie za obec.** Väčšina obcí vlastnú ambulanciu nemá. Pri malom počte obyvateľov by jedna ambulancia urobila z obce „najlepšiu na Slovensku“.

### U5: poradie

Okresy sú zoradené podľa U2 od najnižšej hodnoty, 1 = najmenej ambulancií. Rovnaké hodnoty majú rovnaké poradie a ďalšie poradie sa preskočí: 1, 1, 3. V kóde je to `rank(method="min")`.

### Medián a odľahlé hodnoty (V5.2)

**Medián** je stredná hodnota zoradeného zoznamu. Pri 79 okresoch je to 40. okres v poradí. Na rozdiel od priemeru ho jeden extrémny okres nepohne. Pri VLD je medián 5,25 (register k 1. 10. 2026).

Kontrola V5.2 upozorní (WARN, nie FAIL) na okres, ktorého U2 je viac ako trojnásobok mediánu. Je to signál „pozri sa na to“, nie chyba. Bratislava I má 17,55 a trojnásobok mediánu je 15,75. Je to centrum mesta, kde je ambulancií veľa a kam môžu chodiť aj ľudia z iných okresov.

### U3 a U4: vzdialenosť a počet v okolí obce

- **Referenčný bod obce** je bod sídla obce zo ZBGIS, teda miesto, ku ktorému je priradený názov obce (`settlement_points` v `areas.py`). Pôvodne to bol geometrický stred územia. Pri rozľahlých obciach však padol do hôr: Ľubochňa má ambulanciu priamo v obci, a predsa zo stredu vyšlo 10,2 km. Z bodu sídla vychádza 0,2 km. Takých obcí bolo 172 a po zmene ostala jedna (kontrola V5.6, overenie O18). Ak obec bod sídla nemá, použije sa stred územia (`reference_points`).
- **Haversine** je vzorec na vzdušnú vzdialenosť po povrchu gule s polomerom 6 371 km. Python (`haversine_km` v `compute.py`) aj web (`haversineKm` v `util.js`) používajú ten istý vzorec, preto sa čísla na webe a v CSV zhodujú. Pre predstavu: 1° zemepisnej šírky je asi 111,2 km, 0,1° asi 11,1 km (test v `tests/test_compute.py`).
- **U3** je vzdialenosť k najbližšej ambulancii. **U4** je počet ambulancií do 10 km a do 20 km.
- Kontrola V5.5 overí, či to dáva zmysel: ak je najbližšia ambulancia do 10 km, počet do 10 km musí byť aspoň 1.

Obmedzenia: skutočná cesta je dlhšia ako vzdušná čiara a všetci obyvatelia obce dostanú vzdialenosť z jedného bodu, aj keď obec má viac častí.

### U7: podiel obyvateľov ďaleko od ambulancie

Pre každý okres: koľko percent obyvateľov príslušnej vekovej skupiny býva v obciach, kde je najbližšia ambulancia ďalej ako 5 km, resp. 10 km (funkcia `distance_shares` v `compute.py`). Je to **vážený** podiel: veľká obec sa počíta s väčšou váhou ako malá.

Príklad: okres má tri obce so 100, 300 a 600 dospelými. Ich najbližšia ambulancia je vzdialená 3, 6 a 12 km. Ďalej ako 5 km býva 300 + 600 = 900 z 1 000 dospelých, teda 90 %. Ďalej ako 10 km býva 600 z 1 000, teda 60 % (test v `tests/test_compute.py`).

U7 meria niečo iné ako U2. Pri pediatroch sú Medzilaborce podľa U2 druhé najlepšie (78. zo 79), a predsa 10,1 % detí tam má najbližšieho pediatra ďalej ako 10 km. Krupina je podľa U2 najhoršia a zároveň má ďalej ako 10 km 21,2 % detí (register k 1. 10. 2026).

### U8: ambulancie v okolí 10 km (2SFCA)

U2 počíta iba ambulancie a obyvateľov vo vnútri hraníc okresu. Ľudia však chodia aj do susedného okresu. Pri meste rozdelenom na okresy je to veľký rozdiel: Košice I majú veľa ambulancií a málo obyvateľov, Košice III naopak.

Metóda 2SFCA (`catchment_access` a `catchment_by_okres` v `compute.py`) má dva kroky:
1. **Za každú ambulanciu:** koľko ľudí býva do 10 km od nej? Ambulancia sa rozdelí rovnakým dielom medzi všetkých týchto ľudí.
2. **Za každú obec:** sčítaj diely všetkých ambulancií do 10 km a vynásob 10 000.

Hodnota okresu je vážený priemer obcí.

Príklad z `tests/test_compute.py`: obce A (1 000 dospelých), B (3 000 dospelých, 5,6 km od A) a C (1 000 dospelých, ďaleko). Ambulancie sú v A, v C a jedna ďalej ako 10 km od všetkých obcí.
- Ambulancia v A sa delí medzi 4 000 ľudí z A a B, takže A aj B dostanú 1 / 4 000, teda **2,5 na 10 000**.
- Ambulancia v C patrí iba 1 000 ľuďom z C, takže C dostane **10 na 10 000**.
- Ambulancia bez obyvateľov do 10 km sa nezapočíta nikomu.

**Zákon zachovania (kontrola V5.7).** Ak vynásobíš hodnotu každej obce jej počtom obyvateľov a sčítaš (a vydelíš 10 000), dostaneš presne počet ambulancií, ktoré majú niekoho do 10 km. V príklade: (2,5 · 1 000 + 2,5 · 3 000 + 10 · 1 000) / 10 000 = 2. Pri reálnych dátach je to 2 433 z 2 433 ambulancií VLD. Žiadna ambulancia sa tak nestratí ani nezapočíta dvakrát.

Výsledok pri VLD (register k 1. 10. 2026):

| Okres | U2 | U8 |
|---|---|---|
| Košice III | 2,66, 1. miesto | 7,10, 70. miesto |
| Bratislava I | 17,55, 79. miesto | 7,58, 75. miesto |
| Košice – okolie | 3,14, 2. miesto | 3,95, 5. miesto |

Rozpätie okresov sa zúžilo z 2,66 – 17,55 na 3,25 – 8,35. Najhoršie podľa U8 sú Bytča, Sabinov, Námestovo, Kysucké Nové Mesto a Košice – okolie.

### U6: pracoviská

Pracovisko je jedna dvojica IČO + adresa. Ak má poskytovateľ na jednej adrese viac kódov, počíta sa ako jedno pracovisko. Preto U6 nikdy nie je vyšší ako U1 (kontrola V5.1). K 1. 10. 2026: VLD 2 433 kódov a 2 301 pracovísk.

### Porovnanie s NCZI (V3.7)

Pre každý kraj sa počíta pomer register / NCZI. Mimo rozsahu 0,8 – 1,6 kontrola iba upozorní a nikdy nezastaví zverejnenie. Kraj sa tu určuje z názvu obce v adrese. Ak názov obce existuje vo viacerých krajoch, ambulancia sa započíta iba do Slovenska. Prečo je register vyšší, rozoberá `docs/overenia.md`, časť O14.

### Zmeny v čase (V5.4)

Pri každom behu `compute` sa počty porovnajú s minulým mesiacom z `data/history/pocty_okresy.csv`:

- zmena za Slovensko do 5 %: OK,
- zmena za Slovensko 5 až 15 %: WARN,
- zmena za Slovensko nad 15 %: FAIL (pokračovať sa dá iba s `--potvrdit-zmeny`),
- okres, ktorého počet sa zmenil aspoň o 3 a zároveň aspoň o 25 %: WARN.

Pri prvom snapshote sa nič neporovnáva (INFO).

### Legenda mapy

Hranice farieb sú pevne dané v `config.toml`, sekcia `[legenda]`: VLD 4, 5, 6 a 7, pediatri 8, 10, 12 a 14. Vzniká tak 5 tried, napr. pri VLD: menej ako 4, 4–5, 5–6, 6–7 a 7 a viac. Tmavšia farba znamená menej ambulancií. Pri pevných hraniciach znamená tá istá farba každý mesiac to isté.

### Typické pasce

- **Malé čísla.** V okrese s pár ambulanciami zmení jedna ambulancia U2 výrazne. Panel okresu na to pri menej ako 10 ambulanciách upozorní.
- **Dochádzanie.** Ľudia chodia k lekárovi aj mimo svojho okresu, najmä do miest.
- **Mestá rozdelené na okresy.** Bratislava I–V a Košice I–IV: podľa U2 vychádzajú centrá najlepšie a iné mestské okresy najhoršie. Pri VLD sú Košice III posledné (2,66), k 1. 10. 2026. Riešením je U8 (vyššie).
- **Rôzne dátumy.** Register je k 1. 10. 2026, obyvatelia sú stredný stav 2025 a NCZI je k 31. 12. 2024.
- **Kód nie je lekár.** Jeden kód je jedna ambulancia v registri, nie jeden lekár ani úväzok.

## 6. Vyskúšaj sám: SQL dotazy

**DB Browser for SQLite** (https://sqlitebrowser.org, zadarmo): menu File → **Open Database Read Only**, súbor `data/local/lekari.sqlite`, alebo `build/fixtures/local/lekari.sqlite` pre umelé dáta. Dotazy píš na karte Execute SQL. Databázu otváraj iba vtedy, keď pipeline nebeží.

To isté v Pythone (iba na čítanie):

```python
import sqlite3
import pandas as pd

con = sqlite3.connect("file:data/local/lekari.sqlite?mode=ro", uri=True)
pd.read_sql("SELECT typ, COUNT(*) AS pocet FROM ambulancia GROUP BY typ", con)
```

Každý dotaz nižšie začína riadkom `WITH posledny AS (...)`, ktorý vyberie posledný snapshot registra. Výsledky s menami poskytovateľov nikdy nekopíruj do súborov v Gite.

**1. Počet ambulancií podľa kraja a typu.** Kraj je tu podľa polohy ambulancie, preto sa čísla môžu mierne líšiť od porovnania s NCZI (dotaz 9).

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT o.kraj_nazov AS kraj, a.typ, COUNT(*) AS ambulancie
FROM v_ambulancia a
JOIN posledny USING (snapshot_id)
JOIN okres o ON o.okres_kod = a.okres_kod
GROUP BY o.kraj_nazov, a.typ
ORDER BY kraj, a.typ;
```

**2. U1 a U2 prepočítané ručne pre jeden okres.** Stĺpce „rucne“ a „pipeline“ sa musia zhodovať. Pre umelé dáta zmeň názov okresu napr. na `'Testovka'`. Pre pediatrov zmeň `'VLD'` na `'VLDD'` a `obyv_dospeli` na `obyv_deti`.

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT o.nazov AS okres,
       (SELECT COUNT(*) FROM v_ambulancia a
        WHERE a.okres_kod = u.okres_kod AND a.typ = u.typ AND a.snapshot_id = u.snapshot_id) AS u1_rucne,
       u.pocet AS u1_pipeline,
       o.obyv_dospeli AS menovatel_18plus,
       ROUND(u.pocet * 10000.0 / o.obyv_dospeli, 2) AS u2_rucne,
       u.na_10k AS u2_pipeline
FROM ukazovatel_okres u
JOIN posledny USING (snapshot_id)
JOIN okres o ON o.okres_kod = u.okres_kod
WHERE u.typ = 'VLD' AND o.nazov = 'Rožňava';
```

**3. Desať okresov s najmenej ambulanciami na 10 000 obyvateľov.** Pre najlepšie okresy daj `ORDER BY u.na_10k DESC`. Bez `LIMIT 10` dostaneš celé poradie a medián je 40. riadok.

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT u.poradie, o.nazov AS okres, o.kraj_nazov AS kraj, u.pocet, u.na_10k
FROM ukazovatel_okres u
JOIN posledny USING (snapshot_id)
JOIN okres o ON o.okres_kod = u.okres_kod
WHERE u.typ = 'VLD'
ORDER BY u.na_10k
LIMIT 10;
```

**4. Obce najďalej od ambulancie.** Vzdušná vzdialenosť zo stredu obce (U3) a počty do 10 a 20 km (U4).

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT ob.nazov AS obec, ok.nazov AS okres, ROUND(u.najblizsia_km, 1) AS najblizsia_km,
       u.pocet_10km, u.pocet_20km
FROM ukazovatel_obec u
JOIN posledny USING (snapshot_id)
JOIN obec ob ON ob.obec_kod = u.obec_kod
JOIN okres ok ON ok.okres_kod = ob.okres_kod
WHERE u.typ = 'VLD'
ORDER BY u.najblizsia_km DESC
LIMIT 15;
```

**5. Koľko dospelých má najbližšieho všeobecného lekára ďalej ako 10 km.** Všetci obyvatelia obce dostanú vzdialenosť jej stredu, takže je to iba odhad. Pre výsledok po okresoch pridaj `ob.okres_kod` do `SELECT` a na koniec `GROUP BY ob.okres_kod`.

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT SUM(ob.obyv_dospeli) AS dospelych_spolu,
       SUM(CASE WHEN u.najblizsia_km > 10 THEN ob.obyv_dospeli ELSE 0 END) AS dospelych_nad_10km,
       ROUND(100.0 * SUM(CASE WHEN u.najblizsia_km > 10 THEN ob.obyv_dospeli ELSE 0 END)
             / SUM(ob.obyv_dospeli), 2) AS percento,
       SUM(u.najblizsia_km > 10) AS obci_nad_10km
FROM ukazovatel_obec u
JOIN posledny USING (snapshot_id)
JOIN obec ob ON ob.obec_kod = u.obec_kod
WHERE u.typ = 'VLD';
```

**6. Presnosť polohy podľa okresu.** Kde je najviac ambulancií s polohou iba na stred obce. V SQLite je porovnanie `a.presnost = 'obec'` rovné 1 alebo 0, takže sa dá sčítať.

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT ok.nazov AS okres, COUNT(*) AS ambulancie,
       SUM(a.presnost = 'adresa') AS adresa, SUM(a.presnost = 'ulica') AS ulica,
       SUM(a.presnost = 'obec') AS iba_obec, SUM(a.presnost = 'rucne') AS rucne,
       ROUND(100.0 * SUM(a.presnost = 'obec') / COUNT(*), 1) AS percento_iba_obec
FROM v_ambulancia a
JOIN posledny USING (snapshot_id)
JOIN okres ok ON ok.okres_kod = a.okres_kod
GROUP BY ok.nazov
ORDER BY percento_iba_obec DESC;
```

**7. Kódy (U1) a pracoviská (U6) za Slovensko.**

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT typ, SUM(pocet) AS ambulancie_u1, SUM(pocet_pracovisk) AS pracoviska_u6
FROM ukazovatel_okres
JOIN posledny USING (snapshot_id)
GROUP BY typ;
```

**8. Viac kódov s rovnakým IČO na rovnakej adrese** (kontrola V3.3). Počet nadbytočných kódov je `kodov_v_skupinach − skupin`.

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT typ, COUNT(*) AS skupin, SUM(n) AS kodov_v_skupinach
FROM (SELECT typ, ico, adresa_kluc, COUNT(*) AS n
      FROM ambulancia
      JOIN posledny USING (snapshot_id)
      GROUP BY typ, ico, adresa_kluc
      HAVING COUNT(*) > 1)
GROUP BY typ;
```

**9. Porovnanie s NCZI po krajoch.**

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT n.typ, COALESCE(k.kraj_nazov, 'Slovensko') AS kraj, n.register, n.nczi,
       ROUND(1.0 * n.register / n.nczi, 2) AS pomer
FROM nczi_porovnanie n
JOIN posledny USING (snapshot_id)
LEFT JOIN (SELECT DISTINCT kraj_kod, kraj_nazov FROM okres) k ON k.kraj_kod = n.kraj_kod
ORDER BY n.typ, n.kraj_kod;
```

**10. Upozornenia a chyby z posledného behu.** Kroky `download` a `areas` nemajú snapshot (`snapshot_id IS NULL`).

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT krok, kod, vysledok, popis, hodnota
FROM validacia
WHERE vysledok IN ('WARN', 'FAIL')
  AND (snapshot_id IS NULL OR snapshot_id = (SELECT snapshot_id FROM posledny))
ORDER BY krok, kod;
```

**11. Obce s vlastnou ambulanciou, ktorých referenčný bod je od nej ďaleko** (kontrola V5.6). Pred zmenou referenčného bodu ich bolo 172, teraz má byť zoznam takmer prázdny.

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT u.typ, ob.nazov AS obec, ob.ref_zdroj, ROUND(u.najblizsia_km, 1) AS najblizsia_km, u.pocet_v_obci
FROM ukazovatel_obec u
JOIN posledny USING (snapshot_id)
JOIN obec ob ON ob.obec_kod = u.obec_kod
WHERE u.pocet_v_obci > 0 AND u.najblizsia_km > 2
ORDER BY u.najblizsia_km DESC;
```

**12. U7: okresy s najväčším podielom detí ďalej ako 10 km od pediatra.** Pre dospelých zmeň `'VLDD'` na `'VLD'`. Pre porovnanie s U2 je pridané aj poradie.

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT o.nazov AS okres, ROUND(100 * u.podiel_nad_5km, 1) AS percento_nad_5km,
       ROUND(100 * u.podiel_nad_10km, 1) AS percento_nad_10km, u.na_10k, u.poradie AS poradie_u2
FROM ukazovatel_okres u
JOIN posledny USING (snapshot_id)
JOIN okres o ON o.okres_kod = u.okres_kod
WHERE u.typ = 'VLDD'
ORDER BY u.podiel_nad_10km DESC
LIMIT 10;
```

**13. Okresy, ktoré sa medzi U2 a U8 posunuli najviac.** Kladný posun znamená, že okres je podľa U8 na tom lepšie, ako ukazuje U2.

```sql
WITH posledny AS (SELECT snapshot_id FROM snapshot ORDER BY stav_k DESC LIMIT 1)
SELECT o.nazov AS okres, u.na_10k AS u2, u.poradie AS poradie_u2, u.na_10k_okolie AS u8,
       u.poradie_okolie AS poradie_u8, u.poradie_okolie - u.poradie AS posun
FROM ukazovatel_okres u
JOIN posledny USING (snapshot_id)
JOIN okres o ON o.okres_kod = u.okres_kod
WHERE u.typ = 'VLD'
ORDER BY ABS(u.poradie_okolie - u.poradie) DESC
LIMIT 15;
```

## 7. Slovníček

| Pojem | Význam |
|---|---|
| snapshot | jedna stiahnutá verzia registra k dátumu stavu |
| SHA-256 | odtlačok súboru. Rovnaký súbor má vždy rovnaký odtlačok, pipeline tak spozná, že súbor už má. |
| geokódovanie | prevod adresy na súradnice (OpenStreetMap Nominatim) |
| cache | uložené odpovede Nominatimu (`data/cache/`). Tá istá adresa sa druhýkrát nepýta. |
| fixtures | umelé testovacie dáta v `pipeline/fixtures.py` |
| OK / INFO / WARN / FAIL | výsledok kontroly: v poriadku, informácia, upozornenie, chyba (zastaví krok) |
| referenčný bod obce | bod sídla obce zo ZBGIS, z ktorého sa merajú vzdialenosti |
| menovateľ | počet obyvateľov, ktorým sa delí pri prepočte na 10 000 |
| medián | stredná hodnota zoradeného zoznamu |
| haversine | vzorec na vzdušnú vzdialenosť po povrchu Zeme |
| EPSG:5514 | súradnicový systém S-JTSK v metroch, v ňom sú hranice ZBGIS. Web používa zemepisnú šírku a dĺžku (EPSG:4326). |
| CSP | pravidlá, odkiaľ smie stránka načítať skripty, štýly a obrázky |
| SRI | kontrola, že sa súbor knižnice (Leaflet) nezmenil |
