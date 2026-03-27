# tech-will

[![CI](https://github.com/just-claw-it/tech-will/actions/workflows/ci.yml/badge.svg)](https://github.com/just-claw-it/tech-will/actions/workflows/ci.yml)

`tech-will` reconstructs a developer's implicit technical intent from contribution history and produces a structured **technical will**.

It supports:
- **Archaeology mode**: reconstruct intent for someone who already left.
- **Offboarding mode**: generate and review before sharing (`a/e/s/x` gate).
- **Deterministic mode**: skip LLM calls and render from extracted signals (`--no-llm`).

Outputs:
- Markdown document
- JSON sidecar with structured fields + metadata

## Install

```bash
python -m pip install -e ".[dev]"
```

## Configuration

Copy and edit:

```bash
cp techwill.yaml.example techwill.yaml
```

Environment variables used by LLM client:
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

Optional GitHub token:
- `GITHUB_TOKEN`

`--no-llm` mode does not require LLM environment variables.

## CLI Usage

Generate archaeology will:

```bash
tech-will generate --repo owner/repo --author alice --mode archaeology
```

Generate offboarding will (with review gate):

```bash
tech-will generate --repo owner/repo --author alice --mode offboarding --format both
```

Local repo path:

```bash
tech-will generate --repo ./path/to/local/repo --author alice
```

Use config defaults from `techwill.yaml`:

```bash
tech-will generate --repo owner/repo --author alice --config ./techwill.yaml
```

Strict validation (fail fast on malformed structured output):

```bash
tech-will generate --repo owner/repo --author alice --strict
```

Deterministic generation without LLM:

```bash
tech-will generate --repo owner/repo --author alice --no-llm --format both
```

Dry run (extract/analyze only, no files written):

```bash
tech-will generate --repo owner/repo --author alice --dry-run
```

Disable cache for a fresh extraction:

```bash
tech-will generate --repo owner/repo --author alice --no-use-cache
```

Inspect signals only (no will generation):

```bash
tech-will inspect --repo owner/repo --author alice
```

Preflight validation:

```bash
tech-will validate
```

Validate local repo readability:

```bash
tech-will validate --repo ./path/to/local/repo
```

Validate remote GitHub + LLM connectivity:

```bash
tech-will validate --repo owner/repo --check-remote --check-llm
```

`validate` prints `[PASS]`/`[FAIL]` for each check and exits non-zero on any failure.

List contributors (local repo support in current build):

```bash
tech-will contributors --repo ./path/to/local/repo --min-commits 10
```

## Output

Default markdown filename:

```text
will-{author}-{repo-slug}.md
```

When JSON is enabled (`--format json|both`), sidecar is written as:

```text
will-{author}-{repo-slug}.json
```

JSON includes a `metadata` block with signal counts, confidence note, and inference/severity flags.

Cache files are written under:

```text
.techwill-cache/
```

## OpenClaw Skill

Skill files are under:
- `.claude/skills/tech-will/SKILL.md`
- `.claude/skills/tech-will/skill.py`

Wrapper usage:

```bash
python .claude/skills/tech-will/skill.py --repo owner/repo --author alice --mode archaeology --format both
```

## Test

```bash
python -m pytest -q
```

