# Lua Best Practices: Tables

## 1. Array Indices
- **1-Based Indexing**: Standard Lua arrays are 1-based. Always start your sequences and iterations at `1` to maintain compatibility with Lua's standard library functions like `ipairs` and the length operator `#`.
- **Handling Gaps (Holes)**: Avoid gaps (`nil` values) in array sequences. Gaps cause unpredictable behavior with the length operator and stop `ipairs` prematurely.

## 2. Iterations
- **`ipairs` vs. `pairs`**:
  - Use `ipairs` for ordered, sequential arrays. It is optimized for iterating over contiguous integer keys starting from 1 and guarantees iteration order.
  - Use `pairs` for dictionary-like tables where keys are non-sequential, strings, or other types. The order of traversal with `pairs` is undefined and not guaranteed.

## 3. Performance Optimization
- **Table Insertion**: Avoid using `table.insert(t, value)` inside performance-critical loops when simply appending to the end of an array. The function call introduces overhead. 
  - **Better Alternative**: Use `t[#t + 1] = value`, which executes much faster.
- **Preallocation**: When the table size is known in advance and you are working in high-performance environments, minimize table resizing overhead by reusing tables or assigning pre-calculated indices.

## 4. Dereferencing
- **Direct Access & Localization**: When repeatedly accessing nested table values in a loop or critical path, localize the reference to avoid the overhead of multiple table lookups.
  ```lua
  -- Suboptimal
  for i = 1, 100 do
      config.settings.volume = config.settings.volume + 1
  end

  -- Optimized
  local settings = config.settings
  for i = 1, 100 do
      settings.volume = settings.volume + 1
  end
  ```

## 5. Array Size
- **The Length Operator (`#`)**: Always use `#` to retrieve the length of an array-like table. Ensure the table is a pure sequence with no trailing `nil` values to prevent undefined length boundary results.
