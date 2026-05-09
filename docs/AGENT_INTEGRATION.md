# Integrating CLOAK from another tool

> Audience: AI agents (Codex, Claude, custom assistants) and developer tools that call CLOAK as a subprocess. If you're a human user, the [README](../README.md) is what you want.

CLOAK is a local CLI. It runs cleanly headless: stable JSON output (`--json`), predictable exit codes, no interactive prompts in non-TTY mode. That makes it easy to invoke from other tools without surprises.

## What CLOAK does, in one paragraph

A `.cloakpolicy` (YAML) sits at the user's repo root. CLOAK has three commands: `scan` finds secrets and proprietary markers; `context` produces a redacted markdown view of the source that's safe to paste into an LLM; `obfuscate` produces a transformed copy of the code that — if `--verify "<cmd>"` was passed — only succeeds if the user's tests pass against the transformed output. CLOAK is friction tooling, not unbreakable protection — surface that honestly when relevant.

## When you should call CLOAK

- The user is preparing to send code to an LLM (paste into chat, build a context packet, share with an assistant).
- A `.cloakpolicy` file exists at any ancestor directory of the target path. CLOAK finds it automatically; you don't need to.
- The user explicitly asked for a "safe paste", "redacted version", "AI-safe context", or "obfuscated copy".
- The user is preparing source for a contractor or third party (use `cloak obfuscate --verify`).

## When you should NOT call CLOAK

- For files outside the user's working repo or otherwise not under their control.
- The repo has no `.cloakpolicy` AND the user did not explicitly ask for redaction. Don't surprise users with silent redaction.
- For pure config files, build artifacts, or non-source assets.
- When the user asked for an explicit `--no-cloak` or equivalent escape hatch in your tool. Honor it.

## Detecting CLOAK and installing it

```bash
cloak --version
# Prints "cloak X.Y.Z" on stdout, exit 0. If the command isn't found, install it.
```

```bash
# Recommended:
pip install cloak-cli
# (The PyPI package name is cloak-cli; the binary on $PATH is `cloak`.)

# From source:
git clone https://github.com/newtophilly/cloak.git && cd cloak && pip install .
```

If installation fails, don't silently skip CLOAK in a workflow that explicitly asked for it — surface the error to the user.

## Commands and their JSON contracts

Always pass `--json` when invoking from another tool. The text output is for humans and uses Rich panels, tables, and ANSI codes that don't parse cleanly.

### `cloak scan`

Find secrets and proprietary markers.

```bash
cloak scan <path> [--policy <file>] [--json]
```

JSON output:

```json
{
  "command": "scan",
  "status": "ok",
  "files_scanned": 12,
  "policy_loaded_from": "/abs/path/to/.cloakpolicy",
  "policy_version": 1,
  "findings": [
    {
      "severity": "high",
      "file": "src/foo.py",
      "line": 42,
      "rule_id": "detect-secrets/AWS Access Key",
      "redacted_preview": "AKIA****************",
      "suggested_action": "Rotate this credential and remove it from source."
    }
  ]
}
```

`status` is `"ok"` when there are no findings, `"findings"` when there are. `policy_loaded_from` is `null` if no `.cloakpolicy` was found and defaults are being used. **Raw secrets are never printed — `redacted_preview` is the only secret-derived value that appears in output.**

### `cloak context`

Generate a redacted markdown view safe to paste into an LLM.

```bash
cloak context <path> [--out <file>] [--copy] [--strict] [--policy <file>] [--json]
```

- `--out <file>`: write the markdown to a file (default: stdout).
- `--copy`: also put the result on the system clipboard (uses `pbcopy` / `xclip` / `wl-copy` / `clip.exe` if available).
- `--strict`: aggressive mode — enum values aliased to opaque names, docstrings stripped. Use this when sharing code with parties you don't trust.
- `--json`: emit a status JSON instead of generating context. Useful as a probe to check whether CLOAK is available and what policy applies; doesn't actually produce the redacted output.

The default markdown output structure:
- A stable HTML-comment header with version, policy source, and `strict: true|false` for downstream tooling.
- A `## Files` section listing all input files.
- Per-file sections with imports, class shapes, function/method signatures, docstrings (per policy).
- Function/method bodies replaced with `...` for Python, `/* [REDACTED BY CLOAK] */` for JS/TS.
- Module-level UPPER_SNAKE_CASE constants holding dict/list/object/array literals replaced with `...` (Python) or `/* [REDACTED BY CLOAK] */ null` (JS/TS).

`--json` status output:

```json
{
  "command": "context",
  "status": "ok",
  "files_discovered": 12,
  "policy_loaded_from": "/abs/path/to/.cloakpolicy",
  "policy_version": 1,
  "strict": false,
  "implementation_status": "Python supported; JS/TS supported via tree-sitter."
}
```

