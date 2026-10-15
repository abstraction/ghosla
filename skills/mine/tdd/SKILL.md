---
name: tdd
description: >-
  Test-driven development (TDD), unit testing, and E2E testing for Python and polyglot codebases.
  Combines behavior-focused vertical slices and seam-driven design (Matt Pocock), structured
  research-plan-implement test pipelines (awesome-copilot), and rigorous Python unittest/pytest/Textual
  pilot patterns (LambdaTest & modern test engineering). Use when writing tests, doing TDD, adding test
  coverage, debugging regressions, or writing E2E tests.
---

# Test-Driven Development & Comprehensive Testing (TDD)

Engineering guide for Test-Driven Development (TDD), unit testing, and end-to-end (E2E) testing.
This skill synthesizes three core methodologies:
1. **Seam-Driven TDD (Matt Pocock)**: Behavior over implementation details, vertical slicing (tracer bullets), and boundary-only mocking.
2. **Pipeline Testing Lifecycle (Polyglot Test Agent)**: Structured Research → Plan → Implement → Fix verification loop.
3. **Python & Framework Best Practices (LambdaTest & Textual Pilot)**: Standard `unittest`, `pytest`, and interactive UI/E2E testing (`textual.pilot`).

---

## 1. The Core Philosophy

### Behavior Over Implementation
Tests must verify observable behavior through **public seams**, not internal private methods or implementation details.
- **Good:** "When switching accounts, the active profile symlink points to the requested account directory."
- **Bad:** "When switching accounts, `_internal_link_helper` was called once with arguments `(a, b)`."

If you refactor internal code without altering user-facing behavior, your tests **must continue to pass without changes**.

### What is a Seam?
A **seam** is a public boundary where you observe behavior without reaching inside.
- Test at pre-agreed seams (CLI entrypoint, module public API, class public interface).
- Never poke into private attributes (`_private_field`) or patch internal helper functions.

### Anti-Patterns to Strictly Avoid
1. **Implementation Coupling:** Mocking internal collaborators or verifying internal calls (`mock.assert_called_with` on private functions).
2. **Tautological Tests:** Computing the expected result using the same logic as the implementation (`expected = sum(x); assert calc(x) == expected`). Expected values must come from an independent, known source of truth (fixtures, worked examples, explicit literals).
3. **Horizontal Slicing (Bulk Tests First):** Writing 20 speculative test cases before writing any code. This tests imagined shape rather than verified reality.
4. **Speculative Over-Engineering:** Writing implementation for features not demanded by the current failing test.
5. **Hardcoding Real-World Entities or Personal Data:** NEVER hardcode real user emails, personal names, live account aliases, production usernames, or machine-specific tokens in tests or fixtures. Always use purely generic, synthetic fixtures (e.g. `test_account_a`, `user@example.com`, `user_ineligible@corp.internal`). Coupling tests to real-world identities leaks personal context, introduces brittle coupling to local machine state, and causes test regressions when real-world states change.

---

## 2. The TDD Loop (Red → Green → Review)

Execute in tight **vertical slices (tracer bullets)**:

```
┌─────────────┐     Write 1 minimal failing test at a public seam.
│  1. RED     │ ──> Run the test suite: verify it fails for the expected reason.
└──────┬──────┘
       │
┌──────▼──────┐     Write ONLY enough production code to make the test pass.
│  2. GREEN   │ ──> Run the test suite: verify it passes cleanly.
└──────┬──────┘
       │
┌──────▼──────┐     Run linters (`ruff check`), formatters (`ruff format`),
│  3. REVIEW  │ ──> and static types (`mypy --strict`). Refactor cleanly.
└─────────────┘
```

Repeat this cycle one slice at a time.

---

## 3. Systematic Testing Pipeline

When tasked with adding tests or building a feature test-first, follow this four-phase pipeline:

### Phase 1: Research
- **Detect Language & Runner:** Identify if the project uses `unittest` (`python3 -m unittest discover -s tests`), `pytest`, or custom runners.
- **Map Dependencies & Boundaries:** Check where filesystem, network, keyring, and environment variables are touched.
- **Identify Seams:** List the public entry points that will be tested.

