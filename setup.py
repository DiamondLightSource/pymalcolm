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
    # External
    "enum34==1.1.6",
    "tornado>=5.1.1",
    "numpy==1.16.4",
    "ruamel.yaml==0.15.97",
    "h5py==2.9.0",
    "p4p==3.3.2",
    "pygelf==0.3.5",
    "plop==0.3.0",
    "typing==3.6.1",
    # DLS developed
    "annotypes==0.20",
    "cothread==2.16",
    "scanpointgenerator==2.3",
    "vdsgen==0.5.2",
    ]

tests_require = [
    'mock>=2.0.0', 'nose>=1.3.0', 'coverage>=3.7.1', 'pytest>=3.10.1',
    'pytest-cov>=2.6.1']

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
        'test': tests_require
    },
    include_package_data=True,
    package_data={'malcolm': ['modules/*/*/*.yaml', 'modules/*/*/*.svg']},
    data_files=[
        ('', ['README.rst', 'CHANGELOG.rst', 'LICENSE'])
    ],
    test_suite='nose.collector',
    tests_require=tests_require,
    zip_safe=False,
    entry_points={'console_scripts':
                  ["imalcolm = malcolm.imalcolm:main"]
                  },
)
