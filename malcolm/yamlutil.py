import logging
import os
import importlib
import inspect

from annotypes import Any, TYPE_CHECKING, Anno, NO_DEFAULT
from ruamel import yaml
from collections import MutableSequence

from malcolm.compat import str_, raise_with_traceback, OrderedDict
from malcolm.core import YamlError, Controller, Part, Define, MethodMeta

if TYPE_CHECKING:
    from typing import List, Dict, Tuple, Callable

# Create a module level logger
log = logging.getLogger(__name__)

SECTION_NAMES = [
    "parameters", "controllers", "parts", "blocks", "includes", "defines"]


def _create_takes_arguments(sections):
    # type: (List[Section]) -> List[Anno]
    takes_arguments = []
    for section in sections:
        if section.section == "parameters":
            takes_arguments.append(section.instantiate({}))
    annos = [x for x in takes_arguments if x.default is NO_DEFAULT] + \
            [x for x in takes_arguments if x.default is not NO_DEFAULT]
    return annos


def _create_blocks_and_parts(sections,  # type: List[Section]
                             params  # type: Dict[str, str]
                             ):
    # type: (...) -> Tuple[List[Controller], List[Part]]
    controllers = []
    parts = []

    for section in sections:
        if section.section == "blocks":
            # Any child blocks
            controllers += section.instantiate(params)
        elif section.section == "includes":
            # Includes can have child blocks and/or lists of parts
            new_c, new_p = section.instantiate(params)
            controllers += new_c
            parts += new_p
        elif section.section == "parts":
            # A single part
            parts.append(section.instantiate(params))

    return controllers, parts


def _create_defines(sections,  # type: List[Section]
                    yamlname,  # type: str
                    yamldir,  # type: str
                    params  # type: Dict[str, str]
                    ):
    # type: (...) -> Dict[str, str]
    # Start with some
    defines = dict(yamlname=yamlname, yamldir=yamldir, docstring="")
    # Add in the parameter defaults
    for section in sections:
        if section.section == "parameters":
            parameter = section.instantiate(defines)  # type: Anno
            if parameter.default is not NO_DEFAULT:
                defines[parameter.name] = parameter.default
    if params:
        defines.update(params)
    for section in sections:
        if section.section == "defines":
            define = section.instantiate(defines)  # type: Define
            defines[define.name] = define.value
    return defines


def check_yaml_names(globals_d):
    """Check that all include_creators and block_creators have the same
    name as the base of their file path, and return them in a list suitable
    for publishing as __all__"""
    # type: (Dict[str, Any]) -> List[str]
    all_list = []
    for k, v in sorted(globals_d.items()):
        if hasattr(v, "yamlname"):
            assert v.yamlname == k, \
                "%r should be called %r as it comes from %r" % (
                    k, v.yamlname, v.yamlname + ".yaml")
            all_list.append(k)
    return all_list


def make_include_creator(yaml_path, filename=None):
    # type: (str, str) -> Callable[..., Tuple[List[Controller], List[Part]]]
    sections, yamlname, docstring = Section.from_yaml(yaml_path, filename)
    yamldir = os.path.dirname(os.path.abspath(yaml_path))

    # Check we don't have any controllers
    controller_sections = [s for s in sections if s.section == "controllers"]
    assert len(controller_sections) == 0, \
        "Expected exactly 0 controllers, got %s" % (controller_sections,)

    # Add any parameters to the takes arguments
    def include_creator(kwargs):
        # Create the param dict of the static defined arguments
        defines = _create_defines(sections, yamlname, yamldir, kwargs)
        return _create_blocks_and_parts(sections, defines)

    creator = creator_with_nice_signature(
        include_creator, sections, yamlname, yaml_path, docstring)
    return creator


# Add any parameters to the takes arguments
def creator_with_nice_signature(creator, sections, yamlname, yaml_path,
                                docstring):
    takes = _create_takes_arguments(sections)
    args = []
    for anno in takes:
        if anno.default is NO_DEFAULT:
            args.append(anno.name)
        else:
            args.append("%s=%r" % (anno.name, anno.default))
    func = """
def creator_from_yaml(%s):
    return creator(locals())""" % (", ".join(args))
    # Copied from decorator pypi module
    code = compile(func, yaml_path, 'single')
    exec(code, locals())
    ret = locals()["creator_from_yaml"]
    ret.return_type = Anno("Any return value", Any, "return")
    ret.call_types = OrderedDict((anno.name, anno) for anno in takes)
    ret.__doc__ = docstring
    ret.__name__ = yamlname
    ret.yamlname = yamlname
    return ret


