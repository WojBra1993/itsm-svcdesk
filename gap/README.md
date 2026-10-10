<!-- ai-generated: 100% - Codex wrote the explanation; numerical results come from an actual Toxiproxy run. -->
# Pomiar opoznienia klienta i serwera

Pomiar UTC: 2026-10-10T19:01:04.3884575Z. Profil kb-index: wojbra1993, tak samo jak login w itsmlab.yaml.
Rzeczywisty pomiar itsmlab load 3: 5 sekund rozgrzewki, potem 60 sekund ruchu
40 zadan na sekunde. Klient kierowal zadania /kb/search przez Toxiproxy do svcdesk.
Toxic dzialal downstream z toxicity=1, latency=100 ms i jitter=10 ms.

Z tego samego przebiegu: p99 klienta = 0.2695000 s, p99 serwera = 0.1625000 s.
gap_seconds = p99 klienta - p99 serwera = 0.1070000 s. Wartosci zapisane w gap.json
pochodza z linii q (p99) oraz your histogram's own p99 over the run w rzeczywistym
wyjsciu checkera. Nie wpisywalem oczekiwanych 100 ms w miejsce wyniku pomiaru.

Klient mierzy czas do otrzymania odpowiedzi przez proxy. Histogram w aplikacji
mierzy wykonanie zadania po stronie serwera, w tym oczekiwanie na kb-index,
do wyslania ostatniego fragmentu odpowiedzi. Opoznienie wstawione przez proxy
jest poza aplikacja, wiec zwieksza czas klienta bez takiego samego wzrostu
czasu serwera. Ten sam serwer moze zatem miec dobry histogram i nadal dawac
uzytkownikowi wyraznie wolniejsza odpowiedz z powodu sieci.

P99 serwera jest estymata histogram_quantile(0.99) z przyrostow bucketow w oknie
pomiaru. P99 klienta pochodzi z oha, z korekta opoznienia planowanego ruchu.
Odejmowanie tych percentyli nie jest pomiarem opoznienia jednej konkretnej
odpowiedzi. Jitter, losowy profil kb-index, granice bucketow i obciazenie hosta
powoduja, ze roznica nie musi wynosic dokladnie 0.100 s. Checker powtarza probe
przez 30 sekund i porownuje roznice z tolerancja max(15 ms, 30% swojej roznicy).

Powtorzenie z katalogu repozytorium: .\scripts\lab3-stretch.ps1 -Part gap.
Skrypt stawia svcdesk, kb-index i Toxiproxy, konfiguruje toxic przez API,
uruchamia checker w tej samej sieci Dockera, zapisuje wyniki i zatrzymuje
wylacznie swoj projekt pomiarowy. Log lokalny: lab3-load-gap.txt.