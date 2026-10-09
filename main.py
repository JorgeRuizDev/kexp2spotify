"""Console entry point compatibility wrapper."""

import sys

from kexp2spotify.cli import main

if __name__ == "__main__":
    sys.exit(main())
