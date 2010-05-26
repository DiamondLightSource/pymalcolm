#!/usr/bin/env python

from setuptools import setup, Extension

# these lines allow the version to be specified in Makefile.RELEASE
import os
version = os.environ.get('MODULEVER', 'unknown')

coroutine = Extension(
    'cothread._coroutine', sources = ['context/_coroutine.c'])

setup(
    name = 'cothread',
    version = version,
    description = 'Cooperative threading based utilities',
    author = 'Michael Abbott',
    author_email = 'Michael.Abbott@diamond.ac.uk',
    entry_points = {
        'console_scripts': [
            'pvtree.py = cothread.tools.pvtree:main' ] },

    zip_safe = False,
    ext_modules = [coroutine],
    packages = ['cothread', 'cothread/tools'],)
#     package_data = {'cothread': ['_coroutine.so']})
