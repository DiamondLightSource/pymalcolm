import logging
import os

from ruamel import yaml

from malcolm.compat import str_
from malcolm.core import method_takes, call_with_params


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


def make_include_creator(yaml_path, filename=None):
    sections, yamlname = Section.from_yaml(yaml_path, filename)

    # Check we don't have any controllers
    assert len(sections["controllers"]) == 0, \
        "Expected exactly 0 controller, got %s" % (sections["controllers"],)

    # Add any parameters to the takes arguments
    @method_takes(*_create_takes_arguments(sections))
    def include_creator(process, params=None):
        if params:
            params = dict(params)
        else:
            params = {}
        params["yamlname"] = yamlname
        return _create_blocks_and_parts(process, sections, params)

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
    sections, yamlname = Section.from_yaml(yaml_path, filename)

    # Check we have only one controller
    assert len(sections["controllers"]) == 1, \
        "Expected exactly 1 controller, got %s" % (sections["controllers"],)
    controller_section = sections["controllers"][0]

    # Add any parameters to the takes arguments
    @method_takes(*_create_takes_arguments(sections))
    def block_creator(process, params=None):
        if params:
            params = dict(params)
        else:
            params = {}
        params["yamlname"] = yamlname

        parts = _create_blocks_and_parts(process, sections, params)

        # Make the controller
        controller = controller_section.instantiate(params, process, parts)
        process.add_controller(controller.mri, controller)

        return controller

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
        from malcolm import modules
        ob = modules
        split = self.name.split(".")
        param_dict = self.substitute_params(substitutions)
        for n in split:
            try:
                ob = getattr(ob, n)
            except AttributeError as e:
                raise ValueError("%s:%d: Can't find %r of %r" % (
                    self.filename, self.lineno, n, self.name))
        logging.debug("Instantiating %s with %s", ob, param_dict)
        return call_with_params(ob, *args, **param_dict)

    @classmethod
    def from_yaml(cls, yaml_path, filename=None):
        """Split a dictionary into parameters, controllers, parts and blocks

        Args:
            yaml_path (str): File path to YAML file, or a file in the same dir
            filename (str): If give, use this filename as the last element in
                the yaml_path (so yaml_path can be __file__)

        Returns:
            dict: dictionary containing sections sub dictionaries lists. E.g.
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
        logging.debug("Parsing %s", yaml_path)
        with open(yaml_path) as f:
            text = f.read()
        # First separate them into their relevant sections
        ds = yaml.load(text, Loader=yaml.RoundTripLoader)
        sections = dict(
            parameters=[], controllers=[], parts=[], blocks=[], includes=[])
        for d in ds:
            assert len(d) == 1, \
                "Expected section length 1, got %d" % len(d)
            lineno = d._yaml_line_col.line + 1
            name = list(d)[0]
            split = name.split(".")
            if len(split) != 3:
                raise ValueError(
                    "%s:%d: Expected something like builtin.parts.ChildPart. "
                    "Got %r" % (filename, lineno, name))
            section = split[1]
            if section in sections:
                sections[section].append(cls(
                    yaml_path, lineno, name, d[name]))
            else:
                raise ValueError("Unknown section name %s" % name)

        return sections, yamlname

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


