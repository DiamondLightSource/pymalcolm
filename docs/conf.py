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
except:
    pass
else:
    require("mock")
    require("numpy")
    require("ruamel.yaml")

from mock import MagicMock
from annotypes import make_annotations

# Mock out failing imports
MOCK_MODULES = [
    "scanpointgenerator", "pvaccess", "plop", "plop.viewer", "h5py"]

sys.modules.update((mod_name, MagicMock()) for mod_name in MOCK_MODULES)


sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))

sys.path.append(os.path.dirname(__file__))


# Autodoc event handlers
def skip_member(app, what, name, obj, skip, options):
    # Override @add_call_types to always be documented
    if hasattr(obj, "call_types") or hasattr(obj, "return_type"):
        return False


def process_docstring(app, what, name, obj, options, lines):
    # Work out if we need to work out the call types and return types
    needs_call_types = True
    needs_return_type = True
    for line in lines:
        strip = line.strip()
        if strip.startswith(":type"):
            needs_call_types = False
        elif strip.startswith(":rtype"):
            needs_return_type = False
    # If we have annotated with @add_call_types, or this is a WithCallTypes
    # instance, and we need call_types and return_type, make them
    if needs_call_types and hasattr(obj, "call_types"):
        for k, anno in obj.call_types.items():
            lines.append(":param %s: %s" % (k, anno.description))
            typ = getattr(anno.typ, "__name__", None)
            if typ:
                lines.append(":type %s: %s" % (k, typ))
        needs_call_types = False
    if needs_return_type and hasattr(obj, "return_type"):
        # If we have a return type and it isn't the object itself
        rt = obj.return_type
        if rt and rt.typ != obj:
            typ = getattr(rt.typ, "__name__", None)
            if typ:
                # Don't include the return description if no type given
                lines.append(":returns: %s" % rt.description)
                lines.append(":rtype: %s" % typ)
        needs_return_type = False
    # If we have a type comment but no call_types or return_type, process it
    if needs_call_types or needs_return_type:
        if inspect.isclass(obj):
            obj = obj.__init__
        if inspect.isfunction(obj) or inspect.ismethod(obj):
            try:
                annotations = make_annotations(obj)
            except Exception as e:
                raise ValueError("Can't make annotations for %s, %s" % (obj, e))
        else:
            annotations = None
        if annotations:
            for k, v in annotations.items():
                if k == "return":
                    if v and needs_return_type:
                        lines.append(":rtype: %s" % v)
                elif needs_call_types:
                    lines.append(":type %s: %s" % (k, v))


def setup(app):
    app.connect('autodoc-skip-member', skip_member)
    app.connect('autodoc-process-docstring', process_docstring)
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
    python=('https://docs.python.org/2.7/', None),
    scanpointgenerator=(
        'http://scanpointgenerator.readthedocs.io/en/latest/', None),
    numpy=('https://docs.scipy.org/doc/numpy/', None),
    tornado=('http://www.tornadoweb.org/en/stable/', None),
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

.. _decorators:
    https://realpython.com/blog/python/primer-on-python-decorators/

.. _Scan Point Generator:
    http://scanpointgenerator.readthedocs.org/en/latest/writing.html

.. _NeXus:
    http://www.nexusformat.org/

.. _HDF5:
    https://support.hdfgroup.org/HDF5/

"""
