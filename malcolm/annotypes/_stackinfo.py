import sys
import os

# in python 3.7 the constructor for a generic class is called
# via the __call__ function of _GenericAlias. __init__ is called
# before its __orig_class__ member is set. This means there is
# no way to verify that the correct types have been passed.
#
# As a workaround we walk up the stack to see which concrete
# class called our __init__. This function does the stack walk
# and is called from Array.__init__().


def find_caller_class(filename):
    """
    Find the stack frame of the caller
    """
    f = sys._getframe(1)
    while hasattr(f, "f_code"):
        co = f.f_code
        this_file = os.path.normcase(co.co_filename)
        if filename == this_file:
            f = f.f_back
            continue
        break

    result = f.f_locals['self']
    return result
