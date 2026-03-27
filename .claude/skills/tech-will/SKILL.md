---
name: tech-will
description: Generates a technical will for a contributor by running the tech-will CLI in archaeology or offboarding mode. Use when the user asks what someone left unfinished, what risks they warned about, or to reconstruct contributor intent from repo history.
---
# tech-will skill

## Purpose
Run the local `tech-will` CLI with normalized arguments and return the generated output paths.

## Usage Triggers
Use this skill when requests look like:
- "Generate a technical will for @alice on owner/repo"
- "What did @bob leave unfinished in this repo?"
- "Run tech-will archaeology for @charlie"

## Inputs
- `author` (required): contributor handle, with or without `@`
- `repo` (required): `owner/repo` or local path
- `mode` (optional): `archaeology` (default) or `offboarding`
- `output` (optional): markdown output path
- `format` (optional): `markdown`, `json`, or `both` (default `markdown`)
- `max_commits` (optional): default `1000`

## Execution
Call `skill.py` with explicit flags:

```bash
python .claude/skills/tech-will/skill.py \
  --repo owner/repo \
  --author alice \
  --mode archaeology \
  --format both
```

`skill.py` delegates to:

```bash
tech-will generate --repo ... --author ... --mode ... --format ...
```

## Output Contract
- Print the executed command.
- Stream CLI output.
- Return non-zero exit code if CLI fails.
- On success, report markdown/json output file locations from CLI output.

