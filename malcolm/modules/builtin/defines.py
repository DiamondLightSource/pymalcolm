import os
import subprocess
import types
import sys

from malcolm.core import method_takes, REQUIRED, Importer
from malcolm.modules.builtin.vmetas import StringMeta, NumberMeta


@method_takes(
    "name", StringMeta("The name of the defined parameter"), REQUIRED,
    "value", StringMeta("The value of the defined parameter"), REQUIRED)
def string(params):
    """Define a string parameter to be used within this YAML file"""
    return {params.name: params.value}


@method_takes(
    "name", StringMeta("The name of the defined parameter"), REQUIRED,
    "value", NumberMeta(
        "float64", "The value of the defined parameter"), REQUIRED)
def float64(params):
    """Define a string parameter to be used within this YAML file"""
    return {params.name: params.value}


@method_takes(
    "name", StringMeta("The name of the defined parameter"), REQUIRED,
    "value", NumberMeta(
        "int32", "The value of the defined parameter"), REQUIRED)
def int32(params):
    """Define a string parameter to be used within this YAML file"""
    return {params.name: params.value}


@method_takes(
    "value", StringMeta("The docstring value"), REQUIRED)
def docstring(params):
    """Define the docstring for the YAML file"""
    return {"docstring": params.value}


@method_takes(
    "name", StringMeta("The name of the defined parameter"), REQUIRED,
    "env", StringMeta(
        "The environment variable name to get the value from"), REQUIRED)
def env_string(params):
    """Define a string parameter coming from the environment to be used within
    this YAML file"""
    return {params.name: os.environ[params.env]}


@method_takes(
    "name", StringMeta("The name of the defined parameter"), REQUIRED,
    "cmd", StringMeta(
        "The shell command to run to get the value from"), REQUIRED)
def cmd_string(params):
    """Define a string parameter coming from a shell command to be used within
    this YAML file. Trailing newlines will be stripped."""
    value = subprocess.check_output(params.cmd, shell=True).rstrip("\n")
    return {params.name: value}


@method_takes(
    "name", StringMeta(
        "The environment variable name to set"), REQUIRED,
    "value", StringMeta(
        "The value of the exported environment variable"), REQUIRED)
def export_env_string(params):
    """Exports an environment variable with the given value"""
    os.environ[params.name] = params.value
    return {params.name: params.value}


@method_takes(
    "name", StringMeta("The name of the exported module"), REQUIRED,
    "path", StringMeta("The path of a python package dir to insert as "
                       "malcolm.modules.<name>"), REQUIRED)
def module_path(params):
    """Load an external malcolm module (e.g. ADCore/etc/malcolm)"""
    importer = Importer()
    assert os.path.isdir(params.path), "%r doesn't exist" % params.path
    name = "malcolm.modules.%s" % params.name
    importer.import_package_from_path(name, params.path)
    importer.import_special_subpackages(name, params.path)
    return {params.name: params.path}
