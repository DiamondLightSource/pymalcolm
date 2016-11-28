# -*- coding: utf-8 -*-
#
# malcolm documentation build configuration file

import os
import re
import sys

from pkg_resources import require
require('mock')
from mock import MagicMock

# Mock out failing imports
MOCK_MODULES = ["tornado", "tornado.websocket", "tornado.websocket",
                "tornado.web", "tornado.httpserver", "tornado.ioloop",
                "cothread", "scanpointgenerator"]
sys.modules.update((mod_name, MagicMock()) for mod_name in MOCK_MODULES)

sys.path.append(os.path.dirname(__file__))
from generate_api_docs import generate_docs

generate_docs()  # Generate api.rst

def get_version():
    """
    Extracts the version number from the version.py file.
    """
    VERSION_FILE = '../malcolm/version.py'
    mo = re.search(
        r'^__version__ = [\'"]([^\'"]*)[\'"]', open(VERSION_FILE, 'rt').read(), re.M)
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
    require("sphinxcontrib-plantuml")
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..')))

# -- General configuration ------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinxcontrib.plantuml',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'IPython.sphinxext.ipython_console_highlighting',
]

# http://twistedmatrix.com/trac/browser/tags/releases/twisted-8.2.0/twisted/python/procutils.py?format=txt
def which(name, flags=os.X_OK):
    """Search PATH for executable files with the given name.

    On newer versions of MS-Windows, the PATHEXT environment variable will be
    set to the list of file extensions for files considered executable. This
    will normally include things like ".EXE". This fuction will also find files
    with the given name ending with any of these extensions.

    On MS-Windows the only flag that has any meaning is os.F_OK. Any other
    flags will be ignored.

    @type name: C{str}
    @param name: The name for which to search.

    @type flags: C{int}
    @param flags: Arguments to L{os.access}.

    @rtype: C{list}
    @param: A list of the full paths to files found, in the
    order in which they were found.
    """
    result = []
    exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))
    path = os.environ.get('PATH', None)
    if path is None:
        return []
    for p in os.environ.get('PATH', '').split(os.pathsep):
        p = os.path.join(p, name)
        if os.access(p, flags):
            result.append(p)
        for e in exts:
            pext = p + e
            if os.access(pext, flags):
                result.append(pext)
    return result

here = os.path.abspath(os.path.dirname(__file__))

if not which("plantuml"):
    # For github
    import subprocess
    print "download plantuml..."
    here_plantuml = os.path.join(here, "plantuml_downloaded.jar")
    url = "http://downloads.sourceforge.net/project/plantuml/plantuml.8045.jar"
    subprocess.call(["curl", "-v", "-L", url, "-o", here_plantuml])
    print "download java..."
    here_jre_tar = os.path.join(here, "jre.tar.gz")
    url = "http://download.oracle.com/otn-pub/java/jdk/8u65-b17/jre-8u65-linux-x64.tar.gz"
    subprocess.call(["curl", "-v", "-j", "-k", "-L", "-H", "Cookie: oraclelicense=accept-securebackup-cookie", url, "-o", here_jre_tar])
    print "unzip java..."
    subprocess.call(["/bin/tar", "xvzf", here_jre_tar])
    here_jre = os.path.join(here, "jre1.8.0_65")
    os.environ["JAVA_HOME"] = here_jre
    plantuml = '%s/bin/java -Dplantuml.include.path=%s/.. -jar %s' % (here_jre, here, here_plantuml)
    print "done prep plantuml"
    # get the right font
    fontdir = os.path.expanduser("~/.fonts")
    try:
        os.mkdir(fontdir)
    except OSError:
        pass
    import urllib
    url = "https://github.com/shreyankg/xkcd-desktop/raw/master/Humor-Sans.ttf"
    urllib.urlretrieve(url, os.path.join(fontdir, "Humor-Sans.ttf"))
    # install it
    subprocess.call(["fc-cache", "-vf", fontdir])

napoleon_use_ivar = True

autoclass_content = "both"

autodoc_member_order = 'bysource'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

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

intersphinx_mapping = {
    'python': ('http://docs.python.org/2.7/', None),
}

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# on_rtd is whether we are on readthedocs.org
import os
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

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
