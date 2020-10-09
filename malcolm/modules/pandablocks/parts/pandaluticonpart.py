import operator
from typing import Callable, Dict, Set, Tuple

from malcolm.modules import builtin

from .pandaiconpart import PandAIconPart

LUT_CONSTANTS = dict(
    A=0xFFFF0000, B=0xFF00FF00, C=0xF0F0F0F0, D=0xCCCCCCCC, E=0xAAAAAAAA
)


def _calc_visibility(
    func: str, op: Callable, nargs: int, permutation: int
) -> Tuple[int, Set[str]]:
    # Visibility dictionary defaults
    invis = {"AND", "OR", "LUT", "NOT"}
    invis.remove(func)
    args = []
    # xxxxx where x is 0 or 1
    # EDCBA
    negations = format(permutation, "05b")
    for i, inp in enumerate("EDCBA"):
        if (5 - i) > nargs:
            # invisible
            invis.add(inp)
            invis.add("not%s" % inp)
            invis.add("edge%s" % inp)
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


def _generate_lut_elements() -> Dict[int, Set[str]]:
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
                invis.add("edge%s" % inp)
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


def get_lut_icon_elements(fnum: int) -> Set[str]:
    return LUT_ELEMENTS.get(fnum, LUT_INVIS)


class PandALutIconPart(PandAIconPart):
    update_fields = {"FUNC", "TYPEA", "TYPEB", "TYPEC", "TYPED", "TYPEE"}

    def update_icon(self, icon: builtin.util.SVGIcon, field_values: dict) -> None:
        """Update the icon using the given field values"""
        fnum = int(self.client.get_field(self.block_name, "FUNC.RAW"), 0)
        invis = get_lut_icon_elements(fnum)
        icon.remove_elements(invis)
        for inp in "ABCDE":
            # Old versions don't have type, default to level
            edge = field_values.get("TYPE" + inp, "level")
            icon.update_edge_arrow("edge" + inp, edge)
        icon.add_text(
            field_values["FUNC"],
            x=30,
            y=-8,
            anchor="middle",
            transform="rotate(90 20,40)",
        )
