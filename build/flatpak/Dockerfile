# Somewhere to run flatpak-builder from a Mac.
#
# flatpak-builder is an ordinary Linux program and runs in a container. What it
# needs is user namespaces (bubblewrap builds each module inside one) and
# /dev/fuse (flatpak's installer mounts revokefs over it). Docker Desktop grants
# both with --privileged --device /dev/fuse; build/flatpak.sh passes them.
#
# The base is pinned by digest, like build/docker/Dockerfile. The apt packages
# are deliberately *not* snapshot-pinned the way that image's are: nothing this
# container installs ends up in the artifact. flatpak-builder assembles wheels
# and metadata into a runtime built by somebody else, and what decides the
# result is the runtime version -- pinned in the manifest, not here.
#
# **Bookworm, not trixie, and that is not staleness.** flatpak-builder validates
# every icon it exports by loading it through gdk-pixbuf, and gdk-pixbuf reads
# SVG only through librsvg's loader plugin -- which librsvg removed in 2.58, so
# trixie's librsvg2-common no longer ships libpixbufloader-svg.so. On trixie an
# otherwise clean build dies at the final step with
#
#     is not a valid icon: Format not recognized
#
# naming neither the package nor the fact that the icon is fine. Moving this to
# trixie means rasterising the icon to PNG first. The check below is here so
# that a future bump fails at image-build time saying why, instead of an hour
# later at the export.
ARG BASE_DIGEST=sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171
FROM debian:bookworm-slim@${BASE_DIGEST}

# Re-declared: an ARG from before FROM is out of scope after it, and the only
# symptom is an empty value -- `build/flatpak.sh versions` printed
# "debian:bookworm-slim@" and nothing else. build/docker/Dockerfile has the
# same line for the same reason.
ARG BASE_DIGEST

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        flatpak flatpak-builder ca-certificates \
        librsvg2-common \
        python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN ls /usr/lib/*/gdk-pixbuf-2.0/2.10.0/loaders/ | grep -q 'libpixbufloader-svg' \
    || { echo "FATAL: no gdk-pixbuf SVG loader in this base; icon export will fail" >&2; exit 1; }

# What this image is, for the record. build/flatpak.sh versions prints it.
RUN { \
      echo "base:            debian:bookworm-slim@${BASE_DIGEST}"; \
      echo "flatpak:         $(flatpak --version)"; \
      echo "flatpak-builder: $(flatpak-builder --version)"; \
      echo "python:          $(python3 --version)"; \
    } > /etc/libera-flatpak-image.txt

ENTRYPOINT ["/bin/sh"]
