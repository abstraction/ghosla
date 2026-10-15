# Lua Functions: Best Practices & Reference Guide

This document outlines standard coding conventions and best practices for defining and using functions in Lua.

## 1. Function Size and Scope
* **Single Responsibility Principle:** A function should do exactly one thing. If a function is handling multiple disparate tasks, break it down into smaller, testable helpers.
* **Keep it Concise:** Shorter functions are easier to read, debug, and maintain. If your function requires excessive vertical scrolling, consider refactoring.
* **Local by Default:** Always use `local function myFunc()` unless you specifically need to expose the function globally. Global functions pollute the environment and are marginally slower to look up.

## 2. Naming Conventions
* **Descriptive Names:** Use clear, action-oriented names. `GetPlayerInventory()` is far better than `GetInv()` or `LoadData()`.
* **Consistency:** Stick to a single casing standard throughout your project (e.g., `camelCase` or `PascalCase`).
* **Boolean Returns:** Functions that return a boolean should ideally be prefixed with `Is`, `Has`, or `Can` (e.g., `IsPlayerDead(source)`, `HasItem(item)`).
* **Private/Internal Functions:** If a function is not meant to be accessed outside its module or file, it is common to prefix it with an underscore (e.g., `local function _calculateTaxes()`).

## 3. Parameters and Arguments
* **Parameter Limits:** Avoid functions with a massive list of parameters. A good rule of thumb is 3 or fewer.
* **Option Tables:** If your function requires many parameters or optional configurations, accept a single `options` table instead.
  ```lua
  -- Bad
  function spawnVehicle(model, x, y, z, heading, isNetworked, isDynamic) ... end
  
  -- Good
  function spawnVehicle(model, coords, options) ... end
  ```
* **Default Values:** Handle missing arguments gracefully.
  ```lua
  function doSomething(value)
      value = value or "default_string"
  end
  ```

## 4. Guard Clauses (Early Returns)
Guard clauses improve readability by handling edge cases and errors at the top of the function, avoiding deep nesting.

**Anti-Pattern (Deep Nesting):**
```lua
function processPlayer(playerSource)
    local player = GetPlayer(playerSource)
    if player then
        if player.isAlive then
            if player.hasLicense then
                -- 3 levels deep: execute logic
            end
        end
    end
end
```

**Best Practice (Guard Clauses):**
```lua
function processPlayer(playerSource)
    local player = GetPlayer(playerSource)
    
    if not player then return end
    if not player.isAlive then return end
    if not player.hasLicense then return end
    
    -- 0 levels deep: execute logic
end
```
