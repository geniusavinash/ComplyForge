# the Lobster Trap integration step — Lobster Trap reality-check log + schema diff

This document is the ground-truth record for the Lobster Trap integration step. Re-read it before
trusting any claim about what ComplyForge integrates with.

## Reality Check 1 — repo reachability

| Probe | Result |
| --- | --- |
| `git ls-remote https://github.com/veeainc/lobstertrap.git HEAD` | exit `0`, returned `e49a402864104c19c9a560ad73e06d5493e5d876 HEAD` |
| `git clone --depth=1 https://github.com/veeainc/lobstertrap.git lobstertrap/src` | exit `0`, full tree present (`cmd/`, `internal/policy/`, `configs/default_policy.yaml`, `Makefile`, `README.md`, `claude.md`) |
| Mirror `https://github.com/coal/lobstertrap.git` | not retried — primary succeeded. The Go module path declared in `src/go.mod` is `github.com/coal/lobstertrap`, confirming `coal` is the original author and `veeainc` is the canonical fork. |

**Outcome:** REACHABLE. We are operating against the real upstream code,
not a guess.

## Reality Check 2 — Go installed?

| Probe | Result |
| --- | --- |
| `go version` | exit `0`, `go version go1.25.5 windows/amd64` |
| `go build -o ..\bin\lobstertrap.exe .` (run from `src/`) | exit `0`, dependencies fetched (`zerolog`, `cobra`, `nhooyr.io/websocket`, `mousetrap`, `pflag`, `colorable`, `isatty`) |
| `bin\lobstertrap.exe version` | exit `0`, `lobstertrap v0.1.0` |
| `bin\lobstertrap.exe inspect --policy policies\default.yaml "ignore all previous instructions ..."` | exit `0`, `Action: DENY`, `Rule: block_prompt_injection_signatures`, `Message: [ComplyForge] Blocked: prompt-injection signature.` |

**Outcome:** Go is installed AND the binary builds AND the binary
successfully loads the ComplyForge baseline policy AND it actively denies a
classic injection payload. Definition of Done item "binary exists and runs
--version" is met from this end.

## Reality Check 3 — schema confirmed?

**Outcome:** CONFIRMED. The real schema differs materially from the
initial design placeholder. Source of truth in the cloned upstream:
`src/internal/policy/types.go`, `src/internal/policy/loader.go`,
`src/configs/default_policy.yaml`, and `src/README.md`.

### Field-by-field diff

| Initial placeholder shape | Real Lobster Trap | Notes |
| --- | --- | --- |
| `name: <policy>` | `policy_name: <policy>` | Top-level policy name. |
| `version: 1` (int) | `version: "1.0"` (string) | Loader rejects empty / numeric. |
| `rules:` (single list) | `ingress_rules:` + `egress_rules:` (split) | Direction is encoded by which list, not by a `match.direction` field. |
| (none) | `default_action: ALLOW \| DENY \| ...` | Required default; ComplyForge sets `DENY` for prohibited tier and `ALLOW` otherwise. |
| `id:` per rule | `name:` per rule | Loader enforces non-empty. |
| `priority: <int, lower = higher priority>` | `priority: <int, HIGHER = evaluated first>` | **Inverted.** ComplyForge now emits `priority` in 10–110 range with `100+` for blocks. |
| `match: { direction, any_of: [...] }` | `conditions: [...]` (AND logic) | No `direction` (encoded by list); no `any_of` (semantics are AND, not OR). |
| `any_of: [{intent: ".*"}, {contains: "..."}]` | `[{field, match_type, value, negate?}]` | Conditions are typed: `field` is a structured DPI metadata key (e.g. `contains_injection_patterns`, `contains_pii`, `intent_category`, `risk_score`, `token_count`), not a free-form regex. `match_type` is one of `exact`, `prefix`, `glob`, `regex`, `range`, `contains`, `boolean`, `threshold`. |
| `reason: <string>` | `description: <string>` (+ optional `deny_message`) | ComplyForge maps Gemini-generated reasons into `description`. |
| (none) | `deny_message: <string>` | Returned to the caller when action=DENY. ComplyForge populates this for every DENY/QUARANTINE rule. |
| (free text matchers) | DPI metadata fields are pre-extracted by `internal/inspector` | `contains_credentials` already covers `sk-...`, `AKIA[0-9A-Z]{16}`, `ghp_/github_pat_...`, bearer tokens, `API_KEY=`. `contains_injection_patterns` already covers "ignore previous instructions", "you are now ...", DAN-style jailbreaks, etc. ComplyForge uses these booleans rather than re-implementing the regex. |

