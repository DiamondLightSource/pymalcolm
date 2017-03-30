from malcolm.compat import str_


def error_message(*args):
    formatted_args = ", ".join(repr(a) for a in args)
    message = "Expected StringArray(s1, s2, ...) or StringArray(seq). " \
              "Got StringArray(%s)" % formatted_args
    return message


class StringArray(tuple):
    def __new__(cls, seq=(), *more):
        if isinstance(seq, str_):
            # First element is a string, so assume *more is seq of strings
            seq = (seq,) + more
        else:
            # Assume seq is iterable, so there should be no *more
            if more:
                raise ValueError(error_message(seq, *more))

        inst = tuple.__new__(StringArray, seq)
        for item in inst:
            if not isinstance(item, str_):
                raise ValueError(error_message(seq, *more))
        return inst
