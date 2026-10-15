# Error Handling in Lua

## 1. Purpose
Graceful error handling is critical for preventing script crashes. Proper management of errors ensures reliability, aids debugging, and improves the overall resilience of the codebase.

## 2. Best Practices

### 2.1 Pre-conditions & Assertions
Validate inputs and initial states before executing primary logic. Use `assert()` to enforce conditions that *must* be true for the code to proceed. This is great for developer-facing APIs.

```lua
-- Good: Using assert to validate critical assumptions
function calculateDistance(point1, point2)
    assert(point1 and point2, "Both points must be provided")
    assert(type(point1.x) == "number", "point1.x must be a number")
    
    -- Logic continues...
end
```

### 2.2 Protected Calls (`pcall` / `xpcall`)
Never let unexpected runtime errors crash the main thread. Wrap risky operations (like network calls, parsing, or external module interactions) in a `pcall` (protected call) to handle failures safely.

```lua
-- Bad: Will crash the script if parsing fails
local data = json.decode(invalidJsonString)

-- Good: Safely catching the error
local success, data = pcall(json.decode, invalidJsonString)
if not success then
    print("Failed to decode JSON: " .. tostring(data))
    -- Handle the error gracefully
end
```

### 2.3 Errors as Values
Instead of raising exceptions that halt execution, functions can return multiple values: typically the result on success, or `nil` and an error message on failure. This forces the caller to acknowledge and handle the error.

```lua
function fetchUserData(userId)
    if not userId then
        return nil, "Invalid User ID"
    end
    
    -- Simulation of fetch
    return { name = "John", id = userId }
end

-- Good: Handling the error value explicitly
local user, err = fetchUserData()
if err then
    print("Error fetching user: " .. err)
else
    print("User: " .. user.name)
end
```

### 2.4 Fail Loudly (During Development)
During the development phase, you should surface errors rather than silencing them. Empty `pcall` checks or swallowed exceptions make debugging extremely difficult.

```lua
-- Bad: Swallowing errors silently
pcall(function()
    doRiskyThing()
end)

-- Good: Logging the error so it can be identified and fixed
local success, err = pcall(doRiskyThing)
if not success then
    print("[ERROR] doRiskyThing failed: " .. tostring(err))
end
```
