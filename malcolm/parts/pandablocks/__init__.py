try:
    from .pandablockschildpart import PandABlocksChildPart
    from .pandablocksdriverpart import PandABlocksDriverPart
except ImportError:
    import logging
    logging.warning("Can't import some PandABlocks Parts", exc_info=True)
