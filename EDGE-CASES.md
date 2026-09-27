---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 100% - Codex drafted this explanation after checking the fixture and API outputs. -->

# Przypadki szczególne w danych ćwiczeniowych

## E1 - ujemny czas wskutek rozbieżności zegarów

- What the log contains: Trzy commity, `sha-0040`, `sha-0094` i `sha-0123`, mają czas późniejszy niż pierwsze udane wdrożenie produkcyjne, które je zawiera. API zgłasza trzy ujemne pary czasu dostarczenia.
- What a default definition would have done: Zwykłe odejmowanie mogłoby włączyć ujemne czasy do mediany i sugerować wyjątkowo szybkie dostarczanie. Odrzucanie tych par ukryłoby z kolei wadę danych przed osobą oceniającą proces.
- Why the rule is defensible: R-08 zachowuje każdą parę, ogranicza jej czas do zera i osobno liczy anomalię. Zero nie dowodzi natychmiastowej pracy: pozwala uniknąć niemożliwego czasu, a licznik sygnalizuje właścicielowi pomiaru potrzebę sprawdzenia synchronizacji zegarów.

## E2 - cofnięcie cofnięcia

- What the log contains: `sha-0070` cofa `sha-0069`, a `sha-0071` cofa `sha-0070`. Dwa commity z polem `reverts` dziedziczą tożsamość pierwotnej zmiany; licznik `revert_chains_collapsed` wynosi dwa.
- What a default definition would have done: Liczenie każdego commita jako osobnej zmiany podniosłoby liczbę wykonanych zadań, mimo że zespół zajmował się jedną zmianą i jej cofnięciami. Raport mógłby nagradzać naprawianie własnej pracy jako dodatkową wartość dla klienta.
- Why the rule is defensible: R-06 śledzi `reverts` przechodnio do pierwotnego `change_id`. Commity nadal istnieją i mogą wpływać na metrykę czasu per commit, ale nie tworzą nowych jednostek dostarczonej pracy. Pozwala to oddzielić aktywność techniczną od liczby zmian biznesowych.

## E3 - poprawki poza gałęzią main

- What the log contains: `sha-0019`, `sha-0077`, `sha-0108` i `sha-0127` występują we wdrożeniach produkcyjnych w badanym oknie, chociaż ich gałąź jest inna niż `main`. Są to cztery różne identyfikatory commitów.
- What a default definition would have done: Filtr `branch == "main"` pominąłby część rzeczywistych prób dostarczenia poprawek. Zespół obsługujący awarię przez gałąź hotfix wyglądałby na mniej aktywny, a odbiorca raportu nie widziałby pełnego procesu produkcyjnego.
- Why the rule is defensible: R-09 wiąże pomiar z wdrożeniem produkcyjnym, a nie nazwą gałęzi. Licznik anomalii obejmuje udane i nieudane wdrożenia, natomiast pary lead time powstają wyłącznie dla udanych. Dzięki temu widoczność pracy nie wymaga uznania nieudanej próby za dostarczenie.

## E4 - wdrożenia bez powiązanych commitów

- What the log contains: `DEP-0026`, `DEP-0032`, `DEP-0043` i `DEP-0044` są wdrożeniami produkcyjnymi w oknie, ale mają pustą listę `commits`. API zgłasza cztery takie zdarzenia.
- What a default definition would have done: Odrzucenie pustych list zmniejszyłoby częstotliwość wdrożeń oraz mianowniki wskaźników awarii i poprawek. Próba liczenia czasu bez commita mogłaby natomiast skończyć się wymyślonym zerem albo błędem obliczeń.
- Why the rule is defensible: R-10 traktuje wdrożenie jako zdarzenie operacyjne także wtedy, gdy nie ma powiązanego kodu. Takie zdarzenie może generować pracę lub ryzyko, więc pozostaje w licznikach wdrożeń. Nie ma jednak podstaw do utworzenia pary czasu dostarczenia; licznik pustych wdrożeń pomaga wyjaśnić rozbieżność między aktywnością a dostarczoną wartością.

## E5 - awaria bez potwierdzonego przywrócenia

