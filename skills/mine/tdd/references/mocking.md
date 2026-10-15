# Seams and Mocking Guide

## 1. What is a Seam?
A **seam** is any place where you can alter behavior without editing the code inside.
In automated testing, seams are the boundaries where your tests attach:
- **Public Functions:** The API of a library module.
- **Service Interfaces:** Classes that take dependencies in `__init__`.
- **CLI Commands:** The arguments and exit codes of a tool.

## 2. Rules for Seams
1. **Never test internal functions.** If a function begins with `_` or is not exported in `__all__`, test it through the caller that uses it.
2. **If internal logic is hard to test through the seam, the seam is poorly designed.** Split the module into smaller, cohesive units rather than testing private methods.

## 3. When to Mock
Mock **only at system boundaries**:
- External network APIs
- Database services (unless using a real in-process/in-memory test instance)
- System clock / timestamps
- Hardware / OS services (OS Keyring, DBus, system notifications)

Do **NOT** mock:
- Your own business logic classes
- Data transfer objects or Pydantic models
- Internal helpers or sibling modules in the same package