### Phase 2: Plan
- Group test cases by functional responsibility.
- Define independent test data and fixtures (e.g., isolated temporary directories, mock servers).
- Aim for high branch/line coverage of business logic (target 80%+), avoiding testing boilerplate.

### Phase 3: Implement (Vertical Slices)
- Write tests in standard locations (`tests/test_*.py`).
- Implement the unit or feature incrementally.
- Run tests after each slice to verify state.

### Phase 4: Fix & Verify
- If a test fails unexpectedly:
  1. Inspect the exact stack trace and assertion failure.
  2. Determine whether the expectation or the implementation is incorrect.
  3. Make the minimal necessary code change.
  4. Re-run tests until clean.
  5. Run linters (`ruff check`) and type checkers (`mypy --strict`).

---

## 4. Python Testing Patterns

### 4.1 Standard Library `unittest`
Used when zero extra dependencies are desired or in existing `unittest` suites:

```python
import unittest
from pathlib import Path
import tempfile
import shutil

class TestAccountManager(unittest.TestCase):
    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.root = Path(self.test_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_switch_creates_active_link(self) -> None:
        # Arrange
        account_path = self.root / "accounts" / "alpha"
        account_path.mkdir(parents=True)
        
        # Act
        apply_active(self.root, "alpha")
        
        # Assert
        active_link = self.root / "active"
        self.assertTrue(active_link.is_symlink())
        self.assertEqual(active_link.resolve(), account_path.resolve())

    def test_switch_missing_account_raises_error(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            apply_active(self.root, "nonexistent")
        self.assertIn("Account 'nonexistent' not found", str(ctx.exception))
```

### 4.2 SubTests for Parameterization (`unittest`)
```python
def test_quota_percentages(self) -> None:
    cases = [
        (100, 100, 100.0),
        (50, 100, 50.0),
        (0, 100, 0.0),
    ]
    for current, total, expected in cases:
        with self.subTest(current=current, total=total):
            self.assertAlmostEqual(calculate_ratio(current, total), expected)
```

### 4.3 Boundary Mocking with `unittest.mock`
Only mock external systems (OS Keyring, network requests, external binaries, system clock):

```python
from unittest.mock import patch, MagicMock

@patch("subprocess.run")
def test_refresh_invokes_external_cli_safely(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout='{"status": "ok"}', stderr="")
    
    result = fetch_remote_quota("test-account")
    
    self.assertEqual(result.status, "ok")
    mock_run.assert_called_once()
```

### 4.4 TUI E2E Testing with Textual Pilot
For testing Textual terminal applications asynchronously without opening an actual terminal window:

```python
import pytest
from textual.pilot import Pilot
from antigravity_cli_switcher.tui.app import ACSApp
from antigravity_cli_switcher.tui.widgets.account_table import AccountTable

@pytest.mark.asyncio
async def test_dashboard_loads_accounts(mock_paths: ManagerPaths) -> None:
    app = ACSApp(paths=mock_paths)
    async with app.run_test() as pilot:
        # Verify initial screen mount
        table = pilot.app.query_one(AccountTable)
        assert table is not None
        assert table.row_count > 0
        
        # Simulate pressing 'r' (switch next)
        await pilot.press("r")
        await pilot.pause()
        
        # Verify status bar or state updated
        status = pilot.app.query_one("#status-bar").renderable
        assert "Switched to" in str(status)
```

---

## 5. Mocking Checklist

| Boundary | Recommended Strategy |
|---|---|
| **Filesystem** | Use real temporary directories (`tempfile.TemporaryDirectory` or `tmp_path`). Avoid mocking `os.path` or `open()`. |
| **OS Keyring** | Use an in-memory mock backend or an isolated keyring context manager (`_isolated_keyring_warmup`). |
| **Subprocess Execution** | Mock `subprocess.run` or inject an execution runner function. |
| **Network / HTTP** | Use HTTP test doubles (`respx`, `responses`, or inject a fake transport). |
| **System Time** | Inject a `clock` callable or use `freezegun` / `time_machine`. |
| **Internal Domain Objects** | **NEVER MOCK.** Use the real classes and functions. |
