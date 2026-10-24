<!-- ai-generated: 100% - Codex compared the complete recorded investigation and both actual local runs against PromQL measurements on lab4-rec-3. -->
# Porównanie dwóch badaczy tego samego incydentu

Pierwszy badacz to kursowa pętla agent.py z qwen3:4b-instruct, zapisana przez prowadzącego w lab4-rec-3. Drugi to ta sama pętla z lokalnym qwen3:1.7b. Zastosowano serwer prom_mcp.py z mcp 2.2.0. Oba modele analizowały checkout w nagraniu z 12 października 2026. Nie dostały moich wniosków o flagach. Rozmiar modelu, prompty i liczba kroków różnią się, więc nie traktuję tego jako kontrolowanego benchmarku modeli.

Lokalny model uruchomiono dwa razy. Pierwsza odpowiedź zawierała tylko dwie zbiorcze hipotezy. Drugi przebieg doprecyzował format argumentów narzędzi, historyczną datę, agregowanie histogramów i wymóg co najmniej trzech osobnych zdań. Kod tej zmiany jest w scripts/lab4-ai/Dockerfile. Nie podano rozwiązania incydentu. Oba przebiegi zachowano w transcript.md i transcript.jsonl; ocena obejmuje wszystkie siedem zdań, nie tylko drugą odpowiedź. Wyniki poniżej odtwarzają predykcje o 07:11:00Z i baseline o 07:00:45Z.

| Wpis | Ocena | Co rozstrzyga |
|---|---|---|
| H1, badacz 1 | partially_correct | Checkout rzeczywiście zawiódł, lecz licznik nie wynosił 2 przez cały podany przedział. O 07:07:17.778Z miał 0; o 07:08:17.779Z miał 2. |
| H2, badacz 1 | correct | GetProduct w katalogu ma 0.148950 błędu/s. Błędy CLIENT GetProduct w checkout pokrywają się tempem z błędami SERVER PlaceOrder. |
| H3, badacz 1 | hallucinated | Payment obsługuje 0.125 wywołania/s bez serii błędów. Model użył typowej przyczyny jako domysłu, bez potwierdzenia dla tego incydentu. |
| H4, badacz 1 | partially_correct | Błędy checkout występują, lecz ruch frontend wynosi 0.949908 poziomu baseline. Licznik checkout nie rośnie stale; ogólna sugestia zasobowa pozostaje nieustalona. |
| S1, badacz 2, przebieg 1 | partially_correct | Checkout ma błędy, ale cztery wskazane usługi obsługują łącznie 8.252086 żądania/s. Brak ruchu jest błędną przesłanką. |
| S2, badacz 2, przebieg 1 | hallucinated | Twierdzenie o zerowym calls_total i braku danych histogramu przeczące dodatniemu ruchowi nie może uzasadniać wskazanej przyczyny. |
| S3, badacz 2, przebieg 2 | correct | Histogram checkout zawiera 2 błędne wywołania, nieobecne na baseline. Potwierdza to obecność błędów; nie potwierdza niepodanego przez model progu słowa high. |
| S4, badacz 2, przebieg 2 | hallucinated | Frontend-proxy zwolnił, ale p99 katalogu pozostaje poniżej 10 ms. Opis obu usług jako mających częste długie odpowiedzi nie jest trafny. |
| S5, badacz 2, przebieg 2 | partially_correct | Błędy katalogu są rzeczywiste, ale kolejka eksportera metryk ma 1/1000 pojemności, tyle samo co na baseline. Nowego zalegania jako przyczyny nie wykazano. |
| S6, badacz 2, przebieg 2 | hallucinated | Histogram checkout ma tyle samo błędów w le=100 i +Inf: 2. Nie ma błędów powyżej 100 ms, a granica 300 ms nie istnieje. |
| S7, badacz 2, przebieg 2 | hallucinated | Liczniki błędów katalogu le=50 i le=100 wynoszą po 38. Różnica dla (50,100] ms jest zerowa. |

Pierwszy badacz wykroczył poza nazwy alertów: zapytał o błędy checkout i znalazł wywołanie katalogu. Nadal źle odczytał czas i dopisał niepotwierdzoną awarię płatności. Drugi polegał głównie na nazwach alertów. Żądał pełnych histogramów bez agregacji, co zwróciło wiele serii i obcięty zapis wyniku. Popełnił też błędy formatowania argumentów oraz wykonał zapytanie dla 2023 roku. Pusty wynik poza datą nagrania nie oznacza braku ruchu w czasie awarii.

W obu lokalnych przebiegach narzędzia miały wyłącznie dostęp do odczytu. Zła diagnoza nie zmieniła usługi. Żaden badacz nie przedstawił wystarczającej analizy czasu GC ad ani nie ustalił wiarygodnie pełnego zestawu trzech flag. Własna ocena wymagała dodatkowych zapytań, zwłaszcza porównania z baseline i różnic między kumulacyjnymi bucketami. Większa liczba hipotez po doprecyzowaniu promptu poprawiła możliwość ich oceny, ale nie zapewniła poprawności.

Nie należy porównywać modeli jedynie liczbą wpisów correct: pierwszy ma cztery hipotezy, a drugi siedem z dwóch przebiegów, o różnej szczegółowości. Oba zbiory pokazują tę samą zasadę praktyczną: zapisane twierdzenie staje się podstawą decyzji dopiero po sprawdzeniu konkretnej predykcji w odpowiednim czasie.
