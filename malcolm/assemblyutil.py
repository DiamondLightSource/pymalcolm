import os
from collections import OrderedDict
import logging

from ruamel import yaml

from malcolm.packageutil import prepare_globals_for_package
from malcolm.compat import base_string
from malcolm.core import REQUIRED, method_takes
from malcolm.core.vmetas import StringMeta
import malcolm.controllers
import malcolm.parameters
import malcolm.parts


def make_all_assemblies(globals_d, package_name):
    def finder(package_fs_path, fname):
        split = fname.split(".")
        if split[-1] == "yaml":
            assert len(split) == 2, \
                "Expected <something_without_dots>.yaml, got %r" % fname
            yaml_path = os.path.join(package_fs_path, fname)
            logging.debug("Parsing %s", yaml_path)
            with open(yaml_path) as f:
                text = f.read()
                func = make_assembly(text)
                yield split[0], func

    __all__ = prepare_globals_for_package(globals_d, package_name, finder)
    return __all__

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

    ds = yaml.load(text, Loader=yaml.RoundTripLoader)

    sections = split_into_sections(ds)

    # If we have parts then check we have a maximum of one controller
    if sections["controllers"] or sections["parts"]:
        ncontrollers = len(sections["controllers"])
        assert ncontrollers in (0, 1), \
            "Expected 0 or 1 controller with parts, got %s" % ncontrollers
        # We will be creating a block here, so we need a name
        include_name = True
    else:
        # No name needed as just a collection of other assemblies
        include_name = False

    @with_takes_from(sections["parameters"], include_name)
    def collection(process, params):
        substitute_params(sections, params)
        ret = []

        # If told to make a block instance from controllers and parts
        if sections["controllers"] or sections["parts"]:
            ret.append(make_block_instance(
                params["name"], process,
                sections["controllers"], sections["parts"]))

        # It we have any other assemblies
        for section_d in sections["assemblies"]:
            assert len(section_d) == 1, \
                "Expected section length 1, got %d" % len(section_d)
            name, d = list(section_d.items())[0]
            logging.debug("Instantiating sub assembly %s", name)
            ret += call_with_map(malcolm.assemblies, name, d, process)

        return ret

    return collection

def split_into_sections(ds):
    """Split a dictionary into parameters, controllers, parts and assemblies

    Args:
        ds (list): List of section dictionaries: params. E.g.
            [{"parameters.string": {"name": "something"}},
             {"controllers.ManagerController": None}]

    Returns:
        dict: dictionary containing sections sub dictionaries lists. E.g.
            {
                "parameters": [{
                    "string": {"name": "something"}
                }],
                "controllers": [{
                    "ManagerController": None
                }]
            }
    """
    # First separate them into their relevant sections
    sections = dict(parameters=[], controllers=[], parts=[], assemblies=[])
    for d in ds:
        assert len(d) == 1, \
            "Expected section length 1, got %d" % len(d)
        name = list(d)[0]
        section, subsection = name.split(".", 1)
        if section in sections:
            sections[section].append({subsection: d[name]})
        else:
            raise ValueError("Unknown section name %s" % name)

    return sections

def with_takes_from(parameters, include_name):
    """Create an @takes decorator from parameters dict.

    Args:
        parameters (dict): Parameters sub dictionary. E.g.
            [{"string": {"name": "something"}}]
        include_name (bool): If True then put a "name" meta first

    Returns:
        function: Decorator that will set a "MethodMeta" attribute on the callable
            with the arguments it should take
    """
    # find all the Takes objects and create them
    if include_name:
        takes_arguments = [
            "name", StringMeta("Name of the created block"), REQUIRED]
    else:
        takes_arguments = []
    for param_d in parameters:
        assert len(param_d) == 1, \
            "Expected length 1, got %s" % (param_d,)
        f_name, d = list(param_d.items())[0]
        takes_arguments += call_with_map(malcolm.parameters, f_name, d)
    return method_takes(*takes_arguments)

def substitute_params(d, params):
    """Substitute a dictionary in place with $(attr) macros in it with values
    from params

    Args:
        d (dict): Input dictionary {string key: any value}. E.g.
            {"name": "$(name):pos", "exposure": 1.0}
        params (Map or dict): Values to substitute. E.g. Map of
            {"name": "me"}

    After the call the dictionary will look like:
        {"name": "me:pos", "exposure": 1.0}
    """
    for p in params:
        for k, v in d.items():
            search = "$(%s)" % p
            if isinstance(v, base_string):
                d[k] = v.replace(search, params[p])
            elif isinstance(v, list):
                for d2 in v:
                    substitute_params(d2, params)
            elif isinstance(v, dict):
                substitute_params(v, params)

def make_block_instance(name, process, controllers_d, parts_d):
    """Make a block subclass from a series of parts.* and controllers.* dicts

    Args:
        name (str): The name of the resulting block instance
        process (Process): The process it should be attached to
        controllers_d (dict): Controllers sub dictionary. E.g.
            {"ManagerController": None}
        parts_d (dict): Parts sub dictionary. E.g.
            {"ca.CADoublePart": {"name": "me", "pv": "MY:PV:STRING"}}

    Returns:
        Block: The created block instance as managed by the controller with
            all the parts attached
    """
    parts = OrderedDict()
    for part_d in parts_d:
        assert len(part_d) == 1, \
            "Expected length 1, got %s" % (part_d,)
        cls_name, d = list(part_d.items())[0]
        # Require all parts to have a name
        # TODO: make sure this is added from gui?
        parts[d["name"]] = call_with_map(malcolm.parts, cls_name, d, process)
    if controllers_d:
        assert len(controllers_d) == 1, \
            "Expected length 1, got %s" % (controllers_d,)
        d = controllers_d[0]
        assert len(d) == 1, \
            "Expected length 1, got %s" % (d,)
        cls_name, d = list(d.items())[0]
    else:
        cls_name = "DefaultController"
        d = None
    logging.debug("Creating %s %r", cls_name, name)
    controller = call_with_map(
        malcolm.controllers, cls_name, d, name, process, parts)
    return controller.block

def call_with_map(ob, name, d, *args):
    """Keep recursing down from ob using dotted name, then call it with d, *args

    Args:
        ob (object): The starting object
        name (string): The dotted attribute path to follow
        d (dict): A dictionary of parameters that will be turned into a Map and
            passed to the found callable
        *args: Any other args to pass to the callable

    Returns:
        object: The found object called with (map_from_d, *args)

    E.g. if ob is malcolm.parts, and name is "ca.CADoublePart", then the object
    will be malcolm.parts.ca.CADoublePart
    """
    split = name.split(".")
    for n in split:
        ob = getattr(ob, n)

    params = ob.MethodMeta.prepare_input_map(d)
    args += (params,)
    return ob(*args)