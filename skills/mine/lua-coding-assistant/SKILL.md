---
name: lua-coding-assistant
description: >-
  Use this skill when writing, reviewing, or refactoring Lua code.
  It provides project-specific Lua guidelines, styling rules, and best practices.
---

# Lua Coding Assistant

This skill defines the standard operating procedures and coding guidelines for writing Lua code in this repository. 

## Workflow

1. **Understand the Guidelines**: Before writing or modifying Lua code, review the core guidelines outlined below.
2. **Consult Specific Rules (Progressive Disclosure)**: For complex structures or specific implementations, read the relevant rule files:
   - For logic flow: [Conditionals Rulebook](./rules/conditionals.md)
   - For error handling: [Errors Rulebook](./rules/errors.md)
   - For writing functions: [Functions Rulebook](./rules/functions.md)
   - For data structures: [Tables Rulebook](./rules/tables.md)
   - For variable scoping: [Variables Rulebook](./rules/variables.md)
3. **Write/Refactor Code**: Implement the changes adhering strictly to the guidelines.

## Core Lua Guidelines

### 1. General Style & Idiomatic Lua
*   **Clarity and Conciseness:** Write clean, readable, and idiomatic Lua code. Keep functions small and focused.
*   **Guard Clauses:** Use early returns (guard clauses) to reduce nesting and improve readability.
*   **1-Based Indexing:** Consistently adhere to Lua's native 1-based indexing for arrays.

### 2. Variable & State Management
*   **Local Over Global:** Maximize the use of `local` variables for both performance optimization and scope safety. Avoid global variables whenever possible.
*   **Naming Conventions:** Use clear and consistent naming for constants and variables.
*   **Enums vs. Booleans:** Favor enums over booleans when a state can have more than two possibilities to improve code clarity.

### 3. Tables & Metatables
*   **Table Operations:** Manage array indices carefully. Avoid `table.insert` when direct indexing is faster and more appropriate.
*   **Metatables & Metamethods:** Use metatables effectively for object-oriented patterns or advanced table behaviors.
*   **Iteration:** Use the appropriate iteration methods (`ipairs` for arrays, `pairs` for dictionaries) and manage array sizes efficiently.

### 4. Conditionals & Control Flow
*   **Default Values:** Use Lua's logical operators (e.g., `a = b or default`) to handle default values cleanly.
*   **Boolean Expressions:** Simplify conditionals and use effective boolean logic to avoid deep nesting.

### 5. Error Handling & Robustness
*   **Failing Loudly:** Treat errors as values and fail loudly when unexpected states occur.
*   **Assertions and Pre-conditions:** Use `assert()` to enforce pre-conditions and validate data before processing.
*   **Safe Execution:** Use `pcall` and `xpcall` for robust error handling when executing potentially failing code.
