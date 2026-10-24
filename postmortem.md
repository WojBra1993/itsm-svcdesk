---
lab4_postmortem:
  ticket: "1224ad8d-06a8-4ae3-865a-da2015a4ddb5"
  detecting_alert: ShopCheckoutErrors
  onset: 2026-10-12T07:05:45Z
  detection: 2026-10-12T07:09:19Z
  acknowledgement: 2026-10-12T07:10:07Z
  recovery: 2026-10-12T07:12:19Z
  mttd_seconds: 214
  mtta_seconds: 48
  mttr_seconds: 394
  identified_flags: [productCatalogFailure, adManualGc]
---
<!-- ai-generated: 100% - Codex drafted this analysis from the assigned recording, measured PromQL results and the official incident command; the student reviews the conclusions. -->

# Postmortem: błędy zamówień i wolniejsze reklamy w sklepie demonstracyjnym

## Date

Incydent pochodzi z nagrania lab4-rec-3 z 12 października 2026. Analizę przygotowano 24 października 2026. Wszystkie godziny w raporcie są w UTC.

## Authors

WojBra1993, w roli analityka przypisanego nagrania. Szkic i zapytania przygotowano z pomocą Codex. Dyżur, zgłoszenie i przywracanie usługi widoczne w nagraniu wykonał prowadzący; nie przedstawiam ich jako własnych działań na żywym środowisku.

## Status

Analiza nagrania jest przygotowana do przeglądu. Alarm wykrywający incydent ustąpił, ale to nie oznaczało jeszcze końca wszystkich objawów. Oryginalne zgłoszenie pozostaje w stanie acknowledged; nie zmieniono jego treści ani stanu. Proponowane działania problemowe pozostają otwarte.

## Summary

Po rozpoczęciu awarii o 07:05:45 część odczytów katalogu produktów zawodziła, a błędy dotarły do składania zamówień. Jednocześnie wzrosło opóźnienie usługi reklamowej. Alarm ShopCheckoutErrors zaczął firing o 07:09:19 i zakończył ten przebieg o 07:12:19: laboratoryjny MTTR wynosi 394 s. Ostatnia aktywna flaga przestała być sygnalizowana dopiero o 07:13:20.768, około 61 s po zakończeniu alarmu. Dlatego MTTR tego alarmu nie jest pomiarem pełnego odzyskania całego sklepu.

## Impact

To ruch generatora w sklepie demonstracyjnym, bez danych o rzeczywistych klientach i stratach finansowych. Stan liczników na końcu zapisu o 07:14:45 wskazuje 2 błędne wywołania SERVER PlaceOrder w checkout i 38 błędnych wywołań SERVER GetProduct w product-catalog. Licznik błędów checkout ma próbkę 0 o 07:07:17.778 i 2 o 07:08:17.779, po czym pozostaje na 2. Licznika nie wolno traktować jako kolejnych dwóch błędów w każdej minucie.

O 07:11:00 pięciominutowe tempo błędów checkout wynosi 0.0082304/s przy 0.1332304/s wszystkich wywołań, czyli około 6.18%. Dla katalogu wartości wynoszą 0.148950/s i 1.953117/s, około 7.63%. Są to estymaty rate() w oknie, nie dokładna liczba użytkowników. Na baseline o 07:00:45 obie usługi mają ruch, bez serii błędów SERVER.

P99 usługi ad wzrosło z 5.04 ms na baseline do 796 ms o 07:11:00. Jest to estymacja z histogramu, nie dokładna długość pojedynczego żądania. Ruch frontend nie wzrósł: 4.258316/s na baseline i 4.045009/s podczas awarii. Zapytania Q1–Q4 poniżej pozwalają odtworzyć te liczby.

## Root Causes

Z objawów i tabeli puli flag w INCIDENT-SPEC.md wnioskuję o dwóch flagach:

- productCatalogFailure: GetProduct ma 38 błędów, a checkout pokazuje błędy wywołań CLIENT GetProduct i SERVER PlaceOrder o jednakowym tempie 0.0082304/s o 07:11:00. Katalog nie wykazuje przy tym dużego wzrostu p99: 7.83 ms wobec 9.18 ms na baseline. Pasuje to do błędów katalogu, a nie blokady odczytów na 30 s.
- adManualGc: p99 ad rośnie do 796 ms, a przyrost czasu G1 Old Generation GC w pięciominutowym oknie wynosi 34.5703 s. To mocniejszy argument niż sama obecność wolniejszych stron. W puli laboratoryjnej taki wzorzec odpowiada wymuszaniu GC w ad.

Nie odczytano zaszyfrowanego ground truth. Trzeciej flagi z klasy zasobów nie wskazuję bez wystarczających danych: krótkie nagranie i niewielkie różnice pamięci email/recommendation nie rozstrzygają jej wiarygodnie. To ograniczenie analizy, a nie dowód braku trzeciej awarii. Ostateczne porównanie identyfikacji z faktycznie wylosowanymi flagami wykonuje Tier B.

