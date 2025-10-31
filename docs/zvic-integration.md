# ZVIC integration for CIDSEM

This document describes how CIDSEM uses ZVIC (Zero-Version Interface Contracts) to enforce runtime interface contracts and compatibility checks.

Summary
-------
- ZVIC is used to assert runtime contracts for critical modules in CIDSEM so incompatible changes are detected early (fail-fast).
- Current modules with runtime constraints enabled:
  - `src/cidsem/keys.py` — `E` entity: 256-bit CID invariants, 4-lane tuple input, lane-range checks (uint64).
  - `src/cidsem/cidstore.py` — `TripleRecord` / `CidstoreClient`: module-level runtime checks enabled.

Goals
-----
- Prevent silent data corruption due to incorrect CID shapes or lane overflow.
- Make interface requirements explicit and machine-checkable.
- Provide a low-friction path to add more constraints to other modules (plugins, NLP mappers, config loaders).

How constraints are enabled
--------------------------
In each constrained module we call `constrain_this_module()` at module import time. For example in `keys.py`:

```py
from zvic import constrain_this_module
constrain_this_module()
```

This enables ZVIC's runtime enforcement of any inline annotations and constraint expressions in that module.

Annotation examples used in CIDSEM
---------------------------------
- Constraining constructor and inputs:

```py
def __new__(
    cls,
    id_: "int[_ >= 0 and _ < (1 << 256)] | str | list[int][len(_) == 4] | tuple[int, ...][len(_) == 4] | None" = None,
) -> E:
    ...
```

- Constraining lane properties to uint64:

```py
@property
def high(self) -> "int[_ >= 0 and _ < (1 << 64)]":
    return (self >> 192) & ((1 << 64) - 1)
```

Where possible we use explicit numeric ranges to make the contract self-documenting.

Developer workflow
------------------
1. Keep `constrain_this_module()` enabled in development and CI. It helps catch mistakes early.
2. Write constraints that are clear and minimal. Prefer range checks, length checks, and simple predicate expressions.
3. If a module must avoid the runtime overhead in production, gate `constrain_this_module()` behind an environment variable (example below).

Disabling constraints in production (optional)
-------------------------------------------
To avoid runtime overhead in latency-sensitive production, you can gate the call:

```py
import os
from zvic import constrain_this_module

if os.getenv("CIDSEM_ZVIC_ENABLED", "1") == "1":
    constrain_this_module()
```

Testing and compatibility checks
--------------------------------
- Unit tests exercise the runtime constraints automatically when modules are imported during tests.
- We added an optional compatibility test harness (under `tests/compatibility/`) that uses ZVIC's `is_compatible()` tooling to compare current APIs against frozen snapshots. These tests are intentionally skipped by default while you iterate rapidly; enable them in CI for stronger guarantees.

CI configuration
----------------
We provide a ready-to-run GitHub Actions workflow at `.github/workflows/compatibility.yml` which runs the compatibility tests (uses Python 3.12 and installs `zvic`). Enable or adapt it for your CI environment if you want automated contract checks on push/PR.

How to add new constraints
--------------------------
1. Add `from zvic import constrain_this_module` and call `constrain_this_module()` near the top of the module.
2. Add ZVIC-style annotations to the functions/classes you want to protect. Use explicit predicates where appropriate.
3. Run the test suite locally. Fix any failures triggered by new constraints.

Notes and cautions
------------------
- ZVIC evaluates some annotation expressions at runtime; when evaluating untrusted code, prefer running ZVIC in an isolated worker or CI job.
- Keep constraint expressions simple and deterministic to avoid surprising runtime evaluation behavior.

Resources
---------
- ZVIC documentation (internal): `pip install zvic` then consult runtime help and examples.

Contact
-------
If you want me to expand these docs with examples for plugin interfaces or to add CI jobs that run the compatibility checks, tell me which CI provider you prefer (GitHub Actions, Azure Pipelines, etc.) and I will add a ready-to-run configuration.
