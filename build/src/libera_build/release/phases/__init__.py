"""The work of each phase, grouped by where it runs.

update      sends this commit to every builder
builders    build and bundles: `lb` on the builders, in parallel
here        native and wheel: on this machine
publishing  publish and verify: PyPI, then the bundles on the CDN
"""