### `cloak obfuscate`

Produce a transformed copy of a repo, optionally gated on a test command passing.

```bash
cloak obfuscate <path> --out <out_dir> [--verify "<test_cmd>"] [--profile standard|aggressive] [--policy <file>] [--json]
```

- `--out`: required. Output directory; must not exist or must be empty.
- `--verify "<test_cmd>"`: shell command run inside the output dir. The operation FAILS (exit 1) if the command exits non-zero. This is the differentiating feature — only succeeds if the user's tests pass against the obfuscated copy.
- `--profile`: currently `standard` is the only supported value. `aggressive` is reserved.

JSON output:

```json
{
  "command": "obfuscate",
  "status": "ok",
  "output_dir": "/abs/path/to/out",
  "manifest_path": "/abs/path/to/out/cloak-manifest.json",
  "files_copied": 1,
  "files_transformed": 2,
  "rename_count": 4,
  "policy_loaded_from": "/abs/path/to/.cloakpolicy",
  "verify_command": "pytest",
  "verify_passed": true
}
```

`status` is `"ok"` on success, `"verify_failed"` when `--verify` was passed and the test command exited non-zero, `"error"` when the operation couldn't proceed (e.g., output directory not empty). The output is still written when `verify_failed` so users can inspect what went wrong.

The output directory always contains `cloak-manifest.json` — the audit-trail artifact with: cloak version, generated-at timestamp, sha256 of every source file and every output file, the rename map keyed `path:original`, the policy hash + full policy snapshot, and (if applicable) the verify command + its result. The schema is in [`src/cloak/obfuscate/manifest.py`](../src/cloak/obfuscate/manifest.py).

## Exit codes

- `0` — success.
- `1` — operation completed with findings or verify failure that the caller should look at (e.g., `cloak scan` found secrets, `cloak obfuscate --verify` failed).
- `2` — usage / validation error (bad arguments, output directory not empty, etc.).

When in doubt, parse the JSON `status` field rather than relying only on the exit code.

## Policy file (`.cloakpolicy`)

YAML at the repo root. CLOAK auto-discovers it by walking up from the target path. If no policy is found, sensible defaults apply.

A short example:

```yaml
version: 1
sensitive_paths: ["src/pricing/**"]
public_api: ["QuoteEngine.calculate_quote"]
context_defaults:
  keep_docstrings: true
  redact_function_bodies: true
  alias_enums: false
obfuscate_defaults:
  profile: standard
  strip_docstrings: false
```

A full annotated example is at [`.cloakpolicy.example`](../.cloakpolicy.example) at the repo root.

**Don't modify a project's `.cloakpolicy` without explicit user consent.** Treat it like a CODEOWNERS file or a CI config — it's governance, not configuration you can adjust on the user's behalf.

## Common patterns

### Building a redacted context packet for an LLM

```bash
# Probe: is CLOAK installed and is there a policy in this repo?
cloak scan /path/to/repo --json

# If a policy was loaded OR the user explicitly asked for redaction:
cloak context /path/to/repo --out /tmp/safe.md
# Use /tmp/safe.md as the source-code section of the packet.
```

### Pre-paste workflow (user is about to ask an LLM for help)

```bash
cloak context /path/to/repo/src/foo.py --copy
# Tell the user: "Redacted view is on your clipboard; paste away."
```

### Preparing source for a contractor

```bash
cloak obfuscate /path/to/repo --out /tmp/repo.cloaked --verify "pytest"
# If exit 0, the obfuscated copy passes the user's tests — safe to ship.
# If exit 1, look at the JSON output's verify-related fields and tell the user.
# Either way, /tmp/repo.cloaked/cloak-manifest.json is the audit artifact.
```

## Honesty constraints when describing CLOAK to users

If your tool surfaces CLOAK output to a human, please match CLOAK's positioning:

- DO: "CLOAK redacted the proprietary parts before sending."
- DO: "CLOAK created a transformed copy that still passes your tests."
- DON'T: "Your code is now safe from AI."
- DON'T: "This is unreadable to LLMs."
- DON'T: "This is encrypted."

Obfuscation is friction, not cryptographic protection. The "What CLOAK is NOT" section in the [README](../README.md) is the canonical list of caveats — surface that wording verbatim if a user asks about CLOAK's guarantees.

## Reporting integration issues

Open an issue at https://github.com/newtophilly/cloak/issues with:
- The exact CLOAK version (`cloak --version`).
- Which tool was integrating with CLOAK (yours, fob, your own client, etc.).
- The command invoked and the full output.
- What you expected vs. what happened.
