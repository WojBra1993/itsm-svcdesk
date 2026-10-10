# ai-generated: 100% - Codex wrote the local LLM capture and comparison; evidence comes from the actual SDK export.
"""Call local Ollama once and compare the unmodified OTel export to the pinned spec."""

import json
import io
import os
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4


def read_genai_attributes(export):
    attributes = {}
    spans_seen = 0
    for line in export.splitlines():
        if not line.strip():
            continue
        batch = json.loads(line)
        for resource in batch.get("resourceSpans", []):
            for scope in resource.get("scopeSpans", []):
                for span in scope.get("spans", []):
                    spans_seen += 1
                    if span.get("status", {}).get("code") in (2, "STATUS_CODE_ERROR"):
                        raise RuntimeError("The exported span reports an error; not saving evidence.")
                    for attribute in span.get("attributes", []):
                        if attribute["key"].startswith("gen_ai."):
                            attributes[attribute["key"]] = attribute.get("value", {})
    if not spans_seen or not attributes:
        raise RuntimeError("No exported GenAI span found; not saving evidence.")
    return attributes


def build_diff(attributes, registry, model, response_model, timestamp):
    emitted = set(attributes)
    # Also show two real omissions: a chat request makes no embedding or tool call.
    names = emitted | {"gen_ai.tool.name", "gen_ai.embeddings.dimension.count"}
    if len(names) < 5:
        raise RuntimeError("The export contains too few attributes; inspect instrumentation.")
    libraries = "; ".join(
        f"{name}=={version(name)}" for name in (
            "opentelemetry-instrumentation-genai-openai", "opentelemetry-sdk", "openai",
            "opentelemetry-exporter-otlp-json-file",
        )
    )
    lines = ["---", "lab3_genai_diff:",
             f"  instrumentation: {json.dumps(libraries)}",
             f"  spec_ref: {json.dumps(registry['spec_ref'])}", "  attributes:"]
    rows = []
    for name in sorted(names):
        stability = registry["attributes"].get(name)
        item = {"name": name, "emitted": name in emitted, "in_spec": stability is not None}
        if stability is not None:
            item["stability"] = stability
        lines.append("    - " + json.dumps(item))
        rows.append(f"| `{name}` | {'tak' if name in emitted else 'nie'} | "
                    f"{'tak' if stability else 'nie'} | {stability or 'poza wskazana specyfikacja'} |")
    outside = sorted(name for name in emitted if name not in registry["attributes"])
    comparison = ("Wszystkie wyemitowane klucze gen_ai.* występują w wybranej wersji specyfikacji."
                  if not outside else "Klucze spoza wybranej wersji specyfikacji: " + ", ".join(outside) + ".")
    lines.extend([
        "---",
        "<!-- ai-generated: 100% - Codex wrote the comparison; names and values come from the actual local LLM trace. -->",
        "", "# Ślad lokalnego modelu a specyfikacja GenAI", "",
        f"Pomiar UTC: {timestamp}. Jedno rzeczywiste, niestreamowane wywołanie Chat Completions "
        f"przez SDK OpenAI do lokalnego serwera Ollama w Dockerze. Model żądany: `{model}`; "
        f"model wskazany przez odpowiedź: `{response_model}`. SDK nie ponawia żądania.", "",
        "Prompt: Explain in one short sentence what an error budget is.", "",
        "Plik spans.json jest bezpośrednim eksportem FileSpanExporter. Skrypt nie dopisuje "
        "atrybutów do spanów ani nie zamienia ich wartości. Treść promptu i odpowiedzi nie "
        "jest rejestrowana przez instrumentację; powyżej podaję prompt użyty przez skrypt.", "",
        comparison + " Tabela obejmuje dokładnie wszystkie wyemitowane klucze gen_ai.* "
        "oraz dwa dodatkowe klucze, których obecność sprawdzam w tym samym śladzie. "
        "Brak atrybutów narzędzia i wymiaru embeddingu jest naturalny dla prostego zapytania tekstowego.", "",
        "| Atrybut | Wyemitowany | W specyfikacji | Stabilność |",
        "|---|---|---|---|", *rows, "",
        "Stabilność odnosi się do definicji atrybutu, a nie do wybranej wartości. "
        "development oznacza, że nazwa lub znaczenie mogą się jeszcze zmienić. "
        "Dlatego dashboard oparty na tych kluczach powinien mieć przypięte wersje "
        "instrumentacji i test po ich aktualizacji. Nie należy traktować development jako stable.", "",
        "Wartość gen_ai.provider.name opisuje dostawcę rozpoznanego przez instrumentację SDK. "
        "Przy zgodnym interfejsie może wskazywać openai, chociaż samo wnioskowanie odbywa się "
        "lokalnie w Ollama. Nie jest to dowód wysłania danych do płatnego API. "
        "Liczby tokenów są odczytane z odpowiedzi lokalnego serwera.", "",
        f"Rejestr atrybutów: {registry['source_url']}. Plik spec-attributes.json zachowuje "
        "nazwy i stabilności z tego konkretnego commita oraz SHA-256 pliku źródłowego.", "",
        "Powtórzenie z katalogu repozytorium w PowerShell: "
        "`.\\scripts\\lab3-stretch.ps1 -Part genai`. Wymaga uruchomionego Docker Desktop.", "",
    ])
    return "\n".join(lines)


