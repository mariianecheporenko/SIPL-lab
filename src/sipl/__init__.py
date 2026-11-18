"""SIPL language toolkit."""

from importlib import metadata

try:
    __version__ = metadata.version("sipl-toolkit-knu")
except metadata.PackageNotFoundError:  # running from a source checkout
    __version__ = "0+unknown"
