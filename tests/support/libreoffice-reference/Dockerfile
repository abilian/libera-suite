# LibreOffice as the reference for OOXML signatures: Debian's own packages,
# the core without a window, its Python bridge, and NSS's tools for the key
# store it signs from. See tests/support/libreoffice.py.
FROM docker.io/library/debian:trixie-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libreoffice-core-nogui python3-uno libnss3-tools \
 && rm -rf /var/lib/apt/lists/*
