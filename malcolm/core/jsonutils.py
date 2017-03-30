import json

import numpy as np

from malcolm.core.serializable import serialize_object
from malcolm.compat import OrderedDict


def json_encode(o, indent=None):
    s = json.dumps(o, default=serialize_hook, indent=indent)
    return s


def json_decode(s):
    o = json.loads(s, object_pairs_hook=OrderedDict)
    return o


def serialize_hook(o):
    o = serialize_object(o)
    if isinstance(o, (np.number, np.bool_)):
        return o.tolist()
    elif isinstance(o, np.ndarray):
        assert len(o.shape) == 1, "Expected 1d array, got {}".format(o.shape)
        return o.tolist()
    else:
        return o
