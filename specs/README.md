<!-- ai-generated: 0% - written by the course team -->
# specs/

Your specifications live here: what the service must do, written and published before the code.

- spec-kit writes `specs/<nnn>-<feature>/spec.md`, `plan.md` and `tasks.md` here (its constitution lives in
  `.specify/memory/constitution.md`; that is fine, the checker does not look for it).
- Writing by hand: any Markdown files, any layout, as long as they describe the service before you build it.

Order matters (Core spec L1-CORE-5): push your specs, obtain the `specs` receipt
(`./itsmlab.sh submit 1 --kind specs`, on Windows `.\itsmlab.ps1 submit 1 --kind specs`, then the issue form), and only
then commit files under `src/`.
The receipt requires at least one file of 500 bytes or more in this directory (this README and
`.gitkeep` do not count) and no file under `src/` other than `src/README.md`.

Every `.md` file here carries the AI-disclosure comment in its first ten lines, like the first line of this file:
`<!-- ai-generated: <0-100>% - <one line on how> -->`.
