# Run this repository's own test suite on Linux.
#
# The payload is built in one container (build/docker/) and the Flatpak in
# another (build/flatpak/); neither of those runs a single test from tests/.
# This is the third, and it is the only place the host, the bridge and the
# editor are exercised on Linux at all -- everything else about this project is
# verified on a Mac.
#
# Small on purpose. It builds nothing: it takes a payload that was built
# elsewhere, installs it the way a user does, and runs pytest. The heavy image
# next door is pinned to a compiler and an APT snapshot because the artifact
# depends on them; nothing here ends up in an artifact.
#
# Debian trixie for python 3.13 -- libera wants >= 3.12, and this is also a
# version the Mac does not run, so the suite gets tried on two.
ARG BASE_DIGEST=sha256:d7e12182ce18b85b93007c1dedf31f2d29e01ccf3182cc4017c709b6259bc132
FROM debian:trixie-slim@${BASE_DIGEST}

ARG BASE_DIGEST
# The uv the Mac runs, so a lockfile resolved on one is resolved the same here.
ARG UV_VERSION=0.12.12

ENV DEBIAN_FRONTEND=noninteractive

# chromium from apt, not from `playwright install`: tests/c_e2e/conftest.py
# looks for a system browser first (shutil.which("chromium")) and only falls
# back to Playwright's download, so this saves fetching a second copy of
# Chromium on every run. Debian ships a real .deb; Ubuntu's is a snap stub,
# which is one reason this is not layered onto the build image.
#
# The GTK and WebKit packages are what pywebview asks for and what
# src/libera/gui.py checks -- so gui.why_no_window() is exercised here on a
# machine where the answer is supposed to be None. Xvfb because opening a real
# window needs a display, and a container has none.
#
# desktop-file-utils for one test: `libera --launcher-install` writes a
# freedesktop .desktop file, and a desktop file with a fault in it is not
# rejected by anything at run time -- the desktop silently ignores it and the
# application simply never appears in the launcher. desktop-file-validate is
# the only thing that says why, and the test skips where it is absent.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl git make \
        chromium \
        python3 python3-pip python3-venv python3-pil \
        python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1 \
        xvfb xauth x11-utils scrot \
        desktop-file-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir "uv==${UV_VERSION}"

# Chromium will not start as root, and pid 1 in a container is root: it exits
# immediately and the harness waits three minutes for a page that never loads.
# The symptom is a zombie -- `[chromium] <defunct>` -- and nothing in the log,
# because conftest sends the browser's stderr to DEVNULL.
#
# A wrapper rather than a change to tests/c_e2e/conftest.py: it looks for
# $CHROMIUM first and execs whatever it names, so the container can supply a
# browser that works in a container without the suite knowing it is in one.
#
# --disable-dev-shm-usage for the same class of reason: /dev/shm defaults to
# 64 MB here and Chromium falls over on it part-way through a large document.
RUN printf '%s\n' \
      '#!/bin/sh' \
      'exec /usr/bin/chromium --no-sandbox --disable-dev-shm-usage "$@"' \
      > /usr/local/bin/chromium-container \
    && chmod +x /usr/local/bin/chromium-container

# The virtualenv goes outside the repository. The repository is bind-mounted
# from the host, whose .venv holds macOS wheels -- `uv sync` into it would
# replace them with Linux ones and leave the Mac unable to run its own tests.
# UV_PYTHON, because .python-version says 3.12 and trixie has 3.13: without it
# every uv command prints "Using incompatible environment". It must be the
# system interpreter in any case -- see build/test-linux.sh on PyGObject.
ENV CHROMIUM=/usr/local/bin/chromium-container \
    UV_PROJECT_ENVIRONMENT=/venv \
    UV_PYTHON=/usr/bin/python3 \
    UV_LINK_MODE=copy \
    PLAYWRIGHT_BROWSERS_PATH=/venv/playwright

RUN { \
      echo "base:     debian:trixie-slim@${BASE_DIGEST}"; \
      echo "python:   $(python3 --version)"; \
      echo "uv:       $(uv --version)"; \
      echo "chromium: $(chromium --version 2>/dev/null || echo unknown)"; \
    } > /etc/libera-test-image.txt

ENTRYPOINT ["/bin/sh"]