def main():
    from openai import OpenAI
    from opentelemetry.exporter.otlp.json.file import FileSpanExporter
    from opentelemetry.instrumentation.genai.openai import OpenAIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    output = Path(os.environ.get("TRACE_OUTPUT_DIR", "/output"))
    output.mkdir(parents=True, exist_ok=True)
    model = os.environ.get("LLM_MODEL", "qwen2.5:0.5b")
    base_url = os.environ.get("LLM_BASE_URL", "http://ollama:11434/v1")
    registry = json.loads(Path(__file__).with_name("spec-attributes.json").read_text(encoding="utf-8"))
    timestamp = datetime.now(timezone.utc).isoformat()
    with io.StringIO() as stream:
        provider = TracerProvider(resource=Resource.create({"service.name": "svcdesk-lab3-genai"}))
        provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(stream=stream)))
        instrumentor = OpenAIInstrumentor()
        instrumentor.instrument(tracer_provider=provider)
        try:
            print(f"Calling local model {model}; the first CPU inference may take a few minutes.", flush=True)
            with OpenAI(base_url=base_url, api_key="ollama", max_retries=0, timeout=300.0) as client:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Explain in one short sentence what an error budget is."}],
                    temperature=0,
                    max_tokens=64,
                )
            if not response.choices or not response.choices[0].message.content:
                raise RuntimeError("The model returned no text; not saving evidence.")
            if not provider.force_flush():
                raise RuntimeError("Trace export did not flush; not saving evidence.")
        finally:
            instrumentor.uninstrument()
            provider.shutdown()
        export = stream.getvalue()
        attributes = read_genai_attributes(export)
        diff = build_diff(attributes, registry, model, response.model, timestamp)
        suffix = uuid4().hex
        trace_path = output / f".capture-{suffix}-spans.json"
        diff_path = output / f".capture-{suffix}-DIFF.md"
        try:
            trace_path.write_text(export, encoding="utf-8")
            diff_path.write_text(diff, encoding="utf-8")
            trace_path.replace(output / "spans.json")
            diff_path.replace(output / "DIFF.md")
        finally:
            trace_path.unlink(missing_ok=True)
            diff_path.unlink(missing_ok=True)
        print(f"Saved real model trace: {len(attributes)} GenAI attributes and DIFF.md.", flush=True)
        print("Local response:", response.choices[0].message.content, flush=True)


if __name__ == "__main__":
    main()
