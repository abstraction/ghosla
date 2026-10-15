# Conditionals in Lua

## 1. Purpose
Consistent conditional patterns improve code readability, maintainability, and execution efficiency in Lua. Proper use of boolean logic and early returns prevents deeply nested logic and reduces cognitive load, which is critical for readable scripts.

## 2. Best Practices

### 2.1 Boolean Expressions & Truthiness
In Lua, only `false` and `nil` are considered false. Everything else, including `0`, `""` (empty string), and `{}` (empty table), evaluates to `true`.
- **Avoid explicit comparisons to `true` or `false`** when checking truthiness.

```lua
-- Bad
if isReady == true then ... end
if hasData ~= nil then ... end

-- Good
if isReady then ... end
if hasData then ... end
```

### 2.2 Default Values (The `or` Idiom)
Leverage Lua's logical operators (`or`) to assign default values concisely. The `or` operator returns its first operand if it is truthy; otherwise, it returns the second.

```lua
-- Bad
local config = options
if not config then
    config = {}
end

-- Good
local config = options or {}
```

### 2.3 Early Returns (Guard Clauses)
Avoid deep nesting by checking for invalid states early and returning immediately. This is known as the "Guard Clause" pattern.

```lua
-- Bad
function processPlayer(player)
    if player then
        if player.isAlive then
            -- Deeply nested logic
            player:giveItem("health_pack")
        end
    end
end

-- Good
function processPlayer(player)
    if not player or not player.isAlive then return end
    
    -- Primary logic remains at the top level of indentation
    player:giveItem("health_pack")
end
```

### 2.4 Ternary Operators
Lua does not have a built-in ternary operator (`? :`), but you can simulate it using `and` and `or`. 
*Warning:* This only works safely if the true branch value is not `false` or `nil`.

```lua
-- Good
local status = isOnline and "Online" or "Offline"
```
