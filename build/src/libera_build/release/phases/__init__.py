"""The work of each phase, grouped by where it runs.

update      sends this commit to every builder
builders    bundles: `lb` on the builders, in parallel
components  libera-core's wheel on each builder, libera-web here
here        wheel: on this machine
staging     stage, and publish's refusal of anything it did not stamp
publishing  publish and verify: PyPI, then the bundles on the CDN
"""
