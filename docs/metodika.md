# Metodika

Táto stránka je **neoficiálna analýza verejných dát**. Ukazuje, kde sú ambulancie všeobecných lekárov pre dospelých a pediatrov prvého kontaktu **evidované v registri** Úradu pre dohľad nad zdravotnou starostlivosťou (ÚDZS). Ako ďaleko sú od obcí a koľko ich pripadá na obyvateľov okresu.

Stránka **neukazuje**, či ambulancia prijíma nových pacientov, aké má ordinačné hodiny, koľko v nej pracuje lekárov ani aké sú čakacie doby. Tieto údaje register neobsahuje. Kontakt a ordinačné hodiny overte vo vyhľadávaní lekárov svojej zdravotnej poisťovne.

## Zdroje dát

| Zdroj | Čo z neho používame | Licencia |
|---|---|---|
| ÚDZS – Kódy poskytovateľov zdravotnej starostlivosti (XLSX) | názov poskytovateľa, odbornosť z kódu, adresa ambulancie, platnosť záznamu | licencia nie je uvedená |
| Štatistický úrad SR – STATdata, tabuľka om7006rr | počet obyvateľov obcí vo veku 0 – 17 a 18+ (menovateľ) | CC BY 4.0, „Zdroj: Štatistický úrad SR, CC BY 4.0, www.statistics.sk“ |
| ÚGKK SR – ZBGIS | hranice obcí a okresov, bod sídla každej obce (geografické názvy obcí) | CC BY 4.0, hranice sú pre web zjednodušené |
| OpenStreetMap – Nominatim | poloha (súradnice) adries ambulancií | © OpenStreetMap contributors, ODbL |
| NCZI – výstup S01 o sieti poskytovateľov (tabuľky T2) | kontrola našich počtov po krajoch a úväzky lekárov po krajoch (U9) | citujeme zdroj |

