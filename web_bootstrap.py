# title: riverside
# author: toytoytoy330
# desc: Three-line 2.5D exploration prototype
# site: https://github.com/sejiseji/riverside
# license: MIT
# version: 0.1.0

from __future__ import annotations

import sys


if "src" not in sys.path:
    sys.path.insert(0, "src")

from three_line_explorer.app import main  # noqa: E402


main()
