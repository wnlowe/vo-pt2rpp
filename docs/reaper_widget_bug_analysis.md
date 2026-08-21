# ReaperWidget — `_register_reaper` Loop / Stuck-Button Bug Analysis

## Summary

When `_register_reaper(True)` runs, the "Verify" button can either loop
indefinitely (repeated "close REAPER" prompts) or get stuck permanently
disabled on "Verifying...". There are several compounding bugs behind this,
traced below.

---

## Bug 1: `verify_configuration(v)` never uses `v`

```python
def verify_configuration(self, v = True):
    ...
    result = self._check_ready()
```

`v` is accepted but completely ignored. So this call:

```python
self._check_reaper_state(0, self.verify_configuration, True)
```

calls `verify_configuration(True)` on success **and**
`verify_configuration(False)` on timeout (30s of no REAPER launch) —
identical behavior either way. There's no "give up and reset the button"
path; both outcomes just re-run the whole check from scratch.

---

## Bug 2: The real loop — dist API isn't ready the instant REAPER launches

Trace the "happy path" after you register:

1. `_register_reaper(True)` configures reapy, shows a "start REAPER now"
   dialog, then polls for the process to appear.
2. Process appears → `on_complete(True)` → `verify_configuration(True)`
   re-runs.
3. `_check_ready()` calls `_check_reapy()` first — but REAPER's dist-API
   host script usually isn't listening yet the *instant* the process
   spawns (it needs the app to finish loading and run the startup action).
   `_check_reapy()` fails.
4. Since the process *is* running, `_check_ready()` falls through to
   `return 1`.
5. That triggers `_need_restart()` — **asking the user to close REAPER
   right after telling them to open it.**
6. If the user clicks OK without closing it (why would they — you just
   said to open it), this branch fires:

```python
case QMessageBox.StandardButton.Ok:
    if any("reaper" in ... for p in psutil.process_iter(["name"])):
        self._need_restart()   # <-- recurses with no delay/limit
        return
```

Since REAPER is (correctly) still running, this recurses into itself —
same dialog, forever. That's the loop.

---

## Bug 3: The "stuck disabled forever" case

Two separate ways this happens:

### a) Unhandled exception in `_register_reaper`

```python
reapy.configure_reaper(resource_path=resource_path)
```

has no try/except. If it throws (bad path, reapy version mismatch,
permissions, REAPER not fully initialized yet, etc.), the exception is
swallowed by Qt's slot machinery (since this runs inside a
`QTimer.singleShot` callback via `guard.run_after`), gets printed to
stderr, and execution just stops. Nothing re-enables the button — it's
stuck on "Verifying...".

### b) `self._reaper_timer` gets clobbered

```python
def _close_reaper(self, pid: int):
    ...
    self._check_reaper_state(0, self._register_reaper)
```

called from inside a loop in `_need_restart`:

```python
for p in psutil.process_iter(["name", "pid"]):
    if "reaper" in (p.info.get("name") or "").lower():
        self._close_reaper(p.info["pid"])
```

If REAPER shows up as more than one process (main process +
helper/watchdog — common on some platforms), `_close_reaper` runs
multiple times, and each call overwrites `self._reaper_timer` with a new
`QTimer`. The previous `QTimer` object loses its last Python reference
and can be garbage-collected before it ever fires — so that polling chain
silently dies without ever calling `on_complete`. No callback → button
never re-enabled.

---

## Fixes

### 1. Add a genuine retry/backoff for the dist-API check instead of falling straight to "needs restart"

```python
def _check_ready(self, allow_retry: bool = True) -> int:
    import psutil
    if self._check_reapy():
        return 0
    reaper_running = any("reaper" in (p.info.get("name") or "").lower()
                          for p in psutil.process_iter(["name"]))
    if reaper_running and allow_retry:
        # dist API may just not be up yet — give it a moment before assuming failure
        for _ in range(5):
            time.sleep(1)
            if self._check_reapy():
                return 0
    if reaper_running:
        return 1
    return 2
```

### 2. Differentiate success vs. timeout instead of both calling `verify_configuration`

```python
self._check_reaper_state(
    0,
    lambda ok: self.verify_configuration() if ok else self._registration_failed(),
    True
)

def _registration_failed(self):
    QMessageBox.warning(self, "REAPER didn't start",
                         "Timed out waiting for REAPER to launch. Try again.")
    self._rerun()
```

### 3. Cap `_need_restart`'s recursion and don't loop silently

```python
def _need_restart(self, attempt: int = 0):
    if attempt > 3:
        QMessageBox.warning(self, "Still running", "REAPER is still open — cancelling verification.")
        self._rerun()
        return
    ...
    case QMessageBox.StandardButton.Ok:
        if any(...):
            self._need_restart(attempt + 1)
            return
```

### 4. Wrap the risky reapy call so failures always re-enable the button

```python
def _register_reaper(self, reaper_closed: bool):
    if not reaper_closed:
        self._rerun()
        return
    try:
        resource_path = self.configuration_selector.currentText()
        reapy.configure_reaper(resource_path=resource_path)
    except Exception as e:
        QMessageBox.critical(self, "Registration failed", str(e))
        self._rerun()
        return
    ...
```

### 5. Stop clobbering the timer — don't call `_close_reaper` per-process, gather PIDs once and poll independently

```python
def _need_restart(self, attempt: int = 0):
    ...
    case QMessageBox.StandardButton.Close:
        import psutil
        pids = [p.info["pid"] for p in psutil.process_iter(["name", "pid"])
                if "reaper" in (p.info.get("name") or "").lower()]
        for pid in pids:
            self._close_reaper(pid)          # just kill, no per-pid polling
        self._check_reaper_state(0, self._register_reaper)  # poll once, after all kills issued
```

---

## Priority

The two highest-priority fixes for the reported symptoms:

- **Fix #1** — retry the dist-API check before deciding REAPER "needs to close" (addresses the infinite loop).
- **Fix #4** — wrap `configure_reaper` in try/except so an exception can't strand the button (addresses the permanently-disabled button).

Those two alone would likely resolve both symptoms described.
