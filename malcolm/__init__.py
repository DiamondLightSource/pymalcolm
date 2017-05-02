# Add a do nothing handler to stop "No handlers could be found for " messages.
# This is attached to the top level name, it will propagate down.
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())
