import logging
import os
import importlib

from ruamel import yaml

from malcolm.compat import str_
from malcolm.core import method_takes, call_with_params, YamlError

# Create a module level logger
log = logging.getLogger(__name__)


def _create_takes_arguments(sections):
    takes_arguments = []
    for parameter_section in sections["parameters"]:
        takes_arguments += parameter_section.instantiate({})
    return takes_arguments


def _create_blocks_and_parts(process, sections, params):
    parts = []

    # Any child blocks
    for section in sections["blocks"]:
        section.instantiate(params, process)

    # Do the includes first
    for section in sections["includes"]:
        parts += section.instantiate(params, process)

    # Add any parts in
    for section in sections["parts"]:
        parts.append(section.instantiate(params))

    return parts


def _create_defines(sections, yamlname, yamldir, params):
    defines = dict(yamlname=yamlname, yamldir=yamldir, docstring="")
    if params:
        defines.update(params)
    for section in sections["defines"]:
        defines.update(section.instantiate(defines))
    return defines


def check_yaml_names(globals_d):
    all_list = []
    for k, v in sorted(globals_d.items()):
        if hasattr(v, "yamlname"):
            assert v.yamlname == k, \
                "%r should be called %r as it comes from %r" % (
                    k, v.yamlname, v.yamlname + ".yaml")
            all_list.append(k)
    return all_list


def make_include_creator(yaml_path, filename=None):
    sections, yamlname, docstring = Section.from_yaml(yaml_path, filename)
    yamldir = os.path.dirname(yaml_path)

    # Check we don't have any controllers
    assert len(sections["controllers"]) == 0, \
        "Expected exactly 0 controller, got %s" % (sections["controllers"],)

    # Add any parameters to the takes arguments
    @method_takes(*_create_takes_arguments(sections))
    def include_creator(process, params=None):
        # Create the param dict of the static defined arguments
        defines = _create_defines(sections, yamlname, yamldir, params)
        return _create_blocks_and_parts(process, sections, defines)

    include_creator.__doc__ = docstring
    include_creator.__name__ = yamlname
    include_creator.yamlname = yamlname

    return include_creator


def make_block_creator(yaml_path, filename=None):
    """Make a collection function that will create a list of blocks

    Args:
        yaml_path (str): File path to YAML file, or a file in the same dir
        filename (str): If give, use this filename as the last element in
            the yaml_path (so yaml_path can be __file__)

    Returns:
        function: A collection function decorated with @takes. This can be
            used in other blocks or instantiated by the process. If the
            YAML text specified controllers or parts then a block instance
            with the given name will be instantiated. If there are any
            blocks listed then they will be called. All created blocks
            by this or any sub collection will be returned
    """
    sections, yamlname, docstring = Section.from_yaml(yaml_path, filename)
    yamldir = os.path.dirname(yaml_path)

    # Check we have only one controller
    assert len(sections["controllers"]) == 1, \
        "Expected exactly 1 controller, got %s" % (sections["controllers"],)
    controller_section = sections["controllers"][0]

    # Add any parameters to the takes arguments
    @method_takes(*_create_takes_arguments(sections))
    def block_creator(process, params=None):
        # Create the param dict of the static defined arguments
        defines = _create_defines(sections, yamlname, yamldir, params)
        parts = _create_blocks_and_parts(process, sections, defines)

        # Make the controller
        controller = controller_section.instantiate(defines, process, parts)
        process.add_controller(controller.mri, controller)

        return controller

    block_creator.__doc__ = docstring
    block_creator.__name__ = yamlname
    block_creator.yamlname = yamlname

    return block_creator


class Section(object):
    def __init__(self, filename, lineno, name, param_dict=None):
        self.filename = filename
        self.lineno = lineno
        self.name = name
        if param_dict is None:
            self.param_dict = {}
        else:
            # dictify yaml's intermediate dict like object
            self.param_dict = dict(param_dict)

    def instantiate(self, substitutions, *args):
        """Keep recursing down from base using dotted name, then call it with
        self.params and args

        Args:
            substitutions (dict): Substitutions to make to self.param_dict
            *args: Any other args to pass to the callable

        Returns:
            object: The found object called with (*args, map_from_d)

        E.g. if ob is malcolm.parts, and name is "ca.CADoublePart", then the
        object will be malcolm.parts.ca.CADoublePart
        """
        param_dict = self.substitute_params(substitutions)
        pkg, ident = self.name.rsplit(".", 1)
        pkg = "malcolm.modules.%s" % pkg
        try:
            ob = importlib.import_module(pkg)
        except ImportError:
            raise ImportError("%s:%d:\nCan't import %r" % (
                self.filename, self.lineno, pkg))
        try:
            ob = getattr(ob, ident)
        except AttributeError:
            raise ImportError("%s:%d:\nPackage %r has no ident %r" % (
                self.filename, self.lineno, pkg, ident))
        try:
            ret = call_with_params(ob, *args, **param_dict)
        except YamlError as e:
            raise YamlError("%s:%d:\n%s" % (self.filename, self.lineno, e))
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
                dictionary containing sections sub dictionaries lists. E.g.
                {
                    "parameters": [
                        Section(name="builtin.parameters.string",
                            params={"name": "something"})
                    ],
                    "controllers": [
                        Section(name="builtin.controllers.ManagerController",
                            params={"mri": "something")
                    ]
                }
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
        sections = dict(
            parameters=[], controllers=[], parts=[], blocks=[], includes=[],
            defines=[])
        for d in ds:
            assert len(d) == 1, \
                "Expected section length 1, got %d" % len(d)
            lineno = d._yaml_line_col.line + 1
            name = list(d)[0]
            split = name.split(".")
            if len(split) != 3:
                raise ImportError(
                    "%s:%d: Expected something like 'builtin.parts.ChildPart'. "
                    "Got %r" % (yaml_path, lineno, name))
            section = split[1]
            if section in sections:
                sections[section].append(cls(
                    yaml_path, lineno, name, d[name]))
                if name == "builtin.defines.docstring":
                    docstring = d[name]["value"]
            else:
                raise ImportError("%s:%d: Unknown section name %s" % (
                    yaml_path, lineno, name))

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
            for s in substitutions:
                if isinstance(v, str_):
                    # TODO: handle int etc here
                    v = v.replace("$(%s)" % s, str(substitutions[s]))
            param_dict[k] = v
        return param_dict

    def __repr__(self):
        return "Section(%s, %s)" % (self.name, self.param_dict)


