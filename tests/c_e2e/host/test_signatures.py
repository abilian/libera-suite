"""Signatures in the editor, in a real browser: a signed document's
signatures shown as it opens, and the document read-only; removed, editable
again; a certificate chosen in the bridge's panel, and a document signed
with it (host/signing.py, bridge-desktop.js)."""

from __future__ import annotations

import pytest
from support import ScriptedShell
from support.keys import PASSPHRASE, SIGNER, make_pkcs12
from support.protected import make_protected, open_in

from libera.host import apps, hooks, saving, session as sessions, signing

SIGNATURES = "Asc.editor.asc_getSignatures().length"


@pytest.fixture
def plain(tmp_path):
    return make_protected(apps.WORDS, "docx", tmp_path / "made", password="")


@pytest.fixture
def signed(plain, tmp_path):
    """The document, signed by the host before the editor opens it."""
    signer = open_in(apps.WORDS, plain, tmp_path / "signer")
    if not signer.layout.sign.is_file():
        pytest.skip("this payload has no libera-sign (core 0190)")
    chosen = signing.choose_certificate(
        signer, make_pkcs12(tmp_path / "keys"), None, PASSPHRASE
    )
    signing.sign(signer, chosen.id, "", ("", ""))
    sessions.SESSIONS.clear()
    return plain


def test_a_signed_document_shows_its_signature_and_is_read_only(editor_with, signed):
    editor = editor_with([], document=signed)

    assert editor.frame.evaluate("() => Asc.editor.asc_isSignaturesSupport()")
    editor.frame.wait_for_function(f"() => ({SIGNATURES}) === 1")
    found = editor.frame.evaluate(
        "() => { const s = Asc.editor.asc_getSignatures()[0];"
        " return [s.asc_getValid(), s.asc_getSigner1()]; }"
    )
    assert found == [0, SIGNER]
    # Read-only, as any signed document is: OnlySignatures, which the editor
    # sets itself from the list it was sent.
    assert editor.frame.evaluate("() => Asc.editor.isRestrictionSignatures()")


def test_removing_the_signatures_makes_it_editable(editor_with, signed):
    editor = editor_with([], document=signed)
    editor.frame.wait_for_function(f"() => ({SIGNATURES}) === 1")

    with editor.answered("remove-signature"):
        editor.frame.evaluate("() => Asc.editor.asc_RemoveAllSignatures()")

    editor.frame.wait_for_function(f"() => ({SIGNATURES}) === 0")
    assert not editor.frame.evaluate("() => Asc.editor.isRestrictionSignatures()")
    assert not saving.is_signed(signed)


def test_a_certificate_chosen_in_the_panel_signs(
    editor_with, plain, tmp_path, monkeypatch
):
    """The panel's files come from the host's open dialog, stood in for
    here; its passphrase goes to the host, which loads the key and keeps it
    for the window, and the editor gets the signer back."""
    key = make_pkcs12(tmp_path / "keys")
    editor = editor_with([], document=plain)
    if not next(iter(sessions.SESSIONS.values())).layout.sign.is_file():
        pytest.skip("this payload has no libera-sign (core 0190)")
    monkeypatch.setattr(
        hooks, "shell", ScriptedShell(choose_open_path=lambda _kind: str(key))
    )
    editor.frame.evaluate(
        "() => { window.__chosen = null; Asc.editor.asc_registerCallback("
        "'on_signature_selectsertificate_ret', (c) => { window.__chosen = c; }); }"
    )

    editor.frame.evaluate("() => window.AscDesktopEditor.SelectCertificate()")
    top = editor.page
    with editor.answered("choose-file"):
        top.click("[data-choose='key']")
    top.fill(".libera-panel input[type=password]", "not it")
    with editor.answered("certificate") as refused:
        top.click(".libera-panel button:has-text('OK')")
    assert refused.value.status == 403
    assert top.locator(".libera-panel [role=alert]").inner_text()

    top.fill(".libera-panel input[type=password]", PASSPHRASE)
    with editor.answered("certificate") as taken:
        top.click(".libera-panel button:has-text('OK')")
    assert taken.value.status == 200
    editor.frame.wait_for_function("() => window.__chosen !== null")
    chosen = editor.frame.evaluate("() => window.__chosen")
    assert chosen["name"] == SIGNER
    assert top.locator(".libera-panel").count() == 0

    with editor.answered("sign"):
        editor.frame.evaluate("(id) => Asc.editor.asc_Sign(id)", chosen["id"])
    editor.frame.wait_for_function(f"() => ({SIGNATURES}) === 1")
    assert saving.is_signed(plain)
    assert not [line for line in editor.console if PASSPHRASE in line]
