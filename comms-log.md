---
lab4_comms:
  awareness: 2026-10-12T07:10:07Z
  detection: 2026-10-12T07:09:19Z
  classification: 2026-10-12T07:20:00Z
  nis2:
    early_warning_due: 2026-10-13T07:10:07Z
    notification_due: 2026-10-15T07:10:07Z
    notification_sent: 2026-10-13T09:00:00Z
    final_report_due: 2026-11-13T09:00:00Z
  ksc:
    early_warning_due: 2026-10-13T07:09:19Z
    notification_due: 2026-10-15T07:09:19Z
    notification_sent: 2026-10-13T09:00:00Z
    final_report_due: 2026-11-13T09:00:00Z
  dora:
    initial_due: 2026-10-12T11:20:00Z
    initial_sent: 2026-10-12T08:00:00Z
    intermediate_due: 2026-10-15T08:00:00Z
    intermediate_sent: 2026-10-14T08:00:00Z
    final_due: 2026-11-14T08:00:00Z
  log:
    - {at: 2026-10-12T07:10:07Z, to: kierownik incydentu, what: "Plan ćwiczenia: potwierdzenie wpływu na checkout i rozpoczęcie oceny istotności."}
    - {at: 2026-10-12T07:20:00Z, to: zespół zgodności, what: "Plan ćwiczenia: klasyfikacja major w scenariuszu DORA i potwierdzenie terminów."}
    - {at: 2026-10-12T08:00:00Z, to: właściwy organ nadzoru finansowego, what: "Plan ćwiczenia: wstępne zgłoszenie DORA, wpływ i dostępne czasy incydentu."}
    - {at: 2026-10-12T08:10:00Z, to: właściwy CSIRT, what: "Plan ćwiczenia: wczesne ostrzeżenie NIS2 i KSC; przyczyny pozostają hipotezami do weryfikacji."}
    - {at: 2026-10-13T09:00:00Z, to: właściwy CSIRT, what: "Plan ćwiczenia: zgłoszenia NIS2 i KSC z analizą metryk oraz ograniczeniami ustaleń."}
    - {at: 2026-10-14T08:00:00Z, to: właściwy organ nadzoru finansowego, what: "Plan ćwiczenia: raport pośredni DORA z wynikami analizy i działaniami naprawczymi."}
---
<!-- ai-generated: 100% - Codex calculated the exercise deadlines under INCIDENT-SPEC I-30 and explicitly separated hypothetical communications from recorded evidence. -->

# Plan komunikacji w ćwiczeniu

To scenariusz laboratoryjny według I-30, przy założeniu narzuconym przez zadanie, że podmiot podlega wszystkim trzem reżimom, a incydent jest istotny/poważny w ich rozumieniu. Żadnych zgłoszeń do organów nie wysłano. Pola *_sent oznaczają planowane chwile wysłania w symulacji. Nie są dowodem komunikacji odbytej w nagraniu ani oceną rzeczywistych obowiązków prawnych sklepu.

## Uzasadnienie trzech chwil

Detection to 07:09:19Z 12 października: początek alarmu ShopCheckoutErrors podany przez checker. Awareness przyjmuję jako 07:10:07Z, kiedy dyżurny potwierdził P1. To jawne założenie scenariusza, że w tym momencie rozpoznał istotny wpływ na zamówienia; samo API ack nie dowodzi rzeczywistej prawnej oceny istotności.

Classification przyjmuję jako 07:20:00Z, po dodatkowej ocenie wpływu przez zespół incydentu. Tego zdarzenia nie ma w nagraniu. Jest to zaplanowany krok ćwiczenia, oddzielony od automatycznego wykrycia i potwierdzenia zgłoszenia. W tym scenariuszu klasyfikacja następuje w ciągu 24 godzin od awareness.

## Obliczenia

- NIS2: do awareness dodaję 24 godziny na wczesne ostrzeżenie i 72 godziny na zgłoszenie. Raport końcowy wypada miesiąc kalendarzowy po planowanym zgłoszeniu z 13 października o 09:00Z, czyli 13 listopada o 09:00Z.
- KSC: analogiczne okresy liczę od detection. Terminy są 48 sekund wcześniejsze niż w NIS2. Planowane zgłoszenie jest o tej samej godzinie, więc termin końcowy obu raportów jest wspólny.
- DORA: wcześniejsza z chwil classification + 4 h (12 października 11:20Z) i awareness + 24 h (13 października 07:10:07Z) to 12 października 11:20Z. Wstępne zgłoszenie zaplanowano na 08:00Z tego dnia. Termin raportu pośredniego wynosi 15 października 08:00Z, 72 godziny później; sam raport planuję dzień wcześniej. Raport końcowy przypada 14 listopada 08:00Z, miesiąc po planowanym raporcie pośrednim.

Wszystkie obliczenia stosują UTC i zasady uproszczone w I-30, bez weekendowego przesunięcia. Miesiąc kalendarzowy nie jest stałym okresem 30 dni. Terminy listopadowe zachowują godzinę UTC mimo zmiany czasu w Warszawie.

## Przebieg planowanej komunikacji

Najpierw dyżurny informuje kierownika incydentu o wpływie na checkout. Zespół zgodności potwierdza przyjętą w ćwiczeniu klasyfikację i właściwe zegary. Wstępne informacje do nadzoru i CSIRT opisują znane objawy oraz czasy; nie przedstawiają niepotwierdzonej hipotezy AI jako ustalonej przyczyny. Kolejne zgłoszenie uzupełnia wyniki PromQL i granice analizy, w tym różnicę między ustaniem alarmu a wyłączeniem wszystkich flag. Raport pośredni zawiera działania LAB4-01–LAB4-04. Wszystkie planowane wysyłki mieszczą się przed odpowiednimi terminami z front matter.
