import os
import subprocess
import imp
import importlib

from annotypes import Anno, add_call_types
import numpy as np

from malcolm.core import Define


def import_package_from_path(name, path):
    dirname, basename = os.path.abspath(path).rsplit(os.sep, 1)
    file, pathname, description = imp.find_module(basename, [dirname])
    try:
        mod = imp.load_module(name, file, pathname, description)
    finally:
        if file is not None:
            file.close()
    parent_name, attr_name = name.rsplit(".", 1)
    parent = importlib.import_module(parent_name)
    setattr(parent, attr_name, mod)


with Anno("The name of the defined parameter"):
    AName = str
with Anno("The value of the defined parameter"):
    AStringValue = str
with Anno("The value of the defined parameter"):
    AFloat64Value = np.float64
with Anno("The value of the defined parameter"):
    AInt32Value = np.int32
with Anno("The Define that has been created"):
    ADefine = Define


@add_call_types
def string(name, value):
    # type: (AName, AStringValue) -> ADefine
    """Define a string parameter to be used within this YAML file"""
    return Define(name, value)


@add_call_types
def float64(name, value):
    # type: (AName, AFloat64Value) -> ADefine
    """Define a float64 parameter to be used within this YAML file"""
    return Define(name, value)


@add_call_types
def int32(name, value):
    # type: (AName, AInt32Value) -> ADefine
    """Define an int32 parameter to be used within this YAML file"""
    return Define(name, value)


@add_call_types
def docstring(value):
    # type: (AStringValue) -> ADefine
    """Define the docstring for the YAML file"""
    return Define("docstring", value)


with Anno("The environment variable name to get the value from"):
    AEnvSource = str


@add_call_types
def env_string(name, env):
    # type: (AName, AEnvSource) -> ADefine
    """Define a string parameter coming from the environment to be used within
    this YAML file"""
    return Define(name, os.environ[env])


with Anno("The shell command to run to get the value from"):
    ACmd = str


@add_call_types
def cmd_string(name, cmd):
    # type: (AName, ACmd) -> ADefine
    """Define a string parameter coming from a shell command to be used within
    this YAML file. Trailing newlines will be stripped."""
    value = subprocess.check_output(cmd, shell=True).rstrip("\n")
    return Define(name, value)


with Anno("The environment variable name to set"):
    AEnvName = str
with Anno("The value of the exported environment variable"):
    AEnvValue = str


@add_call_types
def export_env_string(name, value):
    # type: (AEnvName, AEnvValue) -> ADefine
    """Exports an environment variable with the given value"""
    os.environ[name] = value
    return Define(name, value)


with Anno("The name of the exported module"):
    AModuleName = str
with Anno("The path of a python package dir to insert as "
          "malcolm.modules.<name>"):
    AModulePath = str


@add_call_types
def module_path(name, path):
    # type: (AModuleName, AModulePath) -> ADefine
    """Load an external malcolm module (e.g. ADCore/etc/malcolm)"""
    define = Define(name, path)
    assert os.path.isdir(path), "%r doesn't exist" % path
    name = "malcolm.modules.%s" % name
    import_package_from_path(name, path)
    return define
