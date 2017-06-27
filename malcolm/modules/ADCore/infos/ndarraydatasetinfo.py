from malcolm.core import Info


class NDArrayDatasetInfo(Info):
    """Declare the NDArray data this produces as being a useful dataset

     Args:
         rank (int): The rank of the data, e.g. 2 for a 2D detector
    """
    def __init__(self, rank):
        self.rank = rank
