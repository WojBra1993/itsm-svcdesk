---
lab3_first_draft:
  source: ai
  tool: "Codex, 10 October 2026"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]
  verdict: refuted
  evidence:
    p99_seconds: 0.1592
    bucket: [0.1, 0.25]
    relative_width: 0.942211
lab3_flawed_ladder:
  verdict: refuted
  evidence:
    p99_seconds: 0.1592
    bucket: [0.04, 0.5]
    relative_width: 2.889447
---
<!-- ai-generated: 100% - Codex preserved its original answer and wrote the arithmetic from the user's actual load 3 log. -->

# Pierwsza propozycja przed pomiarem

Poniżej zapisano rzeczywistą prośbę użytkownika i pierwszą
propozycję asystenta z tej rozmowy, przed pomiarem profilu `wojbra1993`.
Prośbie towarzyszyły paczka zadania Lab 3, dokument z Moodle i wynik `docker version`.
Pierwsza wersja została zapisana i wysłana na GitHub w commicie `6e40380`
10 października 2026 przed uruchomieniem pomiaru. Po pomiarze uzupełniono
wyłącznie dowody i komentarze; prompt, odpowiedź oraz jej drabinka pozostały bez zmian.

## Prompt

całe zadanie, E:\IT service managment\LAB3 wypakowane w folderze

## Answer

Moja pierwsza propozycja AI do zapisania przed pomiarem:

Na pierwszy pomiar proponuję granice histogramu w sekundach: `[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]`. To domyślna drabinka biblioteki Python, użyta jako punkt odniesienia. Nie jest jeszcze projektem dopasowanym do Twojej usługi i nie spełnia wymaganego w laboratorium limitu szerokości przedziału przy p99. Po pomiarze wskażemy konkretny przedział i policzymy jego szerokość względem Twojego wyniku.

Jako roboczy alert proponuję dostępność 99% i alarm, gdy udział odpowiedzi 5xx przekracza `14.4 × (1 − 0.99) = 0.144` jednocześnie w oknie jednej godziny i pięciu minut, przez pięć minut:

```yaml
alert: KbAvailabilityFastBurn
expr: |
  (
    sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search",http_response_status_code=~"5.."}[1h]))
    /
    sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search"}[1h]))
    > 14.4 * (1 - 0.99)
  )
  and
  (
    sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search",http_response_status_code=~"5.."}[5m]))
    /
    sum(rate(http_server_request_duration_seconds_count{job="svcdesk",http_route="/kb/search"}[5m]))
    > 14.4 * (1 - 0.99)
  )
for: 5m
labels:
  service: svcdesk
  slo: availability
  severity: P1
```

Docelowe SLO wymaga uzasadnienia po pomiarze, drugiego alertu o innym tempie zużywania budżetu błędów oraz testów obu reguł.

## Verdict on the draft ladder

Wynik: **refuted**. Pomiar `load 3` z 10 października 2026 dla loginu
`wojbra1993`, po rozgrzewce i 60 sekundach przy 40 żądaniach/s, dał p99
159,2 ms, czyli q = 0,1592 s. Bezpośredni pomiar `kb-index` dał 160,0 ms.
To liczby z zapisanego logu `lab3-load-first.txt`, a nie z profilu practice.

W pierwszej propozycji q wpada do (0,1; 0,25] s. Szerokość wynosi 0,15 s,
a 0,15 / 0,1592 = 0,942211, czyli 94,22% q. Limit to 20%, więc ten przedział
jest za szeroki. Dla 0,95q i 1,05q wynik nadal wpada do tego samego przedziału.

Histogram z pierwszą drabinką oszacował własne p99 na 199,3 ms. Różnica względem
pomiaru klienta to (199,3 - 159,2) / 159,2 = około 25,19%, tuż poza tolerancją
25%. To pokazuje praktyczny koszt szerokiego przedziału. W nowej drabince q jest
w (0,15; 0,16] s, o szerokości 6,28% q. Przedziały po 10 ms obejmują też
zapas wokół wyniku. Zgodność nowej estymacji musi potwierdzić kolejny pomiar.

## The draft alert rule

Pierwsza reguła stosuje dwa okna, więc po ustaniu błędów krótkie okno może
wyłączyć alarm wcześniej niż długie. Zachowany cel dostępności 99% jest
opisany w `slo.md`; w pomiarze 7 z 2400 odpowiedzi było błędnych, około 0,292%.
Krótka próbka uzasadnia punkt startowy, ale nie potwierdza miesięcznej dostępności.

Do końcowej konfiguracji dodano alert o burn rate 6 z oknami 6h i 30m,
obok burn rate 14,4 z oknami 1h i 5m. Oba mają `for: 5m`. Testy sprawdzają
moment zadziałania, próg, brak alarmu przy mniejszym tempie błędów i reset
po wyzdrowieniu usługi. Testy używają jawnie syntetycznych liczników;
nie są pomiarem działania `kb-index`.

## Verdict on the instructor's flawed ladder

Wynik: **refuted**. Drabinka prowadzącego to
`[0.001, 0.0025, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.0175, 0.02, 0.025, 0.03, 0.04, 0.5, 2.5]`.
Ten sam q = 0,1592 s wpada do (0,04; 0,5] s. Szerokość to 0,46 s,
a 0,46 / 0,1592 = 2,889447, czyli 288,94% q. Drabinka ma wiele granic
w pobliżu mediany, lecz nie rozróżnia wolnego trybu odpowiedzi. Mediana 19,3 ms
nie wystarcza do zaprojektowania histogramu, który ma pokazywać p99 159,2 ms.