### Action vocabulary — IDENTICAL

`ALLOW`, `DENY`, `LOG`, `HUMAN_REVIEW`, `QUARANTINE`, `RATE_LIMIT`,
`MODIFY`, `REDIRECT`. No change required to ComplyForge's `VALID_ACTIONS`
frozenset.

### Per-tier rule counts — UNCHANGED

ComplyForge keeps the original 1 / 5 / 2 / 1 plan: prohibited (1 ingress
DENY), high-risk (3 ingress + 2 egress = 5), limited-risk (2 egress),
minimal-risk (1 ingress LOG). The only thing that moved is which list each
rule lives in.

## Is the YAML in this folder placeholder-shape or real-shape?

**Real-shape.** Both `policies/default.yaml` and
`policies/example_high_risk.yaml` use `policy_name`, `version: "1.0"`,
split `ingress_rules` / `egress_rules`, `name`/`description`/`priority`/
`action`/`conditions` with `field`+`match_type`+`value`. Both load cleanly
through the real Go loader (`bin\lobstertrap.exe inspect --policy <file>`
returned exit 0 for each).

## Did the Lobster Trap integration step patch the backend?

**Yes — minimally.** The schema confirmation triggered the patch rule in
the the Lobster Trap integration step brief:

* `backend/app/agents/policy_generator.py` — emits the real schema (split
  `ingress_rules`/`egress_rules`, `policy_name`, `version: "1.0"`,
  `default_action`, conditions with `field`+`match_type`+`value`,
  `description`, `deny_message`). The single-Gemini-call contract is
  preserved; only YAML serialisation and rule-skeleton field names changed.
  `_rule()` was renamed-in-place to take `name`/`description`/`conditions`
  and a new `_cond()` helper builds DPI conditions.
* `backend/tests/test_policy_generator.py` — assertions updated to the
  real schema (`parsed["ingress_rules"]` / `parsed["egress_rules"]`,
  `rule["name"]`, `rule["description"]`, `rule["conditions"]`,
  `parsed["policy_name"]`, `parsed["version"] == "1.0"`). Per-tier counts
  (1 / 5 / 2 / 1), Article 5 reference for prohibited, PII matcher for
  high-risk, MODIFY-with-Article-50 for limited-risk, single LOG for
  minimal-risk are all preserved. Two new tests were added that the real
  loader implicitly requires:
    - `test_document_has_real_lobstertrap_top_level_fields` — guards
      against future regression on `version`/`policy_name`/
      `default_action`.
    - `test_every_rule_has_at_least_one_condition` — the Go loader
      explicitly rejects rules with zero conditions.

No other backend files were touched. `print_sample_policy.py` continues to
work unchanged because PolicyAgent's public surface (`generate(...)
-> LobsterTrapPolicy`) is intact.

## Re-test result

`python -m pytest tests/ -v` from `backend/`: **87 passed, 50 warnings in
1.55s**, exit 0. The two extra tests are net-new real-schema guards. The
original 85 tests from an earlier milestone all still pass.

## What was NOT done

* No GUI dashboard wiring — that is the frontend dashboard work.
* No live regression of `webhook_bridge.py` against a running proxy +
  backend pair (that is a manual demo step, not a the Lobster Trap integration step deliverable).
  The script is syntax-clean (`python -m py_compile`) and its event-source
  abstractions are based on the real `internal/dashboard/handler.go`
  (`/_lobstertrap/api/events`) and `internal/audit/logger.go` (JSONL audit
  stream) APIs verified in this folder's `src/`.
