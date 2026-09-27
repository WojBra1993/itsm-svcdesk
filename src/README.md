<!-- ai-generated: 0% - written by the course team -->
# src/

Your implementation lives here, in any language. `Dockerfile.example` copies this directory into the image and
starts `svcdesk.main:app` with uvicorn; change the module path to your layout, or replace the Dockerfile.

Do not add any file under `src/` before your `specs` receipt exists: Core spec L1-CORE-5 requires every commit
that adds a file here (other than this README) to be a descendant of the receipted specs commit.

Every source file (`.py .go .ts .js .java .cs .rb .rs .kt .md`) carries, in its first ten lines, a comment
matching `ai-generated: <0-100>% - <one line on how>`, for example:

    # ai-generated: 80% - Claude Code drafted, I rewrote the SLA clock

The checker reports files without it (advisory `ai-disclosure`); the course rules require it on every file,
including an otherwise empty `__init__.py` (one comment line is enough). Files without one of those
extensions (YAML, shell, Dockerfile, requirements.txt) are not checked and need no header.
