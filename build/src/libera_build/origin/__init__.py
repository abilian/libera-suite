"""The CDN: the Flatpak bundles, the Windows installer and the install
scripts, which are what the CDN is for. Since 0.7 nothing downloads a payload
from it; pip installs the components from PyPI.

    place     where the CDN is, asked of the application itself
    cdn       one PUT per object, and what the CDN's answer means
    publish   extras, windows: what goes up, signed, in what order
    status    where a release has got to, here and on PyPI
"""
