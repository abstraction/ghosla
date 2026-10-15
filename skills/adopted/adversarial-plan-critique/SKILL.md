---
name: adversarial-plan-critique
description: Rigorously stress-test and critique implementation or configuration plans before execution to expose failure modes, regressions, and safety risks. Use when the user asks to critique a plan, verify safety before execution, check for regressions, or when preparing high-risk system changes.
---

# Adversarial Plan Critique

Stress-test and critique implementation and configuration plans before making modifications. Systematically expose edge cases, breaking changes, regression vectors, and execution risks before touching system files.

## Steps

1. **State baseline invariants**: Identify system invariants that must not break during the change (display manager state, boot integrity, process availability, dotfile tracked status).
2. **Scan for regression vectors**:
   - Check against established failure patterns in past sessions and project directives (e.g. bare commands without explicit file paths, untracked modifications, unverified display variables).
   - Trace external dependencies and services affected by configuration reloads.
3. **Audit atomicity and blast radius**:
   - Ensure operations target isolated single files rather than batch wildcards or global apply flags.
   - Verify every state mutation has an explicit rollback step (e.g. `chezmoi diff` and `git restore` path).
4. **Demand proof and verification gates**:
   - Construct non-destructive verification commands to run before and after applying changes.
   - Forbid execution on assumed state; require active inspection (checking logs, processes, or syntax) before confirming completion.
5. **Codify durable guardrails**: When a plan reveals an recurring operational mistake or recovery pattern, formulate explicit rules for permanent project directives (e.g. `AGENTS.md`) to prevent recurrence.

## Verification

- Inspect unstaged modifications before executing: `chezmoi diff` or `git status --short`.
- Verify syntax and linter status prior to reload: lint target configs or run dry-run validation commands.
- Confirm system stability immediately after reload by inspecting error logs or service units: `journalctl --since "1 minute ago" -p err`.

## Failure modes

- **Global or untargeted application hanging on conflicts**:
  - Failure: Running bare `chezmoi apply` or commands that prompt interactively can block background tasks or create unmanaged overwrites.
  - Recovery: Scope all apply commands strictly to the explicit target path (`chezmoi apply <path>`).
- **Assumption of external state without verification**:
  - Failure: Proceeding under the assumption that a hardware port, cable, display, or service is operational without live command evidence.
  - Recovery: Always run targeted probe commands (`hyprctl monitors`, `lspci`, `systemctl status`) before declaring failure or success.
- **Unverified plan execution causing UI/shell crash**:
  - Failure: Applying configuration variables or UI markup without linting can break user sessions or cause compositor loops.
  - Recovery: Gate every execution on pre-flight linting and staged testing.

## Notes

Forged by Lore from SpecStory sessions in operating-sys (2026-09-23→2026-10-11).
