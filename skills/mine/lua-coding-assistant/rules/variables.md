# Lua Best Practices: Variables

## 1. Scope Management
- **Always Use `local`**: Variables in Lua are global by default. You must explicitly declare variables as `local`. Local variables are significantly faster to access (as they are stored in registers rather than global hash tables) and prevent namespace pollution.
- **Narrow Scopes**: Keep variable scopes as narrow as possible. Declare them right before they are needed and restrict their visibility to their specific block (e.g., inside an `if` block, function, or `for` loop).

## 2. Variable Naming Conventions
- **Descriptive Names**: Use clear, descriptive names for variables to maximize readability. Avoid single-letter variables unless they are standard loop iterators (`i`, `j`, `k`) or dictionary pairs (`k`, `v`).
- **Consistent Casing**: Stick to consistent casing (typically `camelCase` or `snake_case` in Lua). Adhere to the established style guide for your project.

## 3. Constants
- **Capitalization**: Represent constants using `UPPER_SNAKE_CASE` so they are immediately identifiable to other developers.
- **Read-Only Intent**: Standard Lua versions prior to 5.4 lack strict `const` declarations. Formatting as uppercase visually signals that the variable's value should remain immutable. (If using Lua 5.4+, you can utilize the `<const>` attribute).

## 4. Enums vs. Booleans
- **Use Enums for Complex State**: Avoid boolean variables when representing states that could expand beyond two options. 
  - **Suboptimal**: `is_walking = true`, `is_running = false`
  - **Optimized**: Use an enum-like table or descriptive string constants, e.g., `state = STATES.RUNNING`.
- **Meaningful Code**: Relying on enums over ambiguous boolean combinations drastically improves code readability and makes state transitions self-documenting.

## 5. Conditionals and Defaults
- **Default Values**: Use the `or` operator to assign fallback values concisely.
  ```lua
  local playerName = inputName or "Unknown Player"
  ```
- **Boolean Readability**: Write boolean conditions clearly. Do not write redundant `== true` or `== false` checks.
  ```lua
  -- Suboptimal
  if isValid == true then ... end
  
  -- Optimized
  if isValid then ... end
  ```