def make_block_creator(yaml_path, filename=None):
    # type: (str, str) -> Callable[..., List[Controller]]
    """Make a collection function that will create a list of blocks

    Args:
        yaml_path (str): File path to YAML file, or a file in the same dir
        filename (str): If give, use this filename as the last element in
            the yaml_path (so yaml_path can be __file__)

    Returns:
        A collection function decorated with @takes. This can be used in other
        blocks or instantiated by the process. If the YAML text specified
        controllers or parts then a block instance with the given name will be
        instantiated. If there are any blocks listed then they will be called.
        All created controllers by this or any sub collection will be returned
    """
    sections, yamlname, docstring = Section.from_yaml(yaml_path, filename)
    yamldir = os.path.dirname(os.path.abspath(yaml_path))

    # Check we have only one controller
    controller_sections = [s for s in sections if s.section == "controllers"]
    assert len(controller_sections) == 1, \
        "Expected exactly 1 controller, got %s" % (controller_sections,)
    controller_section = controller_sections[0]

    def block_creator(kwargs):
        # Create the param dict of the static defined arguments
        defines = _create_defines(sections, yamlname, yamldir, kwargs)
        controllers, parts = _create_blocks_and_parts(sections, defines)
        # Make the controller
        controller = controller_section.instantiate(defines)
        for part in parts:
            controller.add_part(part)
        controllers.append(controller)
        return controllers

    creator = creator_with_nice_signature(
        block_creator, sections, yamlname, yaml_path, docstring)
    return creator


class Section(object):
    def __init__(self, filename, lineno, name, param_dict=None):
        self.filename = filename
        self.lineno = lineno
        self.name = name
        # Check the name
        split = name.split(".")
        if len(split) != 3:
            raise YamlError(
                "%s:%d: Expected something like 'builtin.parts.ChildPart'. "
                "Got %r" % (filename, lineno, name))
        section = split[1]
        if section not in SECTION_NAMES:
            raise YamlError("%s:%d: Unknown section name %s" % (
                filename, lineno, name))
        self.section = section
        if param_dict is None:
            self.param_dict = {}
        else:
            # dictify yaml's intermediate dict like object
            self.param_dict = dict(param_dict)

    def instantiate(self, substitutions):
        """Keep recursing down from base using dotted name, then call it with
        self.params and args

        Args:
            substitutions (dict): Substitutions to make to self.param_dict

        Returns:
            The found object called with (*args, map_from_d)

        E.g. if ob is malcolm.parts, and name is "ca.CADoublePart", then the
        object will be malcolm.parts.ca.CADoublePart
        """
        param_dict = self.substitute_params(substitutions)
        pkg, ident = self.name.rsplit(".", 1)
        pkg = "malcolm.modules.%s" % pkg
        try:
            ob = importlib.import_module(pkg)
        except ImportError as e:
            raise_with_traceback(
                ImportError("\n%s:%d:\n%s" % (
                    self.filename, self.lineno, e)))
        try:
            ob = getattr(ob, ident)
        except AttributeError:
            raise_with_traceback(
                ImportError("\n%s:%d:\nPackage %r has no ident %r" % (
                    self.filename, self.lineno, pkg, ident)))
        try:
            meta = MethodMeta.from_callable(ob, returns=False)
            args = meta.takes.validate(param_dict)
            ret = ob(**args)
        except Exception as e:
            sourcefile = inspect.getsourcefile(ob)
            lineno = inspect.getsourcelines(ob)[1]
            raise_with_traceback(
                YamlError("\n%s:%d:\n%s:%d:\n%s" % (
                    self.filename, self.lineno, sourcefile, lineno, e)))
        else:
            return ret

    @classmethod
    def from_yaml(cls, yaml_path, filename=None):
        """Split a dictionary into parameters controllers parts blocks defines

        Args:
            yaml_path (str): File path to YAML file, or a file in the same dir
            filename (str): If give, use this filename as the last element in
                the yaml_path (so yaml_path can be __file__)

        Returns:
            tuple: (sections, yamlname, docstring) where sections is a
                list of created sections
        """
        if filename:
            # different filename to support passing __file__
            yaml_path = os.path.join(os.path.dirname(yaml_path), filename)
        assert yaml_path.endswith(".yaml"), \
            "Expected a/path/to/<yamlname>.yaml, got %r" % yaml_path
        yamlname = os.path.basename(yaml_path)[:-5]
        log.debug("Parsing %s", yaml_path)
        with open(yaml_path) as f:
            text = f.read()
        # First separate them into their relevant sections
        ds = yaml.load(text, Loader=yaml.RoundTripLoader)
        docstring = None
        sections = []
        for d in ds:
            assert len(d) == 1, \
                "Expected section length 1, got %d" % len(d)
            lineno = d._yaml_line_col.line + 1
            name = list(d)[0]
            sections.append(cls(
                yaml_path, lineno, name, d[name]))
            if name == "builtin.defines.docstring":
                docstring = d[name]["value"]

        return sections, yamlname, docstring

    def substitute_params(self, substitutions):
        """Substitute param values in our param_dict from params

        Args:
            substitutions (Map or dict): Values to substitute. E.g. Map of
                {"name": "me"}

        E.g. if self.param_dict is:
            {"name": "$(name):pos", "exposure": 1.0}
        And substitutions is:
            {"name": "me"}
        After the call self.param_dict will be:
            {"name": "me:pos", "exposure": 1.0}
        """
        param_dict = {}
        # TODO: this should be yaml.add_implicit_resolver()
        for k, v in self.param_dict.items():
            param_dict[k] = replace_substitutions(v, substitutions)
        return param_dict

    def __repr__(self):
        return "Section(%s, %s)" % (self.name, self.param_dict)


def replace_substitutions(value, substitutions):
    if isinstance(value, MutableSequence):
        value = [replace_substitutions(v, substitutions) for v in value]
    elif isinstance(value, str_):
        for s in substitutions:
            value = value.replace("$(%s)" % s, str(substitutions[s]))
    return value
