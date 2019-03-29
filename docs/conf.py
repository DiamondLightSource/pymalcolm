# -*- coding: utf-8 -*-
#
# malcolm documentation build configuration file
import inspect
import os
import re
import sys

def get_version():
    """Extracts the version number from the version.py file."""
    VERSION_FILE = '../malcolm/version.py'
    mo = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]',
                   open(VERSION_FILE, 'rt').read(), re.M)
    if mo:
        return mo.group(1)
    else:
        raise RuntimeError(
            'Unable to find version string in {0}.'.format(VERSION_FILE))


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
try:
    from pkg_resources import require
except ImportError:
    pass
else:
    require("mock")
    require("numpy")
    require("ruamel.yaml")
    require("annotypes")
    require("cothread")
    require("enum34")
    require("sphinx_rtd_theme")


from mock import MagicMock
from enum import Enum

# Mock out failing imports
MOCK_MODULES = [
    "scanpointgenerator",
    "p4p", "p4p.nt", "p4p.client", "p4p.client.raw", "p4p.client.cothread",
    "p4p.server", "p4p.server.cothread",
    "plop", "plop.viewer",
    "h5py", "vdsgen", "vdsgen.subframevdsgenerator",
    "tornado", "tornado.options", "tornado.httpserver", "tornado.web",
    "tornado.ioloop", "tornado.websocket"]

sys.modules.update((mod_name, MagicMock()) for mod_name in MOCK_MODULES)


sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))

sys.path.append(os.path.dirname(__file__))


# Autodoc event handlers
def skip_member(app, what, name, obj, skip, options):
    # Override enums to always be documented
    if isinstance(obj, Enum):
        return False


def setup(app):
    app.connect('autodoc-skip-member', skip_member)
    from generate_api_docs import generate_docs
    generate_docs()  # Generate modules_api.rst


# -- General configuration ------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx.ext.inheritance_diagram',
    'sphinx.ext.graphviz',
    'IPython.sphinxext.ipython_console_highlighting',
    'annotypes.sphinxext.call_types'
]

autoclass_content = "both"

autodoc_member_order = 'bysource'

graphviz_output_format = "svg"

# If true, Sphinx will warn about all references where the target can't be found
nitpicky = True

# The name of a reST role (builtin or Sphinx extension) to use as the default
# role, that is, for text marked up `like this`
default_role = "any"

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'contents'

# General information about the project.
project = u'malcolm'
copyright = u'2015, Diamond Light Source'
author = u'Tom Cobb'

# The short X.Y version.
version = get_version()
# The full version, including alpha/beta/rc tags.
release = version

exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

intersphinx_mapping = dict(
    python=('http://docs.python.org/3/', None),
    scanpointgenerator=(
        'http://scanpointgenerator.readthedocs.io/en/latest/', None),
    numpy=('http://docs.scipy.org/doc/numpy/', None),
    tornado=('http://www.tornadoweb.org/en/stable/', None),
    p4p=('http://mdavidsaver.github.io/p4p-dev/', None)
)

# A dictionary of graphviz graph attributes for inheritance diagrams.
inheritance_graph_attrs = dict(rankdir="TB")

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_context = dict(css_files=[])
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]


# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = True

# Output file base name for HTML help builder.
htmlhelp_basename = 'malcolmdoc'

# Logo
html_logo = 'malcolm-logo.svg'
html_favicon = 'malcolm-logo.ico'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    ('contents', 'malcolm.tex', u'malcolm Documentation',
     u'Tom Cobb', 'manual'),
]

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('contents', 'malcolm', u'malcolm Documentation',
     [u'Tom Cobb'], 1)
]

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('contents', 'malcolm', u'malcolm Documentation',
     u'Tom Cobb', 'malcolm', 'A short description',
     'Miscellaneous'),
]

# Common links that should be available on every page
rst_epilog = """
.. _Mapping project:
    https://indico.esss.lu.se/event/357/session/8/contribution/63

.. _EPICS:
    http://www.aps.anl.gov/epics/

.. _PVs:
    https://ics-web.sns.ornl.gov/kasemir/train_2006/1_3_CA_Overview.pdf

.. _GDA:
    http://www.opengda.org/

.. _pvAccess:
    http://epics-pvdata.sourceforge.net/arch.html#Network

.. _websockets:
    https://en.wikipedia.org/wiki/WebSocket

.. _Diamond Light Source:
    http://www.diamond.ac.uk

.. _JSON:
    http://www.json.org/

.. _areaDetector:
    http://cars.uchicago.edu/software/epics/areaDetector.html

.. _YAML:
    https://en.wikipedia.org/wiki/YAML

.. _IPython:
    https://ipython.org

.. _Scan Point Generator:
    http://scanpointgenerator.readthedocs.org/en/latest/writing.html

.. _NeXus:
    http://www.nexusformat.org/

.. _HDF5:
    https://support.hdfgroup.org/HDF5/

"""