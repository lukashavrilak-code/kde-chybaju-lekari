# Denník overení (OVERIŤ)

Každú neoverenú vec zapíš sem: čo, ako, výsledok, zdroj a dátum. Kým položka nie je uzavretá, na webe sa neprezentuje ako fakt.

| # | Čo overiť | Stav | Výsledok a zdroj | Dátum |
|---|---|---|---|---|
| O1 | Kód odbornosti 008 = pediater prvého kontaktu | uzavreté | Číselník NCZI „Odborné zameranie v zariadení“ (OID 1.3.158.00165387.100.10.39, verzia 17, zmena 2026-06-02): 008 = všeobecná starostlivosť o deti a dorast, 020 = všeobecné lekárstvo, 007 = pediatria. Zdroj: https://www.nczisk.sk/Documents/standardy/standardy_zdravotnickej_informatiky/Ciselniky/39.xml. To, že pozície 7–9 kódu PZS sú z tohto číselníka, uvádza sekundárny zdroj (zssambra.sk); potvrdiť v metodickom usmernení ÚDZS. Kontrolná poistka: V3.7 porovnanie s NCZI (rovnaké názvy odborností 008 a 020 aj v tabuľke NCZI T2). | 2026-10-27 |
| O2 | Stĺpce `* OU` = miesto prevádzkovania ambulancie, `Obec`/`PSC` = sídlo poskytovateľa | čiastočne | Register k 1. 10. 2026: adresa OU je vyplnená pri všetkých 2 433 platných VLD (druh činnosti 2). Obec OU sa líši od Obec pri 1 150 z 2 433 VLD, čo zodpovedá významu sídlo vs. prevádzka. (Predtým uvedené „1 154 z 2 443“ bolo počítané bez filtra druhu činnosti a platnosti.) Oficiálny popis stĺpcov ÚDZS zatiaľ nemáme. | 2026-10-27 |
| O3 | Význam pozícií 1–6 a 10–12 v `pzs_kod`; 1 kód = 1 ambulancia?; ukončené záznamy v súbore?; formát dátumov | uzavreté | 1. znak písmeno + 5 číslic (identifikátor poskytovateľa), 7–9 odborné zameranie (číselník 39), 10 typ odbornej činnosti (číselník 37: 2 = ambulancia, 6 = stacionár…), 11–12 poradie. `pzs_kod` je jedinečný. Súbor **neobsahuje ukončené záznamy** (0 s Platnost_do pred dátumom stavu, 52 s budúcim koncom, 13 s budúcim začiatkom), takže históriu z platností spätne zrekonštruovať nemožno. Dátumy sú čitateľné na 100 %. 285 IČO má viac ambulancií VLD. | 2026-10-26 |
| O4 | Stabilná URL súboru, frekvencia aktualizácie, podmienky opätovného použitia | uzavreté | Stránka: https://www.udzs-sk.sk/urad/kody-poskytovatelov-zdravotnej-starostlivosti-a-zdravotnickych-pracovnikov/. URL súboru obsahuje dátum (`VyberKpWeb_1.10.2026.xlsx`), preto ju pipeline hľadá na stránke sama (`python -m pipeline download`, overené 27. 10. 2026). URL v `config.toml` je iba záloha. Frekvencia ani licencia nie sú na stránke uvedené. E-mail ÚDZS sa neposiela – rozhodnutie autora. | 2026-10-27 |
| O5 | Počty obyvateľov obcí: tabuľka, rok, podmienky, formát | uzavreté | STATdata ŠÚ SR, tabuľka om7006rr, pohlavie Spolu, rok 2025, ručný export dvoch súborov (0–17 a 18+). Automatické sťahovanie zo STATdata je podľa podmienok zakázané, pipeline iba číta súbory. Licencia CC BY 4.0, atribúcia „Zdroj: Štatistický úrad SR, CC BY 4.0, www.statistics.sk“. Export nemá kódy obcí: spájame podľa okresu a názvu (odrezanie „, okres X“ za čiarkou, „ - mestská časť “ → „-“). Spojených 2 927 z 2 927 obcí ZBGIS. Súčty za SR: 0–17 = 1 020 767, 18+ = 4 393 662, spolu 5 414 429. Nepoužité riadky bez hodnoty za 2025: Javorina (vojenský obvod), Nové Hony a Pinciná pod okresom Poltár. | 2026-10-27 |
| O6 | Do akého veku patrí pacient k pediatrovi prvého kontaktu (menovateľ) | uzavreté | Menovatele 0–17 (pediatri) a 18+ (všeobecní lekári) sú zhodné s NCZI: súbor S01 2024 T2, hárok Obsah, obrázky O1 („všeobecné lekárstvo na 100 000 obyvateľov vo veku 18+“) a O2 („všeobecná starostlivosť o deti a dorast na 100 000 obyvateľov vo veku 0 – 17“). Právnu vekovú hranicu sme neoverovali, menovateľ ju nepotrebuje. | 2026-10-27 |
| O7 | ZBGIS: URL súboru, vrstva, atribúty kódov obce/okresu/kraja, spojenie so STATdata, mestské časti BA a KE | uzavreté | https://opendata.skgeodesy.sk/static/ZBGIS/usj/ah_gpkg_0.zip (EPSG:5514, CC BY 4.0), súbor `USJ_hranice_0.gpkg`, vrstva `obec_0`: 2 927 obcí vrátane 3 vojenských obvodov, 79 okresov, 8 krajov; atribúty IDN4/NM4 (obec, 6 číslic), IDN3/NM3 (okres), IDN2/NM2 (kraj 1–8 = BA, TT, TN, NR, ZA, BB, PO, KE), LAU2_CODE. Mestské časti BA a KE sú samostatné obce. Vrstva `ku_0` (katastrálne územia) má aj kód obce. Spojenie so STATdata pozri O5. | 2026-10-27 |
| O7a | Možné duplicity: 98 skupín rovnaké IČO + typ + adresa s viacerými kódmi PZS | rozhodnuté | Počítame tak, ako sú v registri (každý kód = ambulancia), uvedené v metodike ako obmedzenie U1. Vplyv na porovnanie s NCZI pozri O14. | 2026-10-26 |
| O8 | Čo počítajú tabuľky NCZI a k akému dátumu | čiastočne | NCZI, výstup S01 za rok 2024, tabuľky T2 (SR) a T2_1 až T2_8 (kraje BA … KE), riadky „ambulancia_výstup“, stĺpec „Počet útvarov“. Za SR: 008 = 885, 020 = 1 891, súčet krajov sedí. Podľa hárku Meta: zdroj je Národný register poskytovateľov zdravotnej starostlivosti a ročné výkazy, počty sú stav k 31. 12. 2024, územie podľa územia činnosti útvaru, „odborný útvar je organizačná jednotka zdravotníckeho zariadenia“. **OVERIŤ:** či „útvar“ zodpovedá jednému kódu PZS v registri ÚDZS. | 2026-10-27 |
| O9 | Presné URL vyhľadávania lekárov VšZP, Dôvery a Unionu | uzavreté | URL dodal autor: VšZP https://www.vszp.sk/zoznam-zmluvnych-lekarov/, Dôvera https://poskytovatelia.dovera.sk/vyhladavanie, Union https://portal.unionzp.sk/pub/zmluvni-lekari-pzs. Iba odkazy, žiadne scrapovanie. | 2026-10-27 |
| O10 | OSM: Tile Usage Policy (Referer), Nominatim Usage Policy, OSMF Geocoding Guideline (ODbL) | otvorené | | |
| O11 | Leaflet 1.9.4 pod CSP bez `'unsafe-inline'` | uzavreté | Funguje. Potrebné povoliť `img-src data:` (Leaflet ruší načítanie dlaždíc 1×1 GIF obrázkom). Overené v Edge 156 headless: 0 hlásení v konzole. | 2026-10-26 |
| O12 | Prenos IP adries návštevníkov do USA pri GitHub Pages (text stránky Súkromie) | otvorené | | |
| O13 | Register adries SR ako open data so súradnicami (záložný geokóder) | otvorené | | |
| O14 | Rozdiel register vs. NCZI: register má o 29 % viac VLD (2 433 vs. 1 891) a o 24 % viac VLDD (1 101 vs. 885) | rozhodnuté | Rozhodnutie autora 27. 10. 2026: **F0 + F1** – nefiltrovať, U1 = počet kódov ostáva, doplnkový ukazovateľ U6 „počet pracovísk“ (rovnaké IČO + adresa). Analýza v časti [O14 – analýza](#o14) nižšie. | 2026-10-27 |
| O15 | Hodnoty STATdata s „,5“ (1 412 obcí pri 0–17): stredný stav, nie okamžitý stav k 30. 6. 2025 | uzavreté | Heslo ŠÚ SR „Stredný (priemerný) stav trvale bývajúceho obyvateľstva“ (https://slovak.statistics.sk/PACVPEM/vocabPagesDetails.html?id=4081&lang=sk): počet obyvateľov ku stredu sledovaného obdobia, od roku 2011 aritmetický priemer stavov k 1. 1. a 31. 12. Text sme mali iba z výsledkov vyhľadávania (stránka vracia 403, API ŠÚ SR odmieta spojenie). Polovičné hodnoty v dátach sa s tým zhodujú. Na webe uvádzame „stredný stav 2025“. Autor môže v STATdata overiť, že názov tabuľky om7006rr obsahuje „stredný stav“. | 2026-10-27 |
| O16 | Obec OU „Myslenice“ (PSČ 902 03) nie je obec ani katastrálne územie v ZBGIS | uzavreté | Priradené k obci Pezinok (508179) v `data/manual/obec_mapping.csv`. Dôvody: Myslenice je historický názov Grinavy (od 1975 súčasť Pezinka, Wikipedia „Grinava“); ZBGIS `ku_0`: Grinava je katastrálne územie obce Pezinok; geokódovaný bod adresy „Myslenická 4076/1E“ (presnosť adresa) leží v obci Pezinok; PSČ 902 03 = Pezinok-Myslenice podľa neoficiálnych zoznamov PSČ. Oficiálne vyhľadávanie Slovenskej pošty (posta.sk/psc) je iba interaktívne a automaticky sa overiť nedalo. Mochovce → Kalná nad Hronom a Tatranská Lomnica → Vysoké Tatry sú priradené podľa ZBGIS `ku_0`. | 2026-10-27 |
| O17 | Body geokódovania mimo obce z adresy v registri (V4.3) | uzavreté | Rozhodnutie autora 27. 10. 2026: ak bod nepadne do obce z registra, skúsiť ďalších kandidátov v tej obci, potom stred obce; tolerancia 300 m pri hranici. Výsledok: prvý bod nesedel pri 27 adresách. 1 adresa ostala vďaka tolerancii (20 m za hranicou), 26 sa vyriešilo iným kandidátom v obci (21 z nich iba s presnosťou obec), 0 ostalo na ručnú kontrolu. Zároveň sa upravenými zneniami adries (bez „ul.“ a „č.“, prehodené číslo, obce bez ulíc) zlepšila presnosť 234 adries: presnosť na adresu 69,7 % → 79,3 % ambulancií, iba obec 23,3 % → 13,4 % (365 adries). Test na 50 dotazoch zlepšil 50 % testovaných adries, plný beh mal 377 dotazov. V4.6: 5 bodov s viac ako 5 adresami. Na ručné zlepšenie ostáva 365 adries s presnosťou iba obec (`geokod_kontrola_2026-10-01.csv`). Oprava pravidla: obec podľa začiatku názvu sa hľadá iba pri obciach so spojovníkom (Bratislava-…, Košice-…, Nedožery-Brezany), Matejovce → Poprad podľa ZBGIS `ku_0`. | 2026-10-27 |

<a id="o14"></a>

## O14 – analýza rozdielu register vs. NCZI (27. 10. 2026)

Register ÚDZS k 1. 10. 2026 vs. NCZI S01 2024 (počet útvarov k 31. 12. 2024). Kraj ambulancie je určený z adresy v registri. Report sa generuje príkazom `python -m pipeline nczi` do `data/local/reports/nczi_rozdiel_RRRR-MM-DD.md` (iba agregáty).

**a) Pomer register / NCZI po krajoch** (prebytok je vo všetkých krajoch, najväčší v Bratislavskom kraji)

| Kraj | VLD register | VLD NCZI | VLD pomer | VLDD register | VLDD NCZI | VLDD pomer |
|---|---:|---:|---:|---:|---:|---:|
| Slovensko | 2 433 | 1 891 | 1,29 | 1 101 | 885 | 1,24 |
| Bratislavský | 376 | 259 | 1,45 | 147 | 94 | 1,56 |
| Trnavský | 224 | 166 | 1,35 | 106 | 90 | 1,18 |
| Trenčiansky | 240 | 199 | 1,21 | 101 | 84 | 1,20 |
| Nitriansky | 315 | 236 | 1,33 | 142 | 110 | 1,29 |
| Žilinský | 266 | 212 | 1,25 | 128 | 103 | 1,24 |
| Banskobystrický | 292 | 236 | 1,24 | 120 | 98 | 1,22 |
| Prešovský | 351 | 275 | 1,28 | 181 | 160 | 1,13 |
| Košický | 354 | 308 | 1,15 | 169 | 146 | 1,16 |

Bez jednoznačného kraja (názov obce existuje vo viacerých krajoch): VLD 15, VLDD 7. Tie sú započítané iba v riadku Slovensko. (Čísla po oprave Myslenice → Pezinok a Matejovce → Poprad, 27. 10. 2026.)

**b) Viac kódov na rovnakom IČO a adrese:** VLD 76 skupín so 132 nadbytočnými kódmi, VLDD 22 skupín s 29 nadbytočnými kódmi. Na 50 adresách má to isté IČO kódy VLD aj VLDD. Poradie 02 a vyššie (pozície 11–12) má 637 kódov VLD a 234 kódov VLDD.

