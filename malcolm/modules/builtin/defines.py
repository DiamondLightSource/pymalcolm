import imp
import importlib
import os
import subprocess
import tempfile
from typing import Union

import numpy as np
from annotypes import Anno, add_call_types

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
    AFloat64Value = Union[np.float64]
with Anno("The value of the defined parameter"):
    AInt32Value = Union[np.int32]
with Anno("The Define that has been created"):
    ADefine = Define


@add_call_types
def string(name: AName, value: AStringValue) -> ADefine:
    """Define a string parameter to be used within this YAML file"""
    return Define(name, value)


@add_call_types
def float64(name: AName, value: AFloat64Value) -> ADefine:
    """Define a float64 parameter to be used within this YAML file"""
    return Define(name, value)


@add_call_types
def int32(name: AName, value: AInt32Value) -> ADefine:
    """Define an int32 parameter to be used within this YAML file"""
    return Define(name, value)


@add_call_types
def docstring(value: AStringValue) -> ADefine:
    """Define the docstring for the YAML file"""
    return Define("docstring", value)


with Anno("The environment variable name to get the value from"):
    AEnvSource = str


@add_call_types
def env_string(name: AName, env: AEnvSource) -> ADefine:
    """Define a string parameter coming from the environment to be used within
    this YAML file"""
    return Define(name, os.environ[env])


@add_call_types
def tmp_dir(name: AName) -> ADefine:
    """Make a temporary directory, and define a string parameter containing
    its path on disk"""
    return Define(name, tempfile.mkdtemp())


with Anno("The shell command to run to get the value from"):
    ACmd = str


@add_call_types
def cmd_string(name: AName, cmd: ACmd) -> ADefine:
    """Define a string parameter coming from a shell command to be used within
    this YAML file. Trailing newlines will be stripped."""
    value = subprocess.check_output(cmd, shell=True).decode().rstrip("\n")
    return Define(name, value)


with Anno("The environment variable name to set"):
    AEnvName = str
with Anno("The value of the exported environment variable"):
    AEnvValue = str


@add_call_types
def export_env_string(name: AEnvName, value: AEnvValue) -> ADefine:
    """Exports an environment variable with the given value"""
    os.environ[name] = value
    return Define(name, value)


with Anno("The name of the exported module"):
    AModuleName = str
with Anno("The path of a python package dir to insert as " "malcolm.modules.<name>"):
    AModulePath = str


@add_call_types
def module_path(name: AModuleName, path: AModulePath) -> ADefine:
    """Load an external malcolm module (e.g. ADCore/etc/malcolm)"""
    define = Define(name, path)
    assert os.path.isdir(path), "%r doesn't exist" % path
    name = "malcolm.modules.%s" % name
    import_package_from_path(name, path)
    return define
