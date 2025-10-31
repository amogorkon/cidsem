## Validation decision pseudocode

This document contains pseudocode describing how validation decisions are made.

```text
# decide whether to accept a validation event
if event.payload is invalid:
    return reject
if event.confidence < threshold:
    return reject
return accept
```

This file is intentionally minimal for test coverage.
