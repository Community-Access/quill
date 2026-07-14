# Table Studio on macOS: the NSAccessibility bridge (design spike)

> Preserved from the retired Table Studio prototype folder (2026-07-05) when
> the prototype scratch (`docs/prototypes/`, gitignored) was deleted after the
> feature shipped (PRD §5.4.14; native Windows UIA provider in
> `quill/native/table_uia/`). This is the only design material that had no
> other home: the plan for giving VoiceOver real grid semantics when Table
> Studio comes to macOS. The cross-platform principle at the bottom is the
> contract the shipped Windows bridge already follows.

## Status: Spike design / not yet built

## What this will do

Expose the `wx.grid.Grid` widget as a proper `NSAccessibilityGrid` element
so that VoiceOver can navigate cells, read row/column headers, and hear
editability state — without the Python `wx.Accessible` approximation.

## Implementation strategy

### Option A: Objective-C++ extension (recommended)

Build a small `.so` using the CPython C API (or pybind11) that:

1. Receives the `NSView*` handle of the wxMac grid window via
   `grid.GetHandle()` cast through `NSView*`.
2. Subclasses `NSObject` and declares it as the grid's
   `accessibilityOverrideValue:forAttribute:` delegate.
3. Implements the required NSAccessibility protocol methods:
   - `NSAccessibilityRoleAttribute`  → `NSAccessibilityGridRole`
   - `NSAccessibilityRowsAttribute`  → virtual row elements
   - `NSAccessibilityColumnsAttribute` → virtual column elements
   - `NSAccessibilitySelectedRowsAttribute`
   - `NSAccessibilityFocusedAttribute`
4. For each virtual cell: `NSAccessibilityCellRole`,
   `NSAccessibilityRowIndexRangeAttribute`,
   `NSAccessibilityColumnIndexRangeAttribute`,
   `NSAccessibilityValueAttribute`,
   `NSAccessibilityEnabledAttribute`.
5. Uses the same `TableCallbacks`-style pattern as the Windows UIA bridge
   so the Python model is never duplicated.

### Option B: PyObjC bridge

Use `objc.lookUpClass("NSObject")` and the PyObjC runtime to implement
the protocol methods in Python.  Avoids a compilation step but adds a
PyObjC dependency and may have thread-safety complications.

### Option C: wxWidgets built-in

Evaluate whether `wxGTK`/`wxMac` exposes adequate `NSAccessibility`
coverage for `wx.grid.Grid` out of the box.  If it reliably reports
`NSAccessibilityGridRole` with correct row/column relationships, the
native bridge may not be needed for an initial macOS release.
The `wx.Accessible` Python fallback must still be available as a safety net.

## Testing

Test with VoiceOver (VO+F3 for item chooser, VO+Right to navigate cells)
and `Accessibility Inspector.app`.

Key VoiceOver behaviors to verify:
- VO announces "Grid, N rows, M columns" on entry.
- VO announces column header on horizontal movement.
- VO announces row header on vertical movement.
- VO correctly says "blank" for empty cells.
- VO enters and exits edit mode on VO+Space.
- Braille display shows row/col coordinates.

## Build

```
# Requires Xcode Command Line Tools + Python headers
clang++ -std=c++17 -arch x86_64 -arch arm64 \   # universal binary
    -I$(python3 -c 'import sysconfig; print(sysconfig.get_path("include"))') \
    -dynamiclib -undefined dynamic_lookup \o _quill_table_nsaccess.so \
    macos_table_provider.mm python_bridge_mac.cpp
```

## Cross-platform principle

The `TableDocumentModel` and `TableController` are identical on all platforms.
Only this bridge (and the Windows UIA bridge) need to be rebuilt per OS.
The `accessibility.py` module selects the right provider at runtime:

```python
if sys.platform == "darwin":
    try:
        import _quill_table_nsaccess
        _native_mac = _quill_table_nsaccess
    except ImportError:
        _native_mac = None   # fall back to wx.Accessible
```