**c) Platnost_od:** po 31. 12. 2024 začalo platiť 266 kódov VLD (2025: 167, 2026: 99) a 136 kódov VLDD (2025: 98, 2026: 38). Register neobsahuje ukončené záznamy, preto počet kódov so začiatkom do 31. 12. 2024 je iba dolný odhad stavu registra k tomuto dátumu.

**d) Scenáre (iba informatívne, nič sa nefiltruje), pomer za SR:**

| Scenár | VLD | VLDD |
|---|---:|---:|
| S0 všetky kódy | 1,29 | 1,24 |
| S1 bez kódov so začiatkom po 31. 12. 2024 | 1,15 | 1,09 |
| S2 rovnaké IČO + typ + adresa zlúčené | 1,22 | 1,21 |
| S3 = S1 + S2 | 1,08 | 1,06 |

V S1 klesne Trenčiansky kraj pod 1 (VLD 0,92, VLDD 0,86) a Trnavský pri VLDD na 0,89. Bratislavský ostáva najvyšší (S3: VLD 1,10, VLDD 1,29).

**Zistenia (overené výpočtom):**
1. Približne polovicu rozdielu VLD a viac ako polovicu rozdielu VLDD tvoria kódy so začiatkom platnosti po referenčnom dátume NCZI (časový posun 2024 → 10/2026).
2. Ďalšiu časť tvoria viaceré kódy toho istého IČO na tej istej adrese.

