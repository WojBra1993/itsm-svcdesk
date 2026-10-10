---
lab3_genai_diff:
  instrumentation: "opentelemetry-instrumentation-genai-openai==1.2b0; opentelemetry-sdk==1.45.0; openai==3.19.2; opentelemetry-exporter-otlp-json-file==0.66b0"
  spec_ref: "semantic-conventions-genai@e57c543b4889619eb2a05702471937db5119165d"
  attributes:
    - {"name": "gen_ai.embeddings.dimension.count", "emitted": false, "in_spec": true, "stability": "development"}
    - {"name": "gen_ai.operation.name", "emitted": true, "in_spec": true, "stability": "development"}
    - {"name": "gen_ai.provider.name", "emitted": true, "in_spec": true, "stability": "development"}
    - {"name": "gen_ai.request.max_tokens", "emitted": true, "in_spec": true, "stability": "development"}
    - {"name": "gen_ai.request.model", "emitted": true, "in_spec": true, "stability": "development"}
    - {"name": "gen_ai.request.temperature", "emitted": true, "in_spec": true, "stability": "development"}
    - {"name": "gen_ai.response.finish_reasons", "emitted": true, "in_spec": true, "stability": "development"}
    - {"name": "gen_ai.response.id", "emitted": true, "in_spec": true, "stability": "development"}
    - {"name": "gen_ai.response.model", "emitted": true, "in_spec": true, "stability": "development"}
    - {"name": "gen_ai.tool.name", "emitted": false, "in_spec": true, "stability": "development"}
    - {"name": "gen_ai.usage.input_tokens", "emitted": true, "in_spec": true, "stability": "development"}
    - {"name": "gen_ai.usage.output_tokens", "emitted": true, "in_spec": true, "stability": "development"}
---
<!-- ai-generated: 100% - Codex wrote the comparison; names and values come from the actual local LLM trace. -->

# Ślad lokalnego modelu a specyfikacja GenAI

Pomiar UTC: 2026-10-10T19:07:42.261452+00:00. Jedno rzeczywiste, niestreamowane wywołanie Chat Completions przez SDK OpenAI do lokalnego serwera Ollama w Dockerze. Model żądany: `qwen2.5:0.5b`; model wskazany przez odpowiedź: `qwen2.5:0.5b`. SDK nie ponawia żądania.

Prompt: Explain in one short sentence what an error budget is.

Plik spans.json jest bezpośrednim eksportem FileSpanExporter. Skrypt nie dopisuje atrybutów do spanów ani nie zamienia ich wartości. Treść promptu i odpowiedzi nie jest rejestrowana przez instrumentację; powyżej podaję prompt użyty przez skrypt.

Wszystkie wyemitowane klucze gen_ai.* występują w wybranej wersji specyfikacji. Tabela obejmuje dokładnie wszystkie wyemitowane klucze gen_ai.* oraz dwa dodatkowe klucze, których obecność sprawdzam w tym samym śladzie. Brak atrybutów narzędzia i wymiaru embeddingu jest naturalny dla prostego zapytania tekstowego.

| Atrybut | Wyemitowany | W specyfikacji | Stabilność |
|---|---|---|---|
| `gen_ai.embeddings.dimension.count` | nie | tak | development |
| `gen_ai.operation.name` | tak | tak | development |
| `gen_ai.provider.name` | tak | tak | development |
| `gen_ai.request.max_tokens` | tak | tak | development |
| `gen_ai.request.model` | tak | tak | development |
| `gen_ai.request.temperature` | tak | tak | development |
| `gen_ai.response.finish_reasons` | tak | tak | development |
| `gen_ai.response.id` | tak | tak | development |
| `gen_ai.response.model` | tak | tak | development |
| `gen_ai.tool.name` | nie | tak | development |
| `gen_ai.usage.input_tokens` | tak | tak | development |
| `gen_ai.usage.output_tokens` | tak | tak | development |

Stabilność odnosi się do definicji atrybutu, a nie do wybranej wartości. development oznacza, że nazwa lub znaczenie mogą się jeszcze zmienić. Dlatego dashboard oparty na tych kluczach powinien mieć przypięte wersje instrumentacji i test po ich aktualizacji. Nie należy traktować development jako stable.

Wartość gen_ai.provider.name opisuje dostawcę rozpoznanego przez instrumentację SDK. Przy zgodnym interfejsie może wskazywać openai, chociaż samo wnioskowanie odbywa się lokalnie w Ollama. Nie jest to dowód wysłania danych do płatnego API. Liczby tokenów są odczytane z odpowiedzi lokalnego serwera.

Rejestr atrybutów: https://raw.githubusercontent.com/open-telemetry/semantic-conventions-genai/e57c543b4889619eb2a05702471937db5119165d/model/gen-ai/registry.yaml. Plik spec-attributes.json zachowuje nazwy i stabilności z tego konkretnego commita oraz SHA-256 pliku źródłowego.

Powtórzenie z katalogu repozytorium w PowerShell: `.\scripts\lab3-stretch.ps1 -Part genai`. Wymaga uruchomionego Docker Desktop.
