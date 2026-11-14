---
lab5_triage:
  image: ghcr.io/wojbra1993/itsm-svcdesk@sha256:93b01b0f17ffb1ba72ef2283dd242190797755122d40878402bc747ff6066c8a
  sarif_receipt: 361
---
<!-- ai-generated: 100% - Codex analysed the actual GitHub Actions reports and drafted this reasoning; the student is responsible for reviewing it. -->
# Triage

Pipeline na main (commit a91e18e, run 43489077415) przeszedł wszystkie siedem zadań. Canary (90217f5, run 43490660116) powstało bez zmiany pipeline: tylko dodane pliki zestawu. Na tej gałęzi deps i secrets zakończyły się failure, a build-test, image, code, ignore-policy i capture zakończyły się success. Raporty pięciu skanerów zostały pobrane bez zmian i zapisane w commicie cc6eab7. Nie łączę canary z main.

## Decyzje dotyczące własnego kodu i obrazu

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| trivy | CVE-2026-76844 | fix | Pierwszy skan obrazu wskazał podatną zlib1g. W Dockerfile przypięto bazę do digestu i dodano apt-get upgrade podczas budowania. Powtórzony gate image przeszedł. |
| trivy | CVE-2026-85091 | fix | Druga podatność tej samej zlib1g została usunięta aktualizacją pakietów systemowych podczas budowania obrazu. Nie dodano wyjątku w .trivyignore. |
| trivy | CVE-2024-47874 | fix | Podniesiono FastAPI do 0.162.7 i Starlette z 0.36.3 do 1.10.0 w requirements.txt. Nowa wersja usuwa zgłoszoną podatność parsowania formularzy; dotychczasowe 55 testów aplikacji nadal przechodzi. |
| trivy | CVE-2026-48818 | fix | Zaktualizowana Starlette 1.10.0 zawiera poprawkę dostępną od 1.1.0. Mimo że aplikacja nie używa StaticFiles, wybrano aktualizację zamiast ignorowania znanego problemu. |
| trivy | CVE-2026-54283 | fix | Aktualizacja Starlette do 1.10.0 usuwa również problem limitów request.form(), poprawiony od 1.3.1. Pin Pydantic podniesiono do 2.14.3, zgodnie z wymaganiami nowego FastAPI. |
| grype | GHSA-6w46-j5rx-g56g-pytest | fix | Raport canary wskazał pytest 8.3.5 we własnym requirements-tests.txt. Po zapisaniu raportu podniesiono pin do 9.1.1; poprawka obsługi katalogów tymczasowych jest dostępna od 9.0.3. Oryginalny SARIF pozostaje niezmieniony. |
| osv-scanner | CVE-2025-71176 | fix | To ta sama podatność pytest wskazana przez OSV-Scanner. Aktualizacja requirements-tests.txt do pytest 9.1.1 usuwa podatną wersję; narzędzie jest używane w kontenerze testowym, nie w obrazie uruchomieniowym svcdesk. |
| semgrep | dockerfile.security.missing-user.missing-user | accept | W głównym Dockerfile naprawiono problem przez USER 10001:10001. W genai/Dockerfile i scripts/lab4-ai/Dockerfile pozostaje root: są to ręcznie uruchamiane pomocniki wcześniejszych laboratoriów, zapisujące wyniki do zamontowanych katalogów, a nie publiczna usługa. Akceptacja tylko do 2026-11-28; przed ponownym użyciem poza ćwiczeniami trzeba dopasować właściciela katalogów i ustawić użytkownika bez uprawnień root. |
| semgrep | python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected | false-positive | scripts/generate_lab2.py bierze base-url z argumentu lokalnego polecenia podanego przez operatora, domyślnie localhost:8080. Nie jest to parametr przyjmowany od klienta API i skrypt nie działa w usłudze. Brakuje więc wskazanej przez regułę ścieżki sterowania URL przez zewnętrznego użytkownika. |

