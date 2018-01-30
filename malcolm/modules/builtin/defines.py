import os
import subprocess

from annotypes import Anno, add_call_types
import numpy as np

from malcolm.core import Define, Importer


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
    importer = Importer()
    assert os.path.isdir(path), "%r doesn't exist" % path
    name = "malcolm.modules.%s" % name
    importer.import_package_from_path(name, path)
    importer.import_special_subpackages(name, path)
    return define
