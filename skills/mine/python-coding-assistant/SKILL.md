---
name: python-coding-assistant
description: >-
  Use this skill when writing, reviewing, or refactoring Python code.
  Enforces strict typing (mypy --strict), Ruff linting, Pydantic validation,
  tenacity resilience, structured error handling, and design patterns.
---

# Python Coding Assistant

Standard operating procedures and engineering guidelines for writing production-grade Python code.

## Workflow

1. **Review Guidelines**: Check the core principles below before modifying or creating Python modules.
2. **Type Safety & Schemas**: Define types first. Use type annotations for all signatures and Pydantic/dataclasses for state.
3. **Resilience & Timeouts**: Ensure every network and filesystem call has an explicit timeout and retry policy where appropriate.
4. **Validation**: Run `ruff check`, `ruff format --check`, and `mypy --strict` on all modified files.

---

## Core Guidelines

### 1. Code Quality & Typing
- **Strict Typing:** Annotate all function parameters and return types. Verify with `mypy --strict`.
- **Data Validation:** Model API payloads, configurations, and internal state using Pydantic `BaseModel` or `@dataclass(frozen=True, slots=True)`. Avoid raw unstructured dicts across boundaries.
- **Type Narrowing:** Use explicit `isinstance` checks and `typing.TypeGuard` or `typing.cast` (sparingly) for dynamic inputs.
- **Linting & Formatting:** Use `ruff` for linting and formatting. Run `ruff check --fix` and `ruff format`.

### 2. Error Handling & Observability
- **Never Fail Silently:** Do not use bare `except:` or `except Exception: pass`. Always catch specific exceptions or log the traceback.
- **Exception Hierarchy:** Define a base project exception (e.g. `AppError(Exception)`) and domain-specific subclasses (e.g. `RateLimitExceededError`, `ResourceNotFoundError`).
- **Structured Logging:** Use structured log records or standard `logging.getLogger(__name__)`. Include identifiers like `repo_name`, `user_id`, or `request_id` in log context.
- **Graceful Shutdowns:** Trap `SIGINT` and `SIGTERM` in long-running processes or CLI tools to clean up sockets and temporary files.

### 3. Resilience & Network Calls
- **Explicit Timeouts:** Never call `httpx`, `requests`, or socket operations without a timeout (e.g., `timeout=10.0`).
- **Retries with Jitter:** Wrap flaky external endpoints or rate-limited APIs with `tenacity` retries using exponential backoff and randomized jitter.
- **Rate Limit Awareness:** Respect HTTP 429 and `Retry-After` headers. Drain queues safely when rate limited.

### 4. Design Patterns & Concurrency
- **Dependency Injection:** Pass clients, configuration, and loggers into functions and classes rather than relying on global singletons.
- **Async I/O Discipline:** When using `asyncio`, never run blocking synchronous I/O in the event loop. Offload CPU-bound or blocking calls to `asyncio.to_thread`.
- **Idempotency:** Design data ingestion, batch jobs, and mutations so re-running them produces the same outcome without duplication.

### 5. Anti-Patterns to Avoid
- **Mutable Defaults:** Never use `def func(items=[])`. Use `def func(items: list[str] | None = None)`.
- **Global Mutable State:** Avoid module-level shared mutable objects.
- **Hardcoded Configs:** Do not embed credentials, tokens, or filesystem paths inside application logic. Read from environment variables, CLI arguments, or configuration classes.