**Hypotézy (neoverené):**
- H1: Časť kódov z rokov 2025–2026 nahrádza staršie kódy (zmena poskytovateľa alebo právnej formy na tom istom mieste). Naznačuje to pokles pod 1 v Trenčianskom kraji v scenári S1. Overiť sa to dá až porovnaním dvoch snapshotov.
- H2: NCZI počíta organizačné útvary zdravotníckeho zariadenia z Národného registra poskytovateľov. To nemusí byť 1 : 1 s kódmi PZS v registri ÚDZS (OVERIŤ, pozri O8).
- H3: Časť kódov môže patriť ambulanciám bez reálnej činnosti alebo bez zmluvy s poisťovňou. Z registra sa to overiť nedá.
- H4: Vyšší pomer v Bratislavskom kraji môže súvisieť s väčším počtom kódov na jedno pracovisko alebo s rozdielom medzi adresou v registri a „územím činnosti útvaru“ v NCZI.

**Návrhy filtrov (autor 27. 10. 2026 zvolil F0 + F1):**

| Návrh | Výhody | Nevýhody |
|---|---|---|
| F0 Nefiltrovať (súčasný stav, U1 = počet kódov) | jednoduché, iba to, čo register obsahuje | počty sú vyššie ako NCZI, mapa môže nadhodnocovať dostupnosť |
| F1 Doplnkový ukazovateľ „počet pracovísk“ (jedinečné IČO + adresa), U1 nemeniť | znižuje vplyv viacerých kódov na jednom mieste, nič sa neskrýva | nový ukazovateľ = MINOR verzia, viac textu na webe |
| F2 Vylúčiť kódy so začiatkom platnosti posledných N mesiacov | priblíži sa NCZI | vylúči aj skutočne nové ambulancie, závisí od dátumu |
| F3 Zlúčiť rovnaké IČO + typ + adresa v U1 | rovnaký efekt ako F1, ale v hlavnom ukazovateli | mení definíciu U1, stráca sa informácia o počte kódov |

Rozhodnutie: **F0 + F1** – U1 ostáva počet kódov, doplnkový ukazovateľ U6 = počet pracovísk (metodika, U6). F2 ani F3 sa nezavádzajú.