Dátum stavu registra a obyvateľstva je uvedený na každej stránke a v časti [Aktuálny stav dát](#aktualne).

## Výber ambulancií

- Každá ambulancia má v registri 12-znakový kód poskytovateľa zdravotnej starostlivosti. Znaky 7 až 9 označujú odborné zameranie podľa číselníka NCZI „Odborné zameranie v zariadení“ (OID 1.3.158.00165387.100.10.39).
- **VLD** – všeobecný lekár pre dospelých: kód **020** (všeobecné lekárstvo).
- **VLDD** – pediater prvého kontaktu: kód **008** (všeobecná starostlivosť o deti a dorast). Kód 007 (pediatria) je odborná pediatrická ambulancia a nezapočítavame ho.
- Znak 10 označuje druh odbornej činnosti podľa číselníka NCZI „Typ odbornej činnosti“ (OID 1.3.158.00165387.100.10.37). Započítavame iba druh **2 – ambulancia**. Iné druhy, napríklad stacionár, nezapočítavame.
- Započítavame iba záznamy platné k dátumu stavu registra: platnosť sa začala najneskôr v tento deň a neskončila pred ním.
- Ak je ten istý kód v registri viackrát, ponecháme záznam s najneskorším začiatkom platnosti.
- Na žiadosť dotknutej osoby môžeme záznam vylúčiť. Vtedy sa nepoužije nikde, ani v súhrnných počtoch. Počet takých záznamov uvádzame v časti [Aktuálny stav dát](#aktualne).

## Ukazovatele

<a id="u1"></a>

### U1 – Počet ambulancií v okrese

Počet ambulancií daného typu, ktorých poloha leží v okrese. Ambulancia je jeden kód v registri. Nie je to jeden lekár ani jeden úväzok: jeden lekár môže mať viac ambulancií a v jednej ambulancii môže pracovať viac lekárov.

<a id="u2"></a>

### U2 – Ambulancie na 10 000 obyvateľov (okres)

**U2 = U1 / menovateľ × 10 000**, zaokrúhlené na dve desatinné miesta.

- Menovateľ pre VLD: obyvatelia okresu vo veku 18 a viac rokov.
- Menovateľ pre pediatrov: obyvatelia okresu vo veku 0 až 17 rokov. Rovnaké vekové skupiny (0 – 17 a 18+) používa aj NCZI pri prepočte lekárov na obyvateľov.
- Počty obyvateľov sú zo STATdata Štatistického úradu SR (tabuľka om7006rr, pohlavie spolu, rok 2025). Je to **stredný (priemerný) stav obyvateľstva v roku 2025**, teda počet obyvateľov ku stredu roka. ŠÚ SR ho počíta ako priemer stavov na začiatku a na konci roka, preto majú niektoré obce polovičné hodnoty (napr. 171,5). Používame ich bez zaokrúhlenia. Dátum sa líši od dátumu registra.
- Export STATdata neobsahuje kódy obcí. Obce spájame s hranicami ZBGIS podľa okresu a názvu obce. Spojí sa všetkých 2 927 obcí a súčet obcí sa rovná údaju za Slovensko.

Obmedzenia: ľudia chodia k lekárovi aj mimo svojho okresu, najmä do miest. Mestské okresy preto môžu vychádzať lepšie, než zodpovedá ich vlastnému obyvateľstvu. Výrazné je to pri Bratislave a Košiciach, ktoré sú rozdelené na viac okresov: centrá (Bratislava I, Košice I) môžu vychádzať najlepšie a iné mestské okresy najhoršie. Preto uvádzame aj [U8](#u8), ktorý počíta s ambulanciami v okolí. V malých okresoch zmení jedna ambulancia hodnotu výrazne. Pre jednotlivé obce tento pomer nepočítame. Väčšina obcí vlastnú ambulanciu nemá a pri malom počte obyvateľov by pomer bol zavádzajúci.

<a id="u3"></a>

### U3 – Vzdialenosť k najbližšej ambulancii (obec)

Vzdušná vzdialenosť v kilometroch z **referenčného bodu obce** k najbližšej ambulancii daného typu, aj v inom okrese. Referenčný bod je bod sídla obce zo ZBGIS, teda bod, ku ktorému ZBGIS priraďuje názov obce (vrstva geografických názvov obcí). Leží v obci, spravidla v jej zastavanej časti. Geometrický stred územia sme nepoužili, lebo pri rozľahlých obciach často padne do hôr alebo lesa. Ak by obec bod sídla nemala alebo by ležal mimo jej územia, použijeme geometrický stred územia, prípadne bod, ktorý zaručene leží vnútri.

Vzdialenosť počítame vzorcom haversine na guli s polomerom 6 371 km. Na webe aj v Pythone používame rovnaký vzorec a rovnaké zaokrúhlené súradnice, aby sa čísla zhodovali.

Obmedzenia: skutočná cesta autom alebo autobusom je dlhšia. Všetci obyvatelia obce dostanú vzdialenosť z jedného bodu, hoci obec môže mať viac častí alebo osád.

<a id="u4"></a>

### U4 – Počet ambulancií do 10 a do 20 km (obec)

Počet ambulancií daného typu, ktorých vzdušná vzdialenosť od referenčného bodu obce je najviac 10 km, resp. 20 km. Pri hodnote „v obci“ počítame ambulancie, ktorých poloha leží na území obce.

<a id="u5"></a>

### U5 – Poradie okresov

Okresy zoradené podľa U2 od najnižšej hodnoty. Prvé miesto znamená najmenej ambulancií na obyvateľa, teda najhoršiu dostupnosť. Rovnaké hodnoty majú rovnaké poradie. Rovnako počítame aj poradie podľa [U8](#u8).

<a id="u6"></a>

### U6 – Počet pracovísk v okrese (doplnkový)

Počet rôznych **pracovísk** daného typu v okrese. Pracovisko je jedna dvojica IČO poskytovateľa a adresy ambulancie (ulica, obec a PSČ podľa registra). Ak má ten istý poskytovateľ na tej istej adrese viac kódov, počítame ich ako jedno pracovisko. Rovnaká adresa s iným IČO je iné pracovisko.

Prečo ho uvádzame: v registri má niekedy jeden poskytovateľ na jednom mieste viac kódov, a preto je počet kódov (U1) vyšší než počet miest, kam pacient reálne chodí. Hlavným ukazovateľom ostáva U1. Farby mapy aj rebríček sa počítajú z U2, ktorý vychádza z U1.

Obmedzenia: adresu porovnávame tak, ako je zapísaná v registri. Rovnaká adresa napísaná inak (napr. iné poradie čísel) sa počíta ako dve pracoviská. Ani pracovisko nehovorí o počte lekárov ani o úväzkoch.

<a id="u7"></a>

### U7 – Podiel obyvateľov ďalej ako 5 a 10 km (okres)

Podiel obyvateľov okresu z príslušnej vekovej skupiny (18+ pri všeobecných lekároch, 0 – 17 pri pediatroch), ktorí bývajú v obciach, ktorých referenčný bod je od najbližšej ambulancie daného typu vzdušne ďalej ako 5 km, resp. 10 km (pozri [U3](#u3)). Ambulancia môže byť aj v inom okrese.

Prečo ho uvádzame: U2 hovorí, koľko ambulancií pripadá na obyvateľov okresu, ale nie, ako ďaleko to majú ľudia. Riedko osídlený okres môže mať veľa ambulancií na obyvateľa, a predsa veľa ľudí ďaleko od najbližšej z nich.

Obmedzenia: rovnaké ako pri U3. Všetci obyvatelia obce dostanú vzdialenosť jej referenčného bodu a vzdialenosť je vzdušnou čiarou. Ukazovateľ nehovorí o kapacite ambulancií.

<a id="u8"></a>

### U8 – Ambulancie v okolí 10 km na 10 000 obyvateľov (okres)

Ukazovateľ počíta s tým, že ľudia môžu chodiť aj k ambulanciám mimo svojej obce a okresu, a že o každú ambulanciu sa delia všetci, ktorí to k nej majú blízko. Je to metóda dvoch krokov s plávajúcou spádovou oblasťou (2SFCA, Luo a Wang, 2003):

1. Pre každú ambulanciu sčítame obyvateľov príslušnej vekovej skupiny vo všetkých obciach, ktorých referenčný bod je od nej vzdušne do 10 km. Ambulancia pripadá na všetkých týchto ľudí rovnako.
2. Pre každú obec sčítame, aká časť každej ambulancie do 10 km od jej referenčného bodu pripadá na jedného obyvateľa, a výsledok vynásobíme 10 000.
3. Hodnota okresu je priemer jeho obcí vážený počtom obyvateľov.

Príklad: obce A (1 000 dospelých) a B (3 000 dospelých) sú od seba 5,6 km a jediná ambulancia je v obci A. Do 10 km od nej býva 4 000 dospelých, preto obom obciam vyjde 1 ambulancia na 4 000 ľudí, teda 2,5 na 10 000. Keby sme počítali iba ambulancie v obci, A by mala 10 na 10 000 a B žiadnu.

Všetky ambulancie sa pri tom rozdelia medzi obyvateľov presne raz: nič sa nestratí ani nepridá (kontrolujeme to). Jednotka je rovnaká ako pri U2, preto na mape používame rovnakú legendu.

Obmedzenia: vzdialenosť je vzdušnou čiarou z referenčného bodu obce. Polomer 10 km je pevná hranica: ambulancia vo vzdialenosti 9 km sa započíta celá, vo vzdialenosti 11 km vôbec. Všetky ambulancie majú rovnakú váhu, lebo ich kapacitu nepoznáme. Neberieme do úvahy obyvateľov ani ambulancie za hranicami Slovenska.

Zdroj metódy: Luo W., Wang F. (2003): Measures of spatial accessibility to health care in a GIS environment: synthesis and a case study in the Chicago region. Environment and Planning B 30(6), 865 – 884, doi:10.1068/b29120.

<a id="u9"></a>

### U9 – Úväzky lekárov na 10 000 obyvateľov (kraj)

Register ÚDZS hovorí, koľko je ambulancií, ale nie, koľko lekárov v nich pracuje. Tento údaj zverejňuje NCZI vo výstupe S01 (tabuľky T2, stĺpec „Počet pracovných miest – Lekári“, riadky „ambulancia_výstup“, odbornosti 008 a 020). Pracovné miesto je podľa NCZI súčet úväzkov pracovníkov prepočítaný na plný pracovný čas, takže dvaja lekári na polovičný úväzok sú jedno pracovné miesto.

**U9 = úväzky lekárov v kraji / menovateľ × 10 000**, zaokrúhlené na dve desatinné miesta. Menovateľ je rovnaký ako pri U2 (18+ pri VLD, 0 – 17 pri pediatroch), sčítaný za okresy kraja. Uvádzame aj priemerný úväzok na jeden útvar NCZI (úväzky / počet útvarov, oboje z NCZI).

Kontrola: súčet úväzkov za kraje sa musí rovnať údaju za Slovensko a údaj za Slovensko overenej hodnote (VLD 1 743,07, VLDD 812,72).

Porovnanie s NCZI: tabuľka T2.9 uvádza úväzky na 100 000 obyvateľov rovnakých vekových skupín. Pri VLD sa naše hodnoty (×10) líšia najviac o 0,4 %. Pri pediatroch sú o 0,1 až 0,8 % vyššie, pravdepodobne preto, že NCZI delí iným rokom obyvateľstva (OVERIŤ, O20).

Obmedzenia: NCZI uvádza úväzky iba za Slovensko a kraje, za okresy nie. Údaje NCZI sú za rok 2024, obyvatelia za rok 2025 a register k inému dátumu. Útvar v NCZI nemusí zodpovedať jednému kódu v registri (O8), preto úväzky nedelíme počtom ambulancií v registri. Úväzok nehovorí o tom, či lekár prijíma nových pacientov.

## Poloha ambulancií

Adresu ambulancie (miesto prevádzkovania podľa registra) prevádzame na súradnice cez službu OpenStreetMap Nominatim. Posielame jej iba adresu, nikdy názov poskytovateľa. Výsledky ukladáme a tú istú adresu sa nepýtame dvakrát.

Obec z adresy hľadáme podľa názvu v ZBGIS. Pri názvoch „Bratislava“ a „Košice“ bez mestskej časti pripúšťame ktorúkoľvek mestskú časť. Miestne časti, ktoré nie sú obcou (napr. Tatranská Lomnica), priraďujeme podľa katastrálnych území ZBGIS.

Polohu hľadáme v tomto poradí a použijeme prvý bod, ktorý leží v obci z registra:

1. ručne overená poloha, ak existuje (použije sa vždy),
2. presná adresa (ulica a číslo, obec, PSČ),
3. ak presná adresa nič nenájde: upravené znenie adresy (bez predpôn ako „ul.“ alebo „č.“, s prehodeným súpisným a orientačným číslom, pri obciach bez ulíc iba obec a číslo domu),
4. ak bod presnej adresy leží mimo obce z registra: tá istá adresa hľadaná iba na území tejto obce,
5. obec a PSČ,
6. referenčný bod obce (presnosť „iba stred obce“).

Každý bod musí ležať na území Slovenska. Bod, ktorý leží najviac 300 m za hranicou obce z registra, ponecháme (hranica obce často vedie ulicou), ale ambulanciu započítame do obce a okresu podľa registra. Ak pri adrese pripadá do úvahy viac obcí s rovnakým názvom a žiadny bod do nich nepadne, bod overujeme ručne. Pri každej ambulancii uvádzame presnosť polohy: presná adresa, ulica alebo iba stred obce.

## Kontrola kvality

Každý krok spracovania končí kontrolami. Ak kontrola zlyhá, výsledky sa nezverejnia. Kontrolujeme najmä:

- očakávané stĺpce registra, formát kódov a čitateľnosť dátumov,
- počty ambulancií oproti očakávaným hodnotám a oproti minulému mesiacu,
- súradnice mimo Slovenska, adresy bez polohy a podozrivé zhluky na jednom bode,
- či má každá obec bod sídla a či obce s vlastnou ambulanciou nemajú referenčný bod ďaleko od nej,
- možné duplicitné záznamy,
- súčty počtov obyvateľov oproti údaju za Slovensko,
- porovnanie našich počtov po krajoch s tabuľkami NCZI (pozri nižšie). Upozorní, ak je pomer register / NCZI v niektorom kraji mimo 0,8 – 1,6, a nikdy neblokuje zverejnenie.

<a id="nczi"></a>

## Porovnanie s NCZI

Porovnávame počet ambulancií v registri ÚDZS s „počtom útvarov“ v tabuľkách NCZI T2 (výstup S01 o sieti poskytovateľov za rok 2024, riadky „ambulancia_výstup“, odbornosti 008 a 020). NCZI uvádza stav k 31. 12. 2024. Kraj ambulancie určujeme podľa adresy v registri.

Register má k 1. 10. 2026 o 29 % viac ambulancií všeobecných lekárov pre dospelých (2 433 vs. 1 891) a o 24 % viac ambulancií pediatrov prvého kontaktu (1 101 vs. 885). Rozdiel je vo všetkých krajoch, najväčší v Bratislavskom kraji.

Čo sme overili výpočtom:

- Približne polovicu rozdielu pri VLD a viac ako polovicu pri pediatroch tvoria kódy, ktorých platnosť sa začala až po 31. 12. 2024 (266 VLD a 136 VLDD). Údaje NCZI ich ešte nemôžu obsahovať.
- Ďalšiu časť tvoria viaceré kódy toho istého poskytovateľa (IČO) na tej istej adrese.
- Bez kódov začatých po 31. 12. 2024 a so zlúčením kódov s rovnakým IČO a adresou by bol rozdiel 8 % pri VLD a 6 % pri pediatroch.

Možné ďalšie príčiny, ktoré sme neoverili (hypotézy): nový kód môže nahrádzať starší kód na tom istom mieste, „útvar“ v NCZI nemusí zodpovedať jednému kódu v registri a časť kódov nemusí mať reálnu činnosť ani zmluvu s poisťovňou.

Záznamy kvôli tomuto rozdielu nefiltrujeme. Každý platný kód v registri počítame ako jednu ambulanciu (pozri U1). Doplnkovo uvádzame počet pracovísk, v ktorom sa viac kódov toho istého poskytovateľa na jednej adrese počíta raz (pozri U6).

## Obmedzenia

- Register obsahuje kódy poskytovateľov. Existencia kódu neznamená, že ambulancia skutočne funguje alebo má zmluvu so zdravotnou poisťovňou.
- Register neuvádza, či ambulancia prijíma nových pacientov, ordinačné hodiny, telefón, počet lekárov ani meno ordinujúceho lekára. Pri spoločnostiach je uvedený iba názov firmy.
- Počet ambulancií nie je kapacita: nehovorí o úväzkoch ani o počte pacientov. Úväzky lekárov poznáme iba za kraje (U9).
- Vzdialenosti sú vzdušnou čiarou, nie po ceste.
- Zdroje majú rôzne dátumy stavu.
- Hranice obcí sú na webe zjednodušené. Výpočty používajú presné hranice.

## Reprodukovateľnosť

Každý výstup nesie dátum zdrojových dát a verziu výpočtu. Celý postup je v otvorenom zdrojovom kóde a dá sa zopakovať. Surové dáta s menami poskytovateľov sa do repozitára neukladajú. Register si pipeline stiahne z pôvodného zdroja, počty obyvateľov zo STATdata sa podľa podmienok Štatistického úradu SR sťahujú ručne.

## História zmien metodiky

| Verzia | Dátum | Zmena |
|---|---|---|
| 0.1.0 | október 2026 | prvá verzia: ukazovatele U1 až U5, doplnkový U6 (pracoviská), U7 (podiel obyvateľov ďalej ako 5 a 10 km) a U8 (ambulancie v okolí 10 km, 2SFCA), U9 (úväzky lekárov z NCZI 2024 po krajoch); referenčný bod obce je bod sídla zo ZBGIS; obyvatelia zo STATdata (om7006rr, stredný stav 2025); kontrola s NCZI S01 2024; poloha musí ležať v obci z registra (tolerancia 300 m) |

<a id="oprava"></a>

## Oprava alebo odstránenie záznamu

Ak je záznam o vašej ambulancii nesprávny, alebo chcete, aby sa na stránke nezobrazoval:

1. Napíšte na projektový e-mail uvedený nižšie. Uveďte názov a adresu ambulancie tak, ako sú zobrazené na stránke, a čo treba opraviť alebo skryť.
2. Prijatie potvrdíme do 2 pracovných dní.
3. Opravu polohy alebo skrytie záznamu urobíme do 5 pracovných dní. Skrytý záznam sa nepoužije nikde, ani v súhrnných počtoch.
4. Ak je chyba priamo v registri ÚDZS (napr. adresa alebo názov), opravu treba požiadať aj u ÚDZS. Stránka preberá údaje z registra.
