import os
import operator

from annotypes import TYPE_CHECKING

from malcolm.modules import builtin
from .pandaiconpart import PandAIconPart
from ..util import SVG_DIR

if TYPE_CHECKING:
    from typing import Callable, Tuple, Set, Dict

LUT_CONSTANTS = dict(
    A=0xffff0000, B=0xff00ff00, C=0xf0f0f0f0, D=0xcccccccc, E=0xaaaaaaaa)


def _calc_visibility(func, op, nargs, permutation):
    # type: (str, Callable, int, int) -> Tuple[int, Set[str]]
    # Visibility dictionary defaults
    invis = {"AND", "OR", "LUT", "NOT"}
    invis.remove(func)
    args = []
    # xxxxx where x is 0 or 1
    # EDCBA
    negations = format(permutation, '05b')
    for i, inp in enumerate("EDCBA"):
        if (5 - i) > nargs:
            # invisible
            invis.add(inp)
            invis.add("not%s" % inp)
        else:
            # visible
            if negations[i] == "1":
                args.append(~LUT_CONSTANTS[inp] & (2 ** 32 - 1))
            else:
                invis.add("not%s" % inp)
                args.append(LUT_CONSTANTS[inp])

    # Insert into table
    fnum = op(args[0], args[1])
    for a in args[2:]:
        fnum = op(fnum, a)
    return fnum, invis


def _generate_lut_elements():
    # type: () -> Dict[int, Set[str]]
    # {fnum: invis}
    lut_elements = {}
    # Generate the lut element table
    # Do the general case funcs
    funcs = [("AND", operator.and_), ("OR", operator.or_)]
    for func, op in funcs:
        for nargs in (2, 3, 4, 5):
            # 2**nargs permutations
            for permutation in range(2 ** nargs):
                fnum, invis = _calc_visibility(func, op, nargs, permutation)
                lut_elements[fnum] = invis
    # Add in special cases for NOT
    for ninp in "ABCDE":
        invis = {"AND", "OR", "LUT"}
        for inp in "ABCDE":
            if inp != ninp:
                invis.add(inp)
            invis.add("not%s" % inp)
        lut_elements[~LUT_CONSTANTS[ninp] & (2 ** 32 - 1)] = invis
    # And catchall for LUT in 0
    invis = {"AND", "OR", "NOT"}
    for inp in "ABCDE":
        invis.add("not%s" % inp)
    lut_elements[0] = invis
    return lut_elements


# lut elements to be displayed or not
LUT_ELEMENTS = _generate_lut_elements()
LUT_INVIS = LUT_ELEMENTS[0]


def get_lut_icon_elements(fnum):
    # type: (int) -> Set[str]
    return LUT_ELEMENTS.get(fnum, LUT_INVIS)


class PandALutIconPart(PandAIconPart):
    update_fields = {"FUNC"}

    def update_icon(self, field_values, ts):
        """Update the icon using the given field values"""
        with open(os.path.join(SVG_DIR, "LUT.svg")) as f:
            svg_text = f.read()
        fnum = int(self.client.get_field(self.block_name, "FUNC.RAW"), 0)
        invis = get_lut_icon_elements(fnum)
        svg_text = builtin.util.svg_text_without_elements(svg_text, invis)
        self.attr.set_value(svg_text, ts=ts)
