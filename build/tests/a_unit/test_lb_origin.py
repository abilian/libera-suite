"""The origin's rules: where it is, what an upload is called and answered,
what a check compares, and what to do next."""

from __future__ import annotations

import io
import json

import pytest
from libera_build.inventory import Builder
from libera_build.origin import cdn, check, collect, place, publish, status
from libera_build.report import RefusedError

from libera.manifest import Artifact, Manifest

ORIGIN = place.Origin("https://cdn.example", "libera", "0.4")


def test_the_origin_splits_into_host_and_zone():
    assert place.split_origin("https://cdn.example/libera") == (
        "https://cdn.example",
        "libera",
    )
    with pytest.raises(RefusedError, match="no zone"):
        place.split_origin("https://cdn.example/")


def test_an_object_is_read_and_written_at_two_urls():
    assert ORIGIN.base == "https://cdn.example/libera/0.4"
    assert ORIGIN.api("0.4/x.tar.gz") == (
        "https://cdn.example/_/api/v1/zones/libera/objects/0.4/x.tar.gz"
    )


def test_the_zone_root_has_no_empty_directory():
    assert cdn.key_for("", "install.sh") == "install.sh"
    assert cdn.key_for("bundles", "latest") == "bundles/latest"


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("core-linux-arm64.tar.gz", "application/gzip"),
        ("manifest.json", "application/json"),
        ("install.sh", "text/plain; charset=utf-8"),
        ("libera-0.3.3-amd64.flatpak.asc", "text/plain; charset=utf-8"),
        ("latest-windows", "text/plain; charset=utf-8"),
        ("libera-0.3.3-amd64.flatpak", "application/vnd.flatpak"),
        ("Libera-Suite-Setup.exe", "application/vnd.microsoft.portable-executable"),
        ("other", "application/octet-stream"),
    ],
)
def test_each_object_gets_its_content_type(name, kind):
    assert cdn.content_type(name) == kind


@pytest.mark.parametrize(
    ("status_", "body", "says"),
    [
        (404, "{}", "no zone called 'libera'"),
        (401, "{}", "token was refused (401)"),
        (500, "oops", "500: oops"),
        (201, '{"size": 9}', "sent 10 bytes, the CDN stored 9"),
        (201, "not json", "the CDN stored nothing"),
    ],
)
def test_the_cdns_answer_is_believed_only_when_it_stored_it_all(status_, body, says):
    assert says in cdn.answer_problem(status_, body, sent=10, zone="libera")


def test_a_whole_upload_is_no_problem():
    assert cdn.answer_problem(201, '{"size": 10}', sent=10, zone="libera") is None


MANIFEST = Manifest(
    "0.4",
    (
        Artifact("core-linux-arm64.tar.gz", "core", "linux-arm64", 68, "a" * 64),
        Artifact("fonts-core.tar.gz", "fonts", None, 4, "b" * 64),
    ),
)


def test_push_goes_smallest_first_and_the_manifest_last():
    assert publish.upload_order(MANIFEST) == [
        "fonts-core.tar.gz",
        "core-linux-arm64.tar.gz",
        "manifest.json",
    ]


def test_a_check_wants_every_artifact_then_the_manifest():
    names = [w.name for w in check.wanted(MANIFEST)]
    assert names == ["core-linux-arm64.tar.gz", "fonts-core.tar.gz", "manifest.json"]


def test_a_check_says_what_it_compared():
    core, _, man = check.wanted(MANIFEST)
    assert check.verdict(core, 68, "a" * 64) == (True, "size and sha256 ok")
    assert check.verdict(core, 68, None) == (True, "size ok")
    assert check.verdict(man, 123, "f" * 64) == (True, "present")
    ok, note = check.verdict(core, 67, "c" * 64)
    assert not ok
    assert "67 bytes" in note
    assert "sha256 cccccccccccc" in note


def test_the_shared_pair_comes_from_the_neutral_builder_else_the_first():
    a = Builder("linux-x86_64", "x", None, False, "~/r")
    b = Builder("macos-arm64", "local", None, True, "~/r")
    assert collect.neutral_of([a, b]) is b
    assert collect.neutral_of([a]) is a
    with pytest.raises(RefusedError):
        collect.neutral_of([])


def test_status_names_one_command_per_machine_and_then_collect():
    lines = status.next_steps(["core-linux-arm64", "editors", "core-macos-arm64"])
    assert lines[0] == "not here yet: core-linux-arm64 editors core-macos-arm64"
    assert sum("lb payload dist" in line for line in lines) == 1
    assert any("--arch arm64" in line for line in lines)
    assert not any("x86_64 box" in line for line in lines)
    assert lines[-1].endswith("lb release collect")
    assert status.next_steps([])[0].startswith("every core is here")
    (_, windows, _) = status.next_steps(["core-windows-x86_64"])
    assert windows.endswith("lb payload all")


def test_status_reads_the_project_from_pypi_and_says_what_is_yanked(monkeypatch):
    """Offline: the URL opened, and what is made of the answer. It once opened
    the per-version template unformatted, `{version}` and all, got a 404, and
    told a finished release to start over."""
    opened = []

    def urlopen(url, timeout):
        opened.append(url)
        return io.BytesIO(
            json.dumps({
                "info": {"version": "0.3.3"},
                "releases": {
                    "0.3.1": [{"yanked": True}],
                    "0.3.3": [{"yanked": False}],
                    "0.4.0rc1": [{"yanked": False}],
                },
            }).encode()
        )

    monkeypatch.setattr(status.urllib.request, "urlopen", urlopen)
    assert status.pypi_summary() == (
        "latest 0.3.3; published 0.3.3, 0.4.0rc1; yanked 0.3.1"
    )
    assert opened == ["https://pypi.org/pypi/libera/json"]
