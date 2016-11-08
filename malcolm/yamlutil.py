import logging

from ruamel import yaml

from malcolm.compat import str_, OrderedDict
from malcolm.core import method_takes


def _create_takes_arguments(sections):
    import malcolm.parameters as parameters_base
    takes_arguments = []
    for parameter_section in sections["parameters"]:
        takes_arguments += parameter_section.instantiate({}, parameters_base)
    return takes_arguments


def _create_blocks_and_parts(process, sections, params):
    import malcolm.includes as includes_base
    import malcolm.parts as parts_base
    import malcolm.blocks as blocks_base

    parts = []
    blocks = []

    # Any child blocks
    for section in sections["blocks"]:
        blocks += section.instantiate(params, blocks_base, process)

    # Do the includes first
    for section in sections["includes"]:
        include_blocks, include_parts = section.instantiate(
            params, includes_base, process)
        blocks += include_blocks
        parts += include_parts

    # Add any parts in
    for section in sections["parts"]:
        parts.append(section.instantiate(params, parts_base, process))

    return blocks, parts


def make_include_creator(text):
    import malcolm.comms as comms_base

    sections = Section.from_yaml(text)

    # Check we don't have any controllers
    assert len(sections["controllers"]) == 0, \
        "Expected exactly 0 controller, got %s" % (sections["controllers"],)

    # Add any parameters to the takes arguments
    @method_takes(*_create_takes_arguments(sections))
    def include_creator(process, params):
        blocks, parts = _create_blocks_and_parts(process, sections, params)

        # Make the comms
        for section in sections["comms"]:
            comms = section.instantiate(params, comms_base, process)
            process.add_comms(comms)

        return blocks, parts

    return include_creator


def make_block_creator(text):
    """Make a collection function that will create a list of blocks

    Args:
        text (str): YAML text specifying parameters, controllers, parts and
            other blocks to be instantiated

    Returns:
        function: A collection function decorated with @takes. This can be
            used in other blocks or instantiated by the process. If the
            YAML text specified controllers or parts then a block instance
            with the given name will be instantiated. If there are any
            blocks listed then they will be called. All created blocks
            by this or any sub collection will be returned
    """
    import malcolm.controllers as controllers_base

    sections = Section.from_yaml(text)

    # Check we have only one controller
    assert len(sections["controllers"]) == 1, \
        "Expected exactly 1 controller, got %s" % (sections["controllers"],)
    controller_section = sections["controllers"][0]

    # Check we have no comms
    assert len(sections["comms"]) == 0, "Can't define comms in a block"

    # Add any parameters to the takes arguments
    @method_takes(*_create_takes_arguments(sections))
    def block_creator(process, params):
        blocks, parts = _create_blocks_and_parts(process, sections, params)

        # Make the controller
        controller = controller_section.instantiate(
            params, controllers_base, process, parts)
        blocks.append(controller.block)

        return blocks

    return block_creator


class Section(object):
    def __init__(self, name, param_dict=None):
        self.name = name
        if param_dict is None:
            self.param_dict = {}
        else:
            # dictify yaml's intermediate dict like object
            self.param_dict = dict(param_dict)

    def instantiate(self, substitutions, base, *args):
        """Keep recursing down from base using dotted name, then call it with
        self.params and args

        Args:
            substitutions (dict): Substitutions to make to self.param_dict
            base (object): The starting object
            *args: Any other args to pass to the callable

        Returns:
            object: The found object called with (*args, map_from_d)

        E.g. if ob is malcolm.parts, and name is "ca.CADoublePart", then the
        object will be malcolm.parts.ca.CADoublePart
        """
        split = self.name.split(".")
        param_dict = self.substitute_params(substitutions)
        for n in split:
            try:
                base = getattr(base, n)
            except AttributeError:
                logging.error("Can't find %s of %s", n, self.name)
                raise
        logging.debug("Instantiating %s with %s", base, param_dict)
        args += (base.MethodMeta.prepare_input_map(**param_dict),)
        return base(*args)

    @classmethod
    def from_yaml(cls, text):
        """Split a dictionary into parameters, controllers, parts and blocks

        Args:
            text (str): Yaml representing some sections. E.g.:
                parameters.string:
                  name: something
                controllers.ManagerController:
                  mri: $(something)

        Returns:
            dict: dictionary containing sections sub dictionaries lists. E.g.
                {
                    "parameters": [
                        Section(name="string", params={"name": "something"}
                    ],
                    "controllers": [
                        Section(name="ManagerController",
                            params={"mri": "something")
                    ]
                }
        """
        # First separate them into their relevant sections
        ds = yaml.load(text, Loader=yaml.RoundTripLoader)
        sections = dict(
            parameters=[], controllers=[], parts=[], blocks=[], comms=[],
            includes=[])
        for d in ds:
            assert len(d) == 1, \
                "Expected section length 1, got %d" % len(d)
            name = list(d)[0]
            section, subsection = name.split(".", 1)
            if section in sections:
                sections[section].append(cls(subsection, d[name]))
            else:
                raise ValueError("Unknown section name %s" % name)

        return sections

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


