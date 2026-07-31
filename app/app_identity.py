"""Set the name macOS shows for the running app (Dock tooltip, app menu).

A plain `python word_canvas_app.py` registers with the Dock as "Python",
because that is the CFBundleName of the Python framework bundle it runs from.
Tk has no API for this — the name has to be patched into the bundle's info
dictionary via the Objective-C bridge.

Timing matters: call this BEFORE the first Tk() call. The Dock reads the name
when the process registers, which Tk triggers on initialization; patching it
afterwards leaves the tooltip stale.

Everything here degrades to a no-op off macOS or without pyobjc installed.
"""
import sys


def set_app_name(name: str) -> bool:
    """True if the name was applied, False if unsupported on this platform."""
    if sys.platform != "darwin":
        return False
    try:
        from Foundation import NSBundle
    except ImportError:
        return False

    try:
        bundle = NSBundle.mainBundle()
        info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
        if info is None:
            return False
        info["CFBundleName"] = name
        info["CFBundleDisplayName"] = name
        return True
    except Exception as e:  # cosmetic only — never block startup over it
        print(f"Nome do app não aplicado: {e}")
        return False
