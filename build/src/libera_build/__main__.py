"""`python3 -m libera_build`: the same as `lb`, for where it is not installed.

The builders run the tooling with their own python3, outside any virtualenv,
so the `lb` console script is not there; `lb release check` runs this instead, with
build/src and src on PYTHONPATH.
"""

from __future__ import annotations

import sys

from libera_build.cli import main

sys.exit(main())
