import logging

from ruamel import yaml

from malcolm.compat import str_, OrderedDict
from malcolm.core import REQUIRED, method_takes
from malcolm.core.vmetas import StringMeta


def make_assembly(text):
    """Make a collection function that will create a list of blocks

    Args:
        text (str): YAML text specifying parameters, controllers, parts and
            other assemblies to be instantiated

    Returns:
        function: A collection function decorated with @takes. This can be
            used in other assemblies or instantiated by the process. If the
            YAML text specified controllers or parts then a block instance
            with the given name will be instantiated. If there are any
            assemblies listed then they will be called. All created blocks
            by this or any sub collection will be returned
    """
    import malcolm.assemblies
    import malcolm.comms
    import malcolm.parameters

    ds = yaml.load(text, Loader=yaml.RoundTripLoader)

    sections = Section.split_into_sections(ds)

    # If we have parts then check we have a maximum of one controller
    if sections["controllers"] or sections["parts"]:
        ncontrollers = len(sections["controllers"])
        assert ncontrollers in (0, 1), \
            "Expected 0 or 1 controller with parts, got %s" % ncontrollers
        # We will be creating a block here, so we need a name
        takes_arguments = [
            "name", StringMeta("Name of the created block"), REQUIRED]
    else:
        # No name needed as just a collection of other assemblies
        takes_arguments = []

    # Add any parameters to the takes arguments
    for parameter_section in sections["parameters"]:
        takes_arguments += parameter_section.instantiate(malcolm.parameters)

    @method_takes(*takes_arguments)
    def collection(process, params):
        # TODO: move this into Section.substitute_params
        ssections = dict()
        for name, section_l in sections.items():
            ssections[name] = []
            for section in section_l:
                section = Section(section.name, section.param_dict.copy())
                section.substitute_params(params)
                ssections[name].append(section)
        ret = []

        # If we have any comms things
        for section in ssections["comms"]:
            comms = section.instantiate(malcolm.comms, process)
            process.add_comms(comms)

        # If we have any other assemblies
        for section in ssections["assemblies"]:
            ret += section.instantiate(malcolm.assemblies, process)

        # If told to make a block instance from controllers and parts
        if ssections["controllers"] or ssections["parts"]:
            ret.append(make_block_instance(
                process, ssections["controllers"], ssections["parts"]))

        return ret

    return collection


def make_block_instance(process, controllers, parts):
    """Make a block subclass from a series of parts.* and controllers.* dicts

    Args:
        process (Process): The process it should be attached to
        controllers (list): List of controller Section objects. E.g.
            [Section("ManagerController")]
        parts (list): List of part Section objects. E.g.
            [Section("ca.CADoublePart", {"name": "me", "pv": "MY:PV:STRING"})]

    Returns:
        Block: The created block instance as managed by the controller with
            all the parts attached
    """
    import malcolm.parts
    import malcolm.controllers

    parts_d = OrderedDict()
    for section in parts:
        part = section.instantiate(malcolm.parts, process)
        parts_d[part.name] = part
    assert len(controllers) == 1, \
        "Expected exactly 1 controller, got %s" % (controllers,)
    controller = controllers[0].instantiate(
        malcolm.controllers, process, parts_d)
    return controller.block


class Section(object):
    def __init__(self, name, param_dict=None):
        if param_dict is None:
            param_dict = {}
        self.name = name
        # dictify yaml's intermediate dict like object
        self.param_dict = dict(param_dict)

    def instantiate(self, base, *args):
        """Keep recursing down from base using dotted name, then call it with
        self.params and args

        Args:
            base (object): The starting object
            *args: Any other args to pass to the callable

        Returns:
            object: The found object called with (*args, map_from_d)

        E.g. if ob is malcolm.parts, and name is "ca.CADoublePart", then the
        object will be malcolm.parts.ca.CADoublePart
        """
        split = self.name.split(".")
        for n in split:
            try:
                base = getattr(base, n)
            except AttributeError:
                logging.error("Can't find %s of %s", n, self.name)
                raise
        logging.debug("Instantiating %s with %s", base, self.param_dict)
        args += (base.MethodMeta.prepare_input_map(**self.param_dict),)
        return base(*args)

    @classmethod
    def split_into_sections(cls, ds):
        """Split a dictionary into parameters, controllers, parts and assemblies

        Args:
            ds (list): List of section dictionaries: params. E.g.
                [{"parameters.string": {"name": "something"}},
                 {"controllers.ManagerController": None}]

        Returns:
            dict: dictionary containing sections sub dictionaries lists. E.g.
                {
                    "parameters": [
                        Section(name="string", params={"name": "something"}
                    ],
                    "controllers": [Section(name="ManagerController")]
                }
        """
        # First separate them into their relevant sections
        sections = dict(
            parameters=[], controllers=[], parts=[], assemblies=[], comms=[])
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
        for s in substitutions:
            for k, v in self.param_dict.items():
                search = "$(%s)" % s
                if isinstance(v, str_):
                    self.param_dict[k] = v.replace(search, substitutions[s])

    def __repr__(self):
        return "Section(%s, %s)" % (self.name, self.param_dict)


