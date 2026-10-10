---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 30d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search",http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
    latency:
      objective: 0.99
      threshold_seconds: 0.2
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk",http_route="/kb/search",le="0.2"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
  alerts:
    - {alert: KbAvailabilityFastBurn, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbAvailabilitySlowBurn, sli: availability, burn_rate: 6, long_window: 6h, short_window: 30m}
---
<!-- ai-generated: 100% - Codex proposed the SLO and wrote the reasoning from the user's real 10 October load 3 measurement. -->

# SLO dla wyszukiwania w bazie wiedzy

## Availability

Cel to co najmniej 99% odpowiedzi bez błędu serwera w ciągu 30 dni.
SLI dzieli liczbę odpowiedzi innych niż 5xx przez wszystkie odpowiedzi trasy
`/kb/search`. Odpowiedź 422 na niepoprawne pytanie oznacza, że usługa poprawnie
odrzuciła żądanie, więc nie zużywa budżetu dostępności. Odpowiedź 502 go zużywa:
dla użytkownika wyszukiwanie nie działa, nawet gdy przyczyna leży w `kb-index`.

W pierwszym pomiarze profilu `wojbra1993` 2393 odpowiedzi miały kod 200,
a 7 kod 502. To 7 / 2400 = 0,2917% błędów, czyli około 99,7083% dostępności
w tej jednej próbce. Cel 99,9% byłby już gorszy od wyniku próbki. Przy 99%
jest zapas na zmienność zależności. To świadomy kompromis: część wyszukiwań
może się nie udać i użytkownik musi spróbować ponownie. Dla bazy wiedzy
przyjmujemy taki koszt, ale długiej awarii nie traktujemy jako normy.

Budżet wynosi 1 - 0,99 = 0,01, czyli 1% żądań. 30 dni to 43 200 minut,
a 0,01 × 43 200 = 432 minuty. To wymagany odpowiednik czasowy przy równym ruchu,
nie pozwolenie na dowolną 432-minutową awarię: rzeczywisty SLI jest liczony
z żądań. Pięciominutowe zapytania PromQL opisują bieżące tempo dobrych i wszystkich
zdarzeń; nie są samodzielnym dowodem spełnienia celu przez całe 30 dni.

Jeżeli budżet zostanie wyczerpany, priorytetem jest poprawa niezawodności i
wstrzymanie zmian zwiększających ryzyko. Ponowna ocena celu powinna korzystać
z dłuższego pomiaru; minuta ruchu nie dowodzi miesięcznej dostępności.

## Latency

Cel to co najmniej 99% odpowiedzi w czasie do 200 ms po stronie serwera,
w tym samym oknie 30 dni. Próg 0,2 s jest dokładną granicą histogramu.
SLI obejmuje wszystkie statusy; szybka odpowiedź 502 może spełniać cel czasu,
ale równocześnie obniża dostępność. Dlatego oba wskaźniki oceniamy razem.

Pierwszy pomiar klienta pokazał medianę 19,3 ms, p95 30,7 ms, p99 159,2 ms
i p99,9 199,8 ms. Bezpośrednie p99 `kb-index` wyniosło 160,0 ms. Większość
wyszukiwań jest szybka, ale istnieje mała grupa znacznie wolniejszych odpowiedzi.
Próg 200 ms zostawia 40,8 ms, czyli około 25,6%, ponad zmierzonym p99.
Cel 99% nie wymaga, aby każda odpowiedź zmieściła się w tym czasie.

To punkt startowy na podstawie pomiaru klienta. Poprawność nowej estymacji
serwera i zachowanie na innym komputerze sprawdzi kolejny przebieg checkera.
Serwerowy histogram nie obejmuje całej drogi sieciowej klienta, więc nie jest
obietnicą czasu widzianego przez każdego użytkownika.
Budżet opóźnień to osobne 1% odpowiedzi powyżej 200 ms, z odpowiednikiem
432 minut. Budżetu czasu i dostępności nie dodajemy do jednej wspólnej puli.

## Alerts

| alert | SLI | burn rate | długie / krótkie okno | orientacyjnie zużyta część miesięcznego budżetu | kanał |
|---|---|---|---|---|---|
| KbAvailabilityFastBurn | availability | 14,4 | 1h / 5m | 14,4 × 1h / 720h = 2% | P1, wezwanie dyżurnego |
| KbAvailabilitySlowBurn | availability | 6 | 6h / 30m | 6 × 6h / 720h = 5% | P2, wiadomość na czacie |

Obie reguły wymagają przekroczenia progu równocześnie w dwóch oknach oraz
utrzymania warunku przez 5 minut. Krótkie okno pozwala wyłączyć alarm po
ustaniu błędów. Same długie okna zbyt długo utrzymywałyby alarm po naprawie.
Reguły wybierają tylko `/kb/search`, żeby poprawne odpowiedzi innych tras
nie ukryły problemu wyszukiwania. Progi to odpowiednio 14,4% i 6% błędów.

Wartości 2% i 5% są przybliżeniem dla stałego ruchu i spalania na progu
przez całe długie okno, bez dodatkowego czasu `for`. Rzeczywisty koszt zależy
od ruchu i historii błędów. Przy utrzymanym burn rate 14,4 pełny budżet
wystarcza na około 50 godzin, a przy burn rate 6 na 120 godzin.

P1 budzi dyżurnego, bo błąd dotyczy dużej części wyszukiwań i szybkie działanie
ma znaczenie dla osób szukających rozwiązania awarii. W pierwszej kolejności
trzeba sprawdzić odpowiedzi 502 i stan `kb-index`. P2 trafia na czat: wymaga
zbadania utrzymującego się problemu, ale ma mniejsze tempo zużywania budżetu.
Nie uruchamiamy alarmu P1 przy pojedynczym 502, bo zależność czasami zawodzi także w
normalnym stanie. Alerty dostępności nie zastępują obserwacji opóźnień na dashboardzie.

## Buckets

Drabinka ma 28 skończonych granic w sekundach:
`[0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.06, 0.08, 0.1,
0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.2, 0.21,
0.22, 0.23, 0.24, 0.3, 0.5, 1, 2.5, 5]`.

Dla q = 0,1592 s właściwy przedział to (0,15; 0,16] s.
Jego względna szerokość wynosi 0,01 / 0,1592 = 6,28%, poniżej limitu 20%.
Pasmo ±20% wokół tego q to [0,12736; 0,19104] s. Każdy przedział w tym
paśmie ma szerokość 10 ms, najwyżej 0,01 / 0,12736 = 7,85% dolnej granicy
pasma. To zapas większy niż wymagane ±10%, bez dostrajania do jednej liczby.

Granice 5-40 ms pokazują szybkie odpowiedzi i medianę. Gęstsza część 120-240 ms
obejmuje wolny tryb oraz próg SLI. Granice powyżej niego pokazują większe
spowolnienia i timeouty. Biblioteka dodaje nieskończony ostatni przedział.
Etykiety zawierają metodę, szablon trasy i status; nie zawierają tekstu pytania
ani identyfikatora zgłoszenia, więc nowe zapytania nie tworzą nowych szeregów.
