---
lab3_first_draft:
  source: ai
  tool: "Codex, 10 October 2026"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]
  verdict: null
  evidence:
    p99_seconds: null
    bucket: null
    relative_width: null
lab3_flawed_ladder:
  verdict: null
  evidence:
    p99_seconds: null
    bucket: null
    relative_width: null
---
<!-- ai-generated: 100% - Codex recorded the initial proposal; measured evidence and verdicts are not yet available. -->

# Pierwsza propozycja przed pomiarem

Stan roboczy: poniżej zapisano rzeczywistą prośbę użytkownika i pierwszą
propozycję asystenta z tej rozmowy, przed pomiarem profilu `wojbra1993`.
Prośbie towarzyszyły paczka zadania Lab 3, dokument z Moodle i wynik `docker version`.
Pola `null` oznaczają brak pomiaru, a nie wynik zerowy. Ten dokument nie jest
jeszcze gotowy do oddania. Po zapisaniu tej wersji w Git i wykonaniu `load 3`
należy uzupełnić dowody i uzasadnienia, zachowując treść promptu i odpowiedzi.

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

Oczekuje na pierwszy rzeczywisty pomiar `load 3`. Wpisz q, przedział (lo, hi]
i obliczenie (hi - lo) / q. Brakujących wartości nie zastępuj profilem practice.

## The draft alert rule

Reguła powyżej jest zapisem pierwszej propozycji, a nie końcową konfiguracją.
Po pomiarze trzeba uzasadnić cel dostępności i przygotować dwie reguły z testami
momentu zadziałania, progu oraz wyłączenia alarmu.

## Verdict on the instructor's flawed ladder

Oczekuje na ten sam pomiar q. Drabinka prowadzącego to
`[0.001, 0.0025, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.0175, 0.02, 0.025, 0.03, 0.04, 0.5, 2.5]`.
Uzasadnienie będzie zawierało przedział obejmujący q oraz (hi - lo) / q.