## Trigger

Uruchomienie wylosowanej kombinacji flag jest widoczne jako pierwsza próbka seeded_fault_active o 07:05:45.768; checker zapisuje tę chwilę jako 07:05:45Z. To znacznik początku używany do wyliczenia czasu, nie źródło alertu. Mechanizmy awarii były obecne w aplikacji wcześniej, a aktywacja flag je uruchomiła. Pierwsza próbka uruchomionego injectora jest o 06:53:15.768, ponad 12 minut przed onset.

## Resolution

W nagraniu ustają błędy checkout i katalogu, a ShopCheckoutErrors kończy swój pierwszy firing run o 07:12:19. seeded_fault_active ma pierwszą próbkę 0 o 07:13:20.768. Zgodnie z kontraktem injectora oznacza to, że żadna wylosowana flaga nie była już aktywna. Nastąpiło to dużo wcześniej niż automatyczne 45-minutowe wyłączenie.

Metryki nie zapisują osobnych poleceń wyłączenia każdej flagi. Nie przypisuję więc dyżurnemu zmyślonej kolejności ani dokładnych czasów poszczególnych zmian. Jako procedurę naprawczą proponuję wyłączenie potwierdzonych flag i sprawdzenie zarówno błędów zamówień, jak i opóźnień zależności. Końcowy pięciominutowy p99 ad nadal wynosi 794.75 ms; to okno zawiera wcześniejsze wolne wywołania i samo nie dowodzi dalszego działania flagi.

## Detection

Oficjalne `.\itsmlab.ps1 incident 4` wskazało ShopCheckoutErrors: wykrycie po 214 s od onset, potwierdzenie przez dyżurnego 48 s później. Zgłoszenie P1 utworzono o 07:09:37 i potwierdzono o 07:10:07. Bez alertu błędy byłyby widoczne w odczytach katalogu, zamówieniach i metrykach; w rzeczywistym sklepie mogłyby też prowadzić do zgłoszeń klientów.

Alarm i potwierdzenie w tym pomiarze pochodzą od prowadzącego. Nowe pliki prometheus/demo-alerts.yml oraz alertmanager/ dotyczą projektu studenta i nie działały w przeszłym nagraniu. Nowe reguły obserwują tylko SERVER spans w oknach 5 min: błędy checkout powyżej 5% i p99 powyżej 2000 ms kierują P1 do pagera; ostrzeżenie powyżej 1% trafia jako P2 na czat. Inhibicja wycisza mniej pilny alarm tylko dla tej samej, niepustej wartości service. P1 innej usługi nie może wyciszyć ostrzeżenia checkout.

## Action Items

Poniższe identyfikatory oznaczają planowane zadania w tym raporcie; nie są deklaracją utworzenia zewnętrznych zgłoszeń.

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Dodać regresję GetProduct z aktywną flagą awarii i sprawdzić zachowanie PlaceOrder przy błędzie katalogu. | prevent | WojBra1993, rola właściciela katalogu | LAB4-01 |
| Usunąć wymuszanie pełnego GC ze ścieżki obsługi reklam i dodać test opóźnienia tej zależności. | prevent | WojBra1993, rola właściciela ad | LAB4-02 |
| Dopisać do runbooka sprawdzenie błędów i opóźnień wszystkich dotkniętych usług przed uznaniem incydentu za zakończony. | process | WojBra1993, rola dyżurnego SRE | LAB4-03 |
| Wymagać historycznej daty zapytań i porównania z baseline przed przyjęciem hipotezy AI. | process | WojBra1993, rola opiekuna narzędzi AI | LAB4-04 |

## Lessons Learned

### What went well

Zachowany snapshot i zgłoszenie pozwalają odtworzyć zegary bez polegania na pamięci dyżurnego. Zestawienie błędów SERVER katalogu z błędami CLIENT w checkout wspiera ścieżkę propagacji. Testy routingu obejmują również istniejące alerty svcdesk z Lab 3.

### What went wrong

Wykrycie trwało 3 min 34 s. Zanik alarmu checkout wyprzedził wyłączenie wszystkich flag, więc sam status tego alarmu był zbyt wąskim kryterium pełnego powrotu sklepu. Pierwszy model mylił licznik z tempem zdarzeń, a drugi błędnie argumentował brakiem ruchu i odczytami histogramu. Ich twierdzenia wymagają osobnej weryfikacji.

### Where we got lucky

Nagranie zachowało zdrowy okres odniesienia i koniec wykrywającego alarmu. Dzięki temu można odróżnić nowe objawy od stałego zachowania systemu. Hipoteza AI o awarii płatności nie została wykonana jako zmiana w środowisku: badanie odbywało się po incydencie na danych tylko do odczytu.

## Timeline

