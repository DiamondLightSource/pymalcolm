# import multiprocessing to avoid this bug
# (http://bugs.python.org/issue15881#msg170215)
import multiprocessing
import sys
import os
from setuptools import setup, find_packages

assert multiprocessing
module_name = "malcolm"

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
    "scanpointgenerator==3.0",
    "vdsgen==0.5.2",
    ]

tests_require = [
    'mock>=2.0.0', 'nose>=1.3.0', 'coverage>=3.7.1', 'pytest>=3.10.1',
    'pytest-cov>=2.6.1']

# Place the directory containing _version_git on the path
for path, _, filenames in os.walk(os.path.dirname(os.path.abspath(__file__))):
    if "_version_git.py" in filenames:
        sys.path.append(path)
        break

from _version_git import get_cmdclass, __version__

packages = [x for x in find_packages() if x.startswith("malcolm")]
setup(
    name=module_name,
    cmdclass=get_cmdclass(),
    version=__version__,
    description='Scanning in the middlelayer',
    long_description=open("README.rst").read(),
    url='https://github.com/dls-controls/pymalcolm',
    author='Tom Cobb',
    author_email='tom.cobb@diamond.ac.uk',
    keywords='',
    packages=packages,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
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
