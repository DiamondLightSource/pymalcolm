# import multiprocessing to avoid this bug
# (http://bugs.python.org/issue15881#msg170215)
import multiprocessing
import re
import os
from setuptools import setup, find_packages

assert multiprocessing
module_name = "malcolm"


def get_version():
    """Extracts the version number from the version.py file.
    """
    VERSION_FILE = os.path.join(module_name, 'version.py')
    txt = open(VERSION_FILE).read()
    mo = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]', txt, re.M)
    if mo:
        version = mo.group(1)
        bs_version = os.environ.get('MODULEVER', '0.0')
        assert bs_version == "0.0" or bs_version == version, \
            "Version {} specified by the build system doesn't match {} in " \
            "version.py".format(bs_version, version)
        return version
    else:
        raise RuntimeError('Unable to find version string in {0}.'
                           .format(VERSION_FILE))

install_requires = [
    'enum34==1.1.6', "numpy==1.13.1", "annotypes==0.17", "cothread==2.14"]


def add_multiversion_require(module):
    try:
        # Can we import it?
        __import__(module)
    except ImportError:
        try:
            # What about if we require?
            from pkg_resources import require
            require(module)
        except Exception:
            pass
        else:
            # So it is there if we require, lets use it
            global install_requires
            install_requires.append(module)


add_multiversion_require("tornado")
add_multiversion_require("ruamel.yaml")
add_multiversion_require("h5py")
add_multiversion_require("p4p")
add_multiversion_require("pygelf")
add_multiversion_require("plop")
add_multiversion_require("scanpointgenerator")
add_multiversion_require("vdsgen")

packages = [x for x in find_packages() if x.startswith("malcolm")]
setup(
    name=module_name,
    version=get_version(),
    description='Scanning in the middlelayer',
    long_description=open("README.rst").read(),
    url='https://github.com/dls-controls/pymalcolm',
    author='Tom Cobb',
    author_email='tom.cobb@diamond.ac.uk',
    keywords='',
    packages=packages,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    license='APACHE',
    install_requires=install_requires,
    extras_require={
        'websocket':  ['tornado'],
        'ca': ['cothread'],
        'hdf5': ['h5py', 'vds-gen'],
    },
    include_package_data=True,
    package_data={'malcolm': ['modules/*/*/*.yaml', 'modules/*/*/*.svg']},
    data_files=[
        ('', ['README.rst', 'CHANGELOG.rst', 'LICENSE'])
    ],
    test_suite='nose.collector',
    tests_require=[
 #       'coverage>=3.7.1',
 #       'mock>=1.0.1',
        'nose>=1.3.0',
    ],
    zip_safe=False,
    entry_points={'console_scripts':
                  ["imalcolm = malcolm.imalcolm:main"]
                  },
)
