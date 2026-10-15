# Good and Bad Test Patterns

## Characteristics of Resilient Tests
1. **Tests Observable Behavior:** Tests should read like a specification of what the system does from the outside.
2. **Uses Public APIs Only:** Refactoring private methods or changing internal call graphs should not break tests.
3. **One Logical Concept per Test:** Each test focuses on a single scenario or state transition.
4. **Independent Assertions:** Assertions compare against known literals or independent specifications, never restating the code's internal calculations.

## Good Test Examples (Python)

```python
# GOOD: Tests public interface and observable outcome
def test_switch_account_activates_selected_profile(self):
    manager = AccountManager(self.test_dir)
    manager.add_account("alpha")
    
    result = manager.switch_account("alpha")
    
    self.assertEqual(result.active, "alpha")
    self.assertEqual(manager.get_active_account(), "alpha")
```

## Anti-Pattern Examples (What to Avoid)

```python
# BAD: Tautological test - passes by construction because it recalculates like the code
def test_quota_percentage_bad(self):
    used = 42
    total = 100
    expected = (used / total) * 100
    self.assertEqual(calculate_pct(used, total), expected)

# GOOD: Tests against an independent known truth
def test_quota_percentage_good(self):
    self.assertEqual(calculate_pct(42, 100), 42.0)

# BAD: Mocking internal collaborators
@patch("antigravity_cli_switcher.manager._internal_symlink_helper")
def test_switch_calls_internal_helper(self, mock_helper):
    switch_account("alpha")
    mock_helper.assert_called_once()
```