Wszystkie zdarzenia niżej dotyczą 12 października 2026, UTC. Czasy podane z milisekundami pochodzą z surowych próbek; cztery wymagane zegary są przepisane z checkera.

| Czas UTC | Obserwacja |
|---|---|
| 07:04:45 | Ostatnia minuta przed onset; w poprzedzającym go dziesięciominutowym baseline brak firing P1. |
| 07:05:45 | Onset: pierwsza próbka aktywnej awarii; surowo 07:05:45.768. |
| 07:08:17.779 | Pierwsza próbka licznika checkout z wartością 2; poprzednia miała 0. |
| 07:09:19 | Detection: ShopCheckoutErrors zaczyna firing, MTTD 214 s. |
| 07:09:37 | Utworzono zgłoszenie P1 1224ad8d-06a8-4ae3-865a-da2015a4ddb5. |
| 07:10:07 | Acknowledgement: potwierdzenie zgłoszenia, MTTA 48 s. |
| 07:11:00 | Punkt porównania zapytań: katalog 0.148950 błędu/s, ad p99 796 ms. To pomiar wykonany retrospektywnie, nie zapis działania dyżurnego. |
| 07:12:19 | Recovery wykrywającego alarmu; MTTR 394 s, ale nie wszystkie flagi jeszcze wyłączone. |
| 07:13:20.768 | Pierwsza próbka seeded_fault_active równa 0. |
| 07:14:45 | Końcowy punkt odczytów: liczniki błędów checkout 2 i katalogu 38; ich pięciominutowe rate wynosi już 0. |

Hipotezy AI oceniano po zdarzeniu. Nie dopisuję fikcyjnych działań dyżurnego na ich podstawie. Dowody i wyniki znajdują się w ai-rca-eval.json oraz ai-rca-eval-2.json.

## Supporting information

Źródła: niezmienione incident/tsdb-snapshot.tar.gz i incident/ticket.json z przypisanego lab4-rec-3; oba transkrypty w ai-rca/; wyniki `.\itsmlab.ps1 recording 4` oraz `.\itsmlab.ps1 incident 4` podane podczas wykonania zadania. Run: fe6ecd21acce7a08. Do zapytań użyto Prometheus 3.15.0 z kopią archiwum, retencją 100 lat i wyłączonym scrape.

Q1, dokładny odczyt zapisanych liczników błędów o 07:14:45Z:

```promql
sum by (service_name, span_name) (traces_span_metrics_calls_total{service_name=~"checkout|product-catalog",span_kind="SPAN_KIND_SERVER",status_code="STATUS_CODE_ERROR"})
```

Q2, tempo błędów i wszystkich żądań: uruchomić obie wersje o 07:00:45Z i 07:11:00Z, podzielić błędy przez wszystkie dla tej samej usługi:

```promql
sum by (service_name) (rate(traces_span_metrics_calls_total{service_name=~"checkout|product-catalog|frontend",span_kind="SPAN_KIND_SERVER",status_code="STATUS_CODE_ERROR"}[5m]))
sum by (service_name) (rate(traces_span_metrics_calls_total{service_name=~"checkout|product-catalog|frontend",span_kind="SPAN_KIND_SERVER"}[5m]))
```

Q3, opóźnienia w milisekundach, te same dwa punkty:

```promql
histogram_quantile(0.99, sum by (service_name, le) (rate(traces_span_metrics_duration_milliseconds_bucket{service_name=~"ad|checkout|product-catalog",span_kind="SPAN_KIND_SERVER"}[5m])))
```

Q4, czas pełnego GC ad w sekundach, o 07:11:00Z:

```promql
sum(increase(jvm_gc_duration_seconds_sum{service_name="ad",jvm_gc_name="G1 Old Generation"}[5m]))
```

Odczyty AI zweryfikowano osobno na baseline o 07:00:45Z. Zaszyfrowana odpowiedź injectora nie była źródłem wniosków. Podane wyżej godziny zapytań wymagają daty 2026-10-12; zapytanie z domyślnym „teraz” nie odtwarza incydentu.

## Problem record

Incident record: 1224ad8d-06a8-4ae3-865a-da2015a4ddb5 — niezmienione zgłoszenie P1 z nagrania.
Root cause: Wnioski z metryk wskazują błędy GetProduct propagowane do checkout oraz wymuszony pełny GC zwiększający opóźnienia ad; trzeciej flagi nie ustalono wiarygodnie.
Known error: Aktywacja wadliwej ścieżki katalogu może przerwać zamówienia, a ścieżka GC reklam pogarsza czas odpowiedzi; alarm zamówień nie obejmuje pełnego odzyskania wszystkich zależności.
Workaround: Wyłączyć potwierdzone flagi awarii, sprawdzić błędy i opóźnienia zależności oraz obserwować całe okno po zmianie; problem pozostaje otwarty do wdrożenia działań LAB4-01–LAB4-04.
