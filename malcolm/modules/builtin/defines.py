import os
import subprocess

from malcolm.core import method_takes, REQUIRED
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
def envstring(params):
    """Define a string parameter coming from the environment to be used within
    this YAML file"""
    return {params.name: os.environ[params.env]}


@method_takes(
    "name", StringMeta("The name of the defined parameter"), REQUIRED,
    "cmd", StringMeta(
        "The shell command to run to get the value from"), REQUIRED)
def cmdstring(params):
    value = subprocess.check_output(params.cmd, shell=True)
    return {params.name: value}
