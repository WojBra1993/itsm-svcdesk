FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py prom_mcp.py ./
COPY <<'PY' /app/run_investigation.py
import asyncio
import sys
import agent

agent.SYSTEM += (
    ' Tool string arguments must be plain JSON strings, never objects with type/value fields. '
    'Keep every query time on 2026-10-12 inside the requested window. '
    'Aggregate histogram results by service_name and le; do not fetch every raw bucket. '
    'Do not infer zero traffic from an empty result at the wrong time.'
)
agent.FINAL += (
    ' Output at least THREE numbered hypotheses H1, H2, H3 as separate complete sentences. '
    'Each sentence must name one service and one testable symptom or mechanism. '
    'Give the supporting query and distinguish an untested hypothesis from an observation. '
    'Do not combine all services into one hypothesis.'
)
sys.exit(asyncio.run(agent.main(' '.join(sys.argv[1:]))))
PY
CMD ["python", "run_investigation.py"]
