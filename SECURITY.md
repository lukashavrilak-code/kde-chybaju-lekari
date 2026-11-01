# Bezpečnosť

Web je statický: nemá server, databázu, prihlasovanie ani formuláre a neukladá nič v prehliadači návštevníka.

## Nahlásenie zraniteľnosti

Zraniteľnosť nahláste súkromne cez záložku **Security → Report a vulnerability** v tomto repozitári, nie cez verejné Issues. Iný kontakt je na stránke [Ochrana súkromia a kontakt](https://lukashavrilak-code.github.io/kde-chybaju-lekari/sukromie.html).

## Čo projekt robí pre bezpečnosť

- Do Gitu nejdú surové dáta, mená poskytovateľov ani tajomstvá. Kontrolujú to `.gitignore`, pre-commit a CI.
- Na webe je prísna Content Security Policy, knižnica Leaflet sa načítava lokálne a s overením integrity (SRI).
- Závislosti sú pripnuté s hashmi, GitHub Actions cez SHA, `pip-audit` beží v CI.
- Nasadenie používa krátkodobé tokeny GitHub Actions, v repozitári nie je žiadny token ani heslo.