- What the log contains: Nieudane wdrożenie `DEP-0015` jest objęte incydentem `INC-0004`, dla którego nie zapisano rozwiązania. Z ośmiu nieudanych wdrożeń siedem ma zmierzony czas przywrócenia, a jedno pozostaje otwarte.
- What a default definition would have done: Zamknięcie awarii na końcu okna dopisałoby zdarzenie, którego nie było. Całkowite usunięcie jej z analizy obniżyłoby natomiast liczbę awarii i dało osobie odpowiedzialnej za usługę zbyt optymistyczny obraz niezawodności.
- Why the rule is defensible: R-12 wyklucza brakujący czas wyłącznie z mediany przywrócenia i zachowuje awarię w `open_failures` oraz wskaźniku nieudanych wdrożeń. Mediana siedmiu zamkniętych przypadków nie opisuje całego ryzyka: właściciel usługi powinien czytać ją razem z liczbą nadal otwartych awarii.

## E6 - nakładające się incydenty

- What the log contains: Przedziały incydentów tworzą jedenaście nieuporządkowanych par z niepustym przecięciem według R-13. Dla incydentu otwartego do porównania przedziałów służy koniec okna, bez uznawania tego za rzeczywiste rozwiązanie.
- What a default definition would have done: Sumowanie czasów równoczesnych incydentów policzyłoby ten sam czas wielokrotnie. Scalenie ich w jedną awarię zgubiłoby natomiast związek między konkretnym nieudanym wdrożeniem a jego przywróceniem i zniekształciło ocenę procesu naprawczego.
- Why the rule is defensible: R-12 i R-13 mierzą przywrócenie osobno dla każdego nieudanego wdrożenia, z najwcześniej otwartym obejmującym je incydentem; remis rozstrzyga identyfikator incydentu. Wspólne rozwiązanie może zamknąć kilka wdrożeń, lecz nie wymaga sumowania czasu ich incydentów. Przedziały tylko stykające się końcami nie są liczone jako nakładające.

## Gaming demonstration

Wybrana metryka to `deployment_frequency_per_day`, a wykorzystana reguła to R-11: liczy ona wszystkie wdrożenia produkcyjne w oknie. R-10 dopuszcza w tym liczniku także wdrożenia bez commitów. W przykładzie osiem ostatnich udanych wdrożeń zawierających kod (`DEP-0030`, `DEP-0031`, `DEP-0033`, `DEP-0037`, `DEP-0039`, `DEP-0040`, `DEP-0041`, `DEP-0042`) przesunięto na 22 września o 12:00 UTC, poza badane okno. Dodano dwadzieścia udanych wdrożeń bez commitów 21 września.

Liczba wdrożeń w oknie rośnie z 42 do 54. Częstotliwość rośnie z 2 do 2,571429 dziennie, czyli o około 28,57%, ponad wymagane 25%. Jednocześnie liczba dostarczonych pierwotnych zmian spada z 65 do 50, czyli o około 23,08%, więcej niż wymagane 10%. Nie dodano żadnych commitów, więc filtrowanie do pierwotnej pracy w R-21 pozostawia ten sam wynik. Mediana rzeczywistego czasu zmian wzrasta z 539452 do 555237 sekund; próg pogorszenia w tym przykładzie spełnia liczba dostarczonych zmian, nie wzrost mediany o 25%.

Zachowano wszystkie bazowe commity i incydenty bez zmian. Wdrożenia bazowe zachowują identyfikatory, środowiska i wyniki; osiem przesunięto wyłącznie później. Pliki `metrics.json` oraz `gaming.json` zawierają odpowiedzi tego samego endpointu dla danych przed i po przekształceniu.

W rzeczywistym zespole taki bodziec mogłaby stworzyć premia za liczbę wdrożeń. Osoba zarządzająca zespołem oraz osoby wykonujące częste operacje dostałyby lepszy wynik na dashboardzie, mimo że klient czekałby na piętnaście zmian, które wcześniej mieściły się w oknie. Dodatkowe operacje bez kodu mogą mieć uzasadnienie, ale sama ich liczba nie dowodzi większej wartości. Dlatego częstotliwość trzeba czytać razem z dostarczonymi zmianami i ich czasem, zamiast nagradzać ją jako samodzielny cel.
