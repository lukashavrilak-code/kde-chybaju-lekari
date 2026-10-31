# Metodika

Táto stránka je **neoficiálna analýza verejných dát**. Ukazuje, kde sú ambulancie všeobecných lekárov pre dospelých (VLD) a pediatrov prvého kontaktu (VLDD) **evidované v registri** Úradu pre dohľad nad zdravotnou starostlivosťou (ÚDZS), ako ďaleko sú od obcí a koľko ich pripadá na obyvateľov.

Stránka **neukazuje**, či ambulancia prijíma nových pacientov, aké má ordinačné hodiny, koľko v nej pracuje lekárov ani aké sú čakacie doby. Tieto údaje register neobsahuje. Kontakt a ordinačné hodiny overte vo vyhľadávaní lekárov svojej zdravotnej poisťovne.

## Zdroje dát

| Zdroj | Čo z neho používame | Stav k | Licencia |
|---|---|---|---|
| ÚDZS – Kódy poskytovateľov zdravotnej starostlivosti (XLSX) | názov poskytovateľa, odbornosť z kódu, adresa ambulancie, platnosť záznamu | mesiac registra (pozri [Aktuálny stav dát](#aktualne)) | licencia nie je uvedená |
| Štatistický úrad SR – STATdata, tabuľka om7006rr | počet obyvateľov obcí vo veku 0 – 17 a 18+ (menovateľ) | stredný stav 2025 | CC BY 4.0, „Zdroj: Štatistický úrad SR, CC BY 4.0, www.statistics.sk“ |
| ÚGKK SR – ZBGIS | hranice obcí a okresov, bod sídla každej obce | súbory z roku 2026 | CC BY 4.0, hranice sú na webe zjednodušené |
| OpenStreetMap – Nominatim | poloha (súradnice) adries ambulancií | pri geokódovaní | © OpenStreetMap contributors, ODbL |
| NCZI – výstup S01 o sieti poskytovateľov (tabuľky T2) | kontrola našich počtov po krajoch, úväzky lekárov po krajoch (U9) | 31. 12. 2024 | citujeme zdroj |

## Výber ambulancií

Každá ambulancia má v registri 12-znakový kód poskytovateľa zdravotnej starostlivosti.

| Pravidlo | Čo to znamená |
|---|---|
| Odborné zameranie (znaky 7 až 9 kódu) | **VLD** = kód **020** (všeobecné lekárstvo). **VLDD** = kód **008** (všeobecná starostlivosť o deti a dorast). Kód 007 (pediatria) je odborná ambulancia a nezapočítavame ho. Číselník NCZI „Odborné zameranie v zariadení“ (OID 1.3.158.00165387.100.10.39). |
| Druh činnosti (znak 10) | Iba **2 – ambulancia**. Iné druhy, napríklad stacionár, nezapočítavame. Číselník NCZI „Typ odbornej činnosti“ (OID 1.3.158.00165387.100.10.37). |
| Platnosť | Iba záznamy platné k dátumu stavu registra: platnosť sa začala najneskôr v tento deň a neskončila pred ním. |
| Ten istý kód viackrát | Ponecháme záznam s najneskorším začiatkom platnosti. |
| Skrytie na žiadosť | Skrytý záznam sa nepoužije nikde, ani v súhrnných počtoch. Počet je v časti [Aktuálny stav dát](#aktualne). |

## Ukazovatele

Ambulancia je **jeden kód v registri**, nie jeden lekár. Jeden lekár môže mať viac ambulancií a v jednej ambulancii môže pracovať viac lekárov.

| | Ukazovateľ | Úroveň | Výpočet v skratke |
|---|---|---|---|
| [U1](#u1) | Počet ambulancií | okres | ambulancie s polohou v okrese |
| [U2](#u2) | Ambulancie na 10 000 obyvateľov | okres | U1 / menovateľ × 10 000 |
| [U3](#u3) | Vzdialenosť k najbližšej ambulancii | obec | vzdušná čiara z bodu sídla obce |
| [U4](#u4) | Počet ambulancií do 10 a 20 km | obec | ambulancie do danej vzdialenosti |
| [U5](#u5) | Poradie okresov | okres | podľa U2, 1 = najmenej |
| [U6](#u6) | Počet pracovísk (doplnkový) | okres | rovnaké IČO a adresa = jedno pracovisko |
| [U7](#u7) | Podiel obyvateľov ďalej ako 5 a 10 km | okres | ľudia v obciach s U3 nad 5, resp. 10 km |
| [U8](#u8) | Ambulancie v okolí 10 km na 10 000 | okres | metóda 2SFCA |
| [U9](#u9) | Úväzky lekárov na 10 000 | kraj | úväzky NCZI / menovateľ × 10 000 |

**Menovateľ** pri všetkých ukazovateľoch na obyvateľa: pri VLD obyvatelia vo veku 18 a viac rokov, pri pediatroch 0 až 17 rokov. Rovnaké vekové skupiny používa aj NCZI.

<a id="u1"></a>

### U1 – Počet ambulancií v okrese

| | |
|---|---|
| Čo meria | počet ambulancií daného typu, ktorých poloha leží v okrese |
| Obmedzenia | ambulancia nie je lekár ani úväzok (pozri [U9](#u9)) |

<a id="u2"></a>

### U2 – Ambulancie na 10 000 obyvateľov (okres)

| | |
|---|---|
| Výpočet | **U2 = U1 / menovateľ × 10 000**, zaokrúhlené na dve desatinné miesta |
| Menovateľ | obyvatelia okresu 18+ (VLD) alebo 0 – 17 (pediatri), STATdata om7006rr, pohlavie spolu, rok 2025 |
| Stredný stav | Je to **stredný (priemerný) stav obyvateľstva v roku 2025**. ŠÚ SR ho počíta ako priemer stavov na začiatku a na konci roka, preto majú niektoré obce polovičné hodnoty (napr. 171,5). Používame ich bez zaokrúhlenia. |
| Spojenie s obcami | Export STATdata neobsahuje kódy obcí. Obce spájame s hranicami ZBGIS podľa okresu a názvu. Spojí sa všetkých 2 927 obcí a súčet sa rovná údaju za Slovensko. |
| Obmedzenia | Ľudia chodia k lekárovi aj mimo svojho okresu, najmä do miest. Pri Bratislave a Košiciach, rozdelených na viac okresov, môžu centrá (Bratislava I, Košice I) vychádzať najlepšie a iné mestské okresy najhoršie. Preto uvádzame aj [U8](#u8). V malých okresoch zmení jedna ambulancia hodnotu výrazne. Pre jednotlivé obce pomer nepočítame, lebo väčšina obcí vlastnú ambulanciu nemá. |

<a id="u3"></a>

### U3 – Vzdialenosť k najbližšej ambulancii (obec)

| | |
|---|---|
| Čo meria | vzdušnú vzdialenosť v km z **referenčného bodu obce** k najbližšej ambulancii daného typu, aj v inom okrese |
| Referenčný bod | bod sídla obce zo ZBGIS (vrstva geografických názvov obcí). Leží v obci, spravidla v zastavanej časti. Geometrický stred územia nepoužívame, lebo pri rozľahlých obciach padne do hôr alebo lesa. Ak bod sídla chýba alebo leží mimo obce, použijeme stred územia, prípadne bod, ktorý zaručene leží vnútri. |
| Výpočet | vzorec haversine na guli s polomerom 6 371 km. Web aj Python používajú rovnaký vzorec a rovnako zaokrúhlené súradnice, aby sa čísla zhodovali. |
| Obmedzenia | Skutočná cesta autom alebo autobusom je dlhšia. Všetci obyvatelia obce dostanú vzdialenosť z jedného bodu, hoci obec môže mať viac častí. |

<a id="u4"></a>

### U4 – Počet ambulancií do 10 a do 20 km (obec)

| | |
|---|---|
| Čo meria | počet ambulancií daného typu najviac 10 km, resp. 20 km vzdušnou čiarou od referenčného bodu obce |
| „V obci“ | ambulancie, ktorých poloha leží na území obce |

<a id="u5"></a>

### U5 – Poradie okresov

| | |
|---|---|
| Čo meria | poradie okresov podľa U2 od najnižšej hodnoty: 1. miesto = najmenej ambulancií na obyvateľa |
| Rovnaké hodnoty | majú rovnaké poradie. Rovnako počítame aj poradie podľa [U8](#u8). |

<a id="u6"></a>

### U6 – Počet pracovísk v okrese (doplnkový)

| | |
|---|---|
| Čo meria | počet rôznych **pracovísk**: jedna dvojica IČO poskytovateľa a adresy ambulancie. Viac kódov toho istého poskytovateľa na jednej adrese je jedno pracovisko, rovnaká adresa s iným IČO je iné pracovisko. |
| Prečo | Jeden poskytovateľ má niekedy na jednom mieste viac kódov, a preto je U1 vyšší než počet miest, kam pacient reálne chodí. Hlavným ukazovateľom ostáva U1, z neho sa počítajú farby mapy aj rebríček. |
| Obmedzenia | Adresy porovnávame tak, ako sú zapísané v registri. Rovnaká adresa zapísaná inak sú dve pracoviská. Ani pracovisko nehovorí o počte lekárov. |

<a id="u7"></a>

### U7 – Podiel obyvateľov ďalej ako 5 a 10 km (okres)

| | |
|---|---|
| Čo meria | podiel obyvateľov okresu z príslušnej vekovej skupiny, ktorí bývajú v obciach s najbližšou ambulanciou ([U3](#u3)) ďalej ako 5 km, resp. 10 km. Ambulancia môže byť aj v inom okrese. |
| Prečo | U2 hovorí, koľko ambulancií pripadá na obyvateľov, ale nie, ako ďaleko to ľudia majú. Riedko osídlený okres môže mať veľa ambulancií na obyvateľa, a predsa veľa ľudí ďaleko od najbližšej z nich. |
| Obmedzenia | rovnaké ako pri U3. Ukazovateľ nehovorí o kapacite ambulancií. |

<a id="u8"></a>

### U8 – Ambulancie v okolí 10 km na 10 000 obyvateľov (okres)

| | |
|---|---|
| Čo meria | koľko ambulancií pripadá na obyvateľov, keď ľudia môžu chodiť aj do iných obcí a okresov a o každú ambulanciu sa delia všetci, čo to k nej majú blízko. Metóda dvoch krokov s plávajúcou spádovou oblasťou (2SFCA, Luo a Wang, 2003). |
| Krok 1 | Pre každú ambulanciu sčítame obyvateľov vo všetkých obciach, ktorých referenčný bod je od nej vzdušne do 10 km. Ambulancia pripadá na všetkých rovnako. |
| Krok 2 | Pre každú obec sčítame, aká časť každej ambulancie do 10 km pripadá na jedného obyvateľa, a vynásobíme 10 000. |
| Okres | priemer obcí okresu vážený počtom obyvateľov |
| Kontrola | Všetky ambulancie sa rozdelia medzi obyvateľov presne raz, nič sa nestratí ani nepridá. Jednotka je rovnaká ako pri U2, preto má mapa rovnakú legendu. |
| Obmedzenia | Vzdialenosť je vzdušnou čiarou. Polomer 10 km je pevná hranica: ambulancia vo vzdialenosti 9 km sa započíta celá, vo vzdialenosti 11 km vôbec. Všetky ambulancie majú rovnakú váhu, lebo ich kapacitu nepoznáme. Neberieme do úvahy obyvateľov ani ambulancie za hranicami Slovenska. |

Príklad: obce A (1 000 dospelých) a B (3 000 dospelých) sú od seba 5,6 km a jediná ambulancia je v obci A. Do 10 km od nej býva 4 000 dospelých, preto obom obciam vyjde 1 ambulancia na 4 000 ľudí, teda 2,5 na 10 000. Keby sme počítali iba ambulancie v obci, A by mala 10 na 10 000 a B žiadnu.

Zdroj metódy: Luo W., Wang F. (2003): Measures of spatial accessibility to health care in a GIS environment: synthesis and a case study in the Chicago region. Environment and Planning B 30(6), 865 – 884, doi:10.1068/b29120.

<a id="u9"></a>

### U9 – Úväzky lekárov na 10 000 obyvateľov (kraj)

| | |
|---|---|
| Prečo | Register hovorí, koľko je ambulancií, ale nie, koľko lekárov v nich pracuje. Tento údaj zverejňuje NCZI. |
| Zdroj | NCZI, výstup S01 2024, tabuľky T2, stĺpec „Počet pracovných miest – Lekári“, riadky „ambulancia_výstup“, odbornosti 008 a 020. Pracovné miesto je súčet úväzkov prepočítaný na plný pracovný čas: dvaja lekári na polovičný úväzok sú jedno pracovné miesto. |
| Výpočet | **U9 = úväzky lekárov v kraji / menovateľ × 10 000**, zaokrúhlené na dve desatinné miesta. Menovateľ ako pri U2, sčítaný za okresy kraja. Uvádzame aj priemerný úväzok na jeden útvar NCZI (úväzky / počet útvarov, oboje z NCZI). |
| Kontrola | Súčet krajov sa rovná údaju za Slovensko a údaj za Slovensko overenej hodnote (VLD 1 743,07, VLDD 812,72). |
| Porovnanie s NCZI | Tabuľka T2.9 uvádza úväzky na 100 000 obyvateľov. Pri VLD sa naše hodnoty (×10) líšia najviac o 0,4 %, pri pediatroch sú o 0,1 až 0,8 % vyššie. Za Slovensko NCZI pri pediatroch delí asi 1 025 875 deťmi. To je menej ako stredný stav 2024 (1 028 343) a viac ako stredný stav 2025 (1 020 767), ktorý používame my. Pravdepodobne ide o stav k 31. 12. 2024 (OVERIŤ, O20). |
| Obmedzenia | NCZI uvádza úväzky iba za Slovensko a kraje. Údaje NCZI sú za rok 2024, obyvatelia za rok 2025. Útvar NCZI nemusí zodpovedať jednému kódu v registri (O8), preto úväzky nedelíme počtom ambulancií v registri. Úväzok nehovorí o tom, či lekár prijíma nových pacientov. |

## Poloha ambulancií

Adresu ambulancie (miesto prevádzkovania podľa registra) prevádzame na súradnice cez OpenStreetMap Nominatim. Posielame mu iba adresu, nikdy názov poskytovateľa. Výsledky ukladáme a tú istú adresu sa nepýtame dvakrát. Obec z adresy hľadáme podľa názvu v ZBGIS. Pri „Bratislava“ a „Košice“ bez mestskej časti pripúšťame ktorúkoľvek mestskú časť. Miestne časti, ktoré nie sú obcou (napr. Tatranská Lomnica), priraďujeme podľa katastrálnych území.

Polohu hľadáme v tomto poradí a použijeme prvý bod, ktorý leží v obci z registra:

| Poradie | Pokus | Presnosť na webe |
|---|---|---|
| 1 | ručne overená poloha (použije sa vždy) | ručne overená |
| 2 | presná adresa: ulica a číslo, obec, PSČ | presná adresa alebo ulica |
| 3 | upravené znenie adresy, ak presná nič nenájde: bez „ul.“ a „č.“, s prehodeným súpisným a orientačným číslom, pri obciach bez ulíc iba obec a číslo domu | presná adresa alebo ulica |
| 4 | tá istá adresa hľadaná iba na území obce, ak bod padol mimo nej | presná adresa alebo ulica |
| 5 | obec a PSČ | iba stred obce |
| 6 | referenčný bod obce | iba stred obce |

- Každý bod musí ležať na území Slovenska.
- Bod najviac 300 m za hranicou obce z registra ponecháme (hranica často vedie ulicou), ale ambulanciu započítame do obce a okresu podľa registra.
- Ak pripadá do úvahy viac obcí s rovnakým názvom a žiadny bod do nich nepadne, bod overujeme ručne.

## Kontrola kvality

Každý krok spracovania končí kontrolami. Chyba zastaví spracovanie a výsledky sa nezverejnia. Upozornenie iba zapíšeme a vysvetlíme.

| Čo kontrolujeme | Čo sa stane pri probléme |
|---|---|
| stĺpce registra, formát kódov, čitateľnosť dátumov | chyba: spracovanie sa zastaví |
| počty ambulancií oproti očakávaným hodnotám a oproti minulému mesiacu | upozornenie, pri zmene za Slovensko nad 15 % chyba |
| súradnice mimo Slovenska, adresy bez polohy | chyba |
| podozrivé zhluky viacerých adries na jednom bode | upozornenie |
| bod sídla obce mimo jej územia | chyba |
| obec bez bodu sídla (použije sa stred územia) | upozornenie |
| obce s vlastnou ambulanciou, ale s referenčným bodom ďalej ako 2 km od nej | informácia na sledovanie |
| možné duplicitné záznamy (rovnaké IČO, typ a adresa) | upozornenie (pozri [U6](#u6)) |
| súčet obyvateľov obcí oproti údaju za Slovensko | chyba |
| pomer register / NCZI po krajoch mimo 0,8 – 1,6 | iba upozornenie, nikdy neblokuje zverejnenie |

<a id="nczi"></a>

## Porovnanie s NCZI

Porovnávame počet ambulancií v registri ÚDZS s „počtom útvarov“ v tabuľkách NCZI T2 (výstup S01 za rok 2024, riadky „ambulancia_výstup“, odbornosti 008 a 020, stav k 31. 12. 2024). Kraj ambulancie určujeme podľa adresy v registri.

| | VLD | Pediatri (VLDD) |
|---|---:|---:|
| Register k 1. 10. 2026 | 2 433 | 1 101 |
| NCZI, počet útvarov k 31. 12. 2024 | 1 891 | 885 |
| Rozdiel | +29 % | +24 % |
| z toho kódy s platnosťou od 1. 1. 2025 | 266 | 136 |
| Rozdiel bez nich a so zlúčením kódov s rovnakým IČO a adresou | +8 % | +6 % |

Rozdiel je vo všetkých krajoch, najväčší v Bratislavskom. Kódy začaté po 31. 12. 2024 údaje NCZI ešte nemôžu obsahovať. Ďalšiu časť tvoria viaceré kódy toho istého poskytovateľa na tej istej adrese.

Neoverené hypotézy: nový kód môže nahrádzať starší na tom istom mieste, „útvar“ NCZI nemusí zodpovedať jednému kódu v registri a časť kódov nemusí mať reálnu činnosť ani zmluvu s poisťovňou.

Záznamy kvôli rozdielu nefiltrujeme. Každý platný kód počítame ako jednu ambulanciu (U1), doplnkovo uvádzame pracoviská (U6).

## Obmedzenia

| Obmedzenie | Čo to znamená pre čitateľa |
|---|---|
| Register obsahuje kódy poskytovateľov | kód neznamená, že ambulancia skutočne funguje alebo má zmluvu s poisťovňou |
| Register neuvádza prijímanie pacientov, ordinačné hodiny, telefón ani počet lekárov | tieto údaje overte u svojej zdravotnej poisťovne. Pri spoločnostiach je uvedený iba názov firmy. |
| Počet ambulancií nie je kapacita | nehovorí o úväzkoch ani o počte pacientov. Úväzky lekárov poznáme iba za kraje ([U9](#u9)). |
| Vzdialenosti sú vzdušnou čiarou | skutočná cesta je dlhšia |
| Zdroje majú rôzne dátumy | register, obyvatelia a NCZI nie sú k rovnakému dňu |
| Hranice obcí sú na webe zjednodušené | výpočty používajú presné hranice |

## Reprodukovateľnosť

Každý výstup nesie dátum zdrojových dát a verziu výpočtu. Celý postup je v otvorenom zdrojovom kóde a dá sa zopakovať. Surové dáta s menami poskytovateľov sa do repozitára neukladajú. Register si pipeline stiahne z pôvodného zdroja, počty obyvateľov zo STATdata sa podľa podmienok Štatistického úradu SR sťahujú ručne.

## História zmien metodiky

| Verzia | Dátum | Zmena |
|---|---|---|
| 0.1.0 | október 2026 | prvá verzia: ukazovatele U1 až U5, doplnkový U6 (pracoviská), U7 (podiel obyvateľov ďalej ako 5 a 10 km), U8 (ambulancie v okolí 10 km, 2SFCA) a U9 (úväzky lekárov z NCZI 2024 po krajoch); referenčný bod obce je bod sídla zo ZBGIS; obyvatelia zo STATdata (om7006rr, stredný stav 2025); kontrola s NCZI S01 2024; poloha musí ležať v obci z registra (tolerancia 300 m) |

<a id="oprava"></a>

## Oprava alebo odstránenie záznamu

Ak je záznam o vašej ambulancii nesprávny alebo nechcete, aby sa zobrazoval, napíšte na projektový e-mail uvedený nižšie. Uveďte názov a adresu ambulancie tak, ako sú na stránke, a čo treba opraviť alebo skryť. Žiadosť vybavíme bez zbytočného odkladu. Skrytý záznam sa nepoužije nikde, ani v súhrnných počtoch. Ak je chyba priamo v registri ÚDZS, opravu treba žiadať aj u ÚDZS. Viac na stránke [Ochrana súkromia a kontakt](sukromie.html).
