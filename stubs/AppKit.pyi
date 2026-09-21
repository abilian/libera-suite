from typing import Any

# Built from the Objective-C runtime at import time. Listed, not described:
# what matters is that the name exists, not what it is.
NSAlert: Any
NSAlertStyleWarning: Any
NSApp: Any
NSBeep: Any
NSFileHandlingPanelOKButton: Any
NSMenu: Any
NSMenuItem: Any
NSObject: Any
NSPopUpButton: Any
NSSavePanel: Any
NSTextField: Any
NSView: Any
NSWindow: Any
NSWindowStyleMaskFullScreen: Any

def __getattr__(name: str) -> Any: ...
