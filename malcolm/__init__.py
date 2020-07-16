# Add a do nothing handler to stop "No handlers could be found for " messages.
# This is attached to the top level name, it will propagate down.
import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())

try:
    # In a release there will be a static version file written by setup.py
    from ._version_static import __version__
except ImportError:
    # Otherwise get the release number from git describe
    from ._version_git import __version__
