"""PyInstaller entry point: runs the ims package like `python -m ims`."""

import sys

from ims.__main__ import main

sys.exit(main())