Pliki .trivyignore i .gitleaksignore nie zawierają wyjątków. Główna aplikacja działa jako użytkownik 10001, a pip jest usuwany z gotowego obrazu po instalacji zależności. Pozostałych kontenerów pomocniczych nie traktuję jako zabezpieczonych do wdrożenia produkcyjnego.

## Bake-off

Pomiar obejmuje osiem oznaczonych błędów. Etykiety zostały ujawnione przez bota dopiero po przyjęciu zgłoszenia SARIF 361. Wyniki poniżej pochodzą z bakeoff.py i tych samych pięciu plików SARIF; nie usuwano duplikatów ani fałszywych alarmów z plików wejściowych. Program stosuje zasady dopasowania i deduplikacji P-14–P-22.

| Narzędzie | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Trivy | 3 | 1 | 5 | 0.75 | 0.375 | 0.5 |
| Grype | 2 | 0 | 6 | 1.0 | 0.25 | 0.4 |
| OSV-Scanner | 2 | 0 | 6 | 1.0 | 0.25 | 0.4 |
| gitleaks | 1 | 1 | 7 | 0.5 | 0.125 | 0.2 |
| Semgrep | 2 | 3 | 6 | 0.4 | 0.25 | 0.3077 |

W bramce pozostawiłbym Trivy dla podatności HIGH/CRITICAL oraz gitleaks dla sekretów, ale każde zgłoszenie wymaga sprawdzenia. Trivy ma tutaj najwyższy recall, 0.375, jednak nadal pomija pięć błędów. Wynik zielony nie oznacza więc, że aplikacja jest bezpieczna. Jeden fałszywy alarm Trivy i jeden gitleaks pokazują, że bramka może też zatrzymać poprawną zmianę. Takie sytuacje powinny mieć opisany powód decyzji, a wyjątki nie mogą być bezterminowe ani wyłączać całego skanera.

Grype i OSV-Scanner wykryły te same dwa podatne pakiety, cryptography i requests. Precision 1.0 wynika tutaj z dwóch trafień bez FP, a nie z dowodu niezawodności na innych projektach. Ich recall 0.25 ma jako mianownik wszystkie osiem błędów, również błędy logiki i sekrety spoza głównego zakresu tych narzędzi. Pozostawiłbym je jako dodatkowe raporty i źródło potwierdzenia aktualizacji zależności. Nie sumuję ich TP, bo oba narzędzia znalazły te same defekty.

Semgrep wykrył SQL injection w ticket_search.py oraz sekret CMDB, ale zgłosił też trzy FP. Przy precision 0.4 pozostawiłbym reguły p/default jako raport do przeglądu. Włączenie wszystkich tych reguł jako bezwarunkowej bramki zwiększyłoby liczbę zatrzymanych zmian i pracę potrzebną do sprawdzania alarmów. Własne dwie reguły dotyczą przechwytywania wyjątków w svcdesk; ich testy pokazują oczekiwane dopasowania, ale nie są częścią pomiaru p/default.

Żaden z pięciu skanerów nie dopasował defektów A08 (słaba losowość tokenów), A12 (kontrola dostępu), C04 (sekret JWT) i C05 (sekret poczty). Łącznie narzędzia pokryły zatem cztery z ośmiu defektów. Te pominięcia wymagają przeglądu przepływu danych, modelu uprawnień i sposobu użycia wartości, zamiast polegania wyłącznie na znanych wzorcach i bazach CVE. Dotyczy to również gitleaks: wykrycie jednego sekretu nie dowodzi, że reszta konfiguracji jest czysta.

To niewielki, sztucznie przygotowany zestaw. Wynik recall traktuję jako wskazówkę i optymistyczne przybliżenie, nie prognozę skuteczności w produkcji. Wstrzyknięte błędy często są łatwiejsze do znalezienia niż rzeczywiste problemy. Dobór loginu ustala próbkę, więc ranking z tego zestawu nie uzasadnia ogólnego twierdzenia, że jeden skaner jest zawsze lepszy od pozostałych.
