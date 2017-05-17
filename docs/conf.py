# -*- coding: utf-8 -*-
#
# malcolm documentation build configuration file

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

# Mock out failing imports
MOCK_MODULES = []

sys.modules.update((mod_name, MagicMock()) for mod_name in MOCK_MODULES)


sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))

sys.path.append(os.path.dirname(__file__))


# Autodoc event handlers
def skip_member(app, what, name, obj, skip, options):
    # Override @method_takes to always be documented
    if hasattr(obj, "MethodModel") and hasattr(obj.MethodModel, "takes") and \
            obj.MethodModel.takes.elements:
        return False


def process_docstring(app, what, name, obj, options, lines):
    # Add some documentation for @method_takes decorated members
    if hasattr(obj, "MethodModel") and hasattr(obj.MethodModel, "takes") and \
            obj.MethodModel.takes.elements:
        # Add a new docstring
        lines.append("params:")
        for param, vmeta in obj.MethodModel.takes.elements.items():
            lines.append(
                "    - %s (%s):" % (param, vmeta.doc_type_string()))
            description = vmeta.description.strip()
            if not description[-1] in ".?!,":
                description += "."
            if param in obj.MethodModel.takes.required:
                default = "Required"
            elif param in obj.MethodModel.defaults:
                default = "Default=%r" % (obj.MethodModel.defaults[param],)
            else:
                default = "Optional"
            lines.append("        %s %s" % (description, default))
        lines.append("")


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
    ('index', 'malcolm.tex', u'malcolm Documentation',
     u'Tom Cobb', 'manual'),
]

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'malcolm', u'malcolm Documentation',
     [u'Tom Cobb'], 1)
]

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'malcolm', u'malcolm Documentation',
     u'Tom Cobb', 'malcolm', 'A short description',
     'Miscellaneous'),
]
