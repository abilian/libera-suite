"""Write the installer's file associations, from the editors' own list.

    python build/windows/associations.py OUT.iss

src/libera/host/apps.py says which extensions each editor opens, and it is
the only place that does: the Linux desktop entry is checked against it, and
this is generated from it, so an extension added there reaches the Windows
installer with nothing else to edit.

What it registers, all per-user (HKA is HKCU in a non-administrative install):

  a ProgID per editor, `LiberaSuite.Words` and so on, whose open command is
      Libera.exe "%1";
  each extension's OpenWithProgids, which puts Libera Suite in Explorer's
      "Open with" for that type without taking it from whatever has it;
  Capabilities and RegisteredApplications, which is what lists Libera Suite
      in Settings > Default apps, where a user can make it the default.

Windows no longer lets an installer make itself the default handler for a
type: that choice belongs to the user, and the two places above are where
they make it.
"""

from __future__ import annotations

import sys
from pathlib import Path

from libera.host import apps

CAPABILITIES = r"Software\Abilian\Libera Suite\Capabilities"


def progid(app: apps.App) -> str:
    return f"LiberaSuite.{app.name.capitalize()}"


def lines() -> list[str]:
    out = ["[Registry]"]

    def add(key: str, name: str | None, value: str, flags: str = "") -> None:
        value_name = f'ValueName: "{name}"; ' if name is not None else ""
        extra = f"; Flags: {flags}" if flags else ""
        # Inno Setup quotes a parameter in double quotes and escapes one inside
        # by doubling it, which the open commands need: "C:\...\Libera.exe" "%1".
        quoted = value.replace('"', '""')
        out.append(
            f'Root: HKA; Subkey: "{key}"; {value_name}ValueType: string; '
            f'ValueData: "{quoted}"{extra}'
        )

    classes = r"Software\Classes"
    for app in apps.ALL:
        pid = progid(app)
        add(rf"{classes}\{pid}", "", f"{app.title} {app.noun}", "uninsdeletekey")
        add(rf"{classes}\{pid}\DefaultIcon", "", r"{app}\Libera.exe,0")
        add(
            rf"{classes}\{pid}\shell\open\command",
            "",
            r'"{app}\Libera.exe" "%1"',
        )
        for ext in sorted(app.opens):
            add(
                rf"{classes}\.{ext}\OpenWithProgids",
                pid,
                "",
                "uninsdeletevalue",
            )
            add(rf"{CAPABILITIES}\FileAssociations", f".{ext}", pid)

    # The application itself, for "Open with > Choose another app".
    application = rf"{classes}\Applications\Libera.exe"
    add(application, "FriendlyAppName", "Libera Suite", "uninsdeletekey")
    add(rf"{application}\shell\open\command", "", r'"{app}\Libera.exe" "%1"')
    for app in apps.ALL:
        for ext in sorted(app.opens):
            add(rf"{application}\SupportedTypes", f".{ext}", "")

    add(CAPABILITIES, "ApplicationName", "Libera Suite", "uninsdeletekey")
    add(
        CAPABILITIES,
        "ApplicationDescription",
        "Documents, spreadsheets and presentations, on your own computer.",
    )
    add(
        r"Software\RegisteredApplications",
        "Libera Suite",
        CAPABILITIES,
        "uninsdeletevalue",
    )
    # The vendor key the Capabilities live under, removed with them.
    out.append(
        r'Root: HKA; Subkey: "Software\Abilian\Libera Suite"; '
        "Flags: uninsdeletekeyifempty"
    )
    return out


if __name__ == "__main__":
    Path(sys.argv[1]).write_text("\n".join(lines()) + "\n", encoding="utf-8")
