import os
import shutil


repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def generate_docs():
    build_dir = os.path.join(repo_root, "docs", "build")
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    # Add entries for each module
    modules = []
    modules_root = os.path.join(repo_root, "malcolm", "modules")
    for modulename in sorted(os.listdir(modules_root)):
        module_root = os.path.join(modules_root, modulename)
        if not os.path.isdir(module_root):
            continue
        # Make sure the directory exists
        docs_build = os.path.join(repo_root, "docs", "build", modulename)
        if not os.path.exists(docs_build):
            os.makedirs(docs_build)
        # Walk the tree finding documents
        # {docname: section}
        documents = {}
        dirs = sorted(os.listdir(module_root))
        # Make any parameters and defines docs
        for fname in ["parameters.py", "defines.py", "hooks.py", "infos.py",
                      "util.py", "blocks", "includes", "controllers", "parts"]:
            if fname in dirs:
                if fname.endswith(".py"):
                    fname = fname[:-3]
                docname = "%s_api" % fname
                section = "malcolm.modules.%s.%s" % (modulename, fname)
                documents[docname] = section

        # Copy from the docs dir if it exists
        docs_dir = os.path.join(module_root, "docs")
        for docname, section in sorted(documents.items()):
            src_path = os.path.join(docs_dir, docname + ".rst")
            rst_path = os.path.join(docs_build, docname + ".rst")
            if os.path.exists(src_path):
                with open(src_path) as rst:
                    text = rst.read()
                write_if_different(rst_path, text)
            else:
                # Or make one up
                make_automodule_doc(section, rst_path)

        # Add an index
        src_path = os.path.join(docs_dir, "index.rst")
        rst_path = os.path.join(docs_build, "index.rst")
        got_index = True
        if os.path.exists(src_path):
            with open(src_path) as rst:
                text = rst.read()
            write_if_different(rst_path, text)
        elif documents:
            # Or make one up
            make_index_doc(modulename, rst_path, documents)
        else:
            got_index = False

        # Add entry to top level page
        if got_index:
            modules.append(modulename)

    text = """
malcolm.modules
===============

.. module:: malcolm.modules

.. toctree::
    :maxdepth: 1
   
"""
    for modulename in modules:
        text += "    %s/index\n" % modulename

    fname = os.path.join(repo_root, "docs", "build", "modules_api.rst")
    write_if_different(fname, text)


def make_automodule_doc(section, rst_path):
    text = """
%(section)s
%(underline)s

.. automodule:: %(section)s
    :members:
""" % dict(section=section, underline="=" * len(section))

    write_if_different(rst_path, text)


def make_index_doc(modulename, rst_path, documents):
    text = """
%(modulename)s
%(underline)s

.. module:: malcolm.modules.%(modulename)s

.. toctree::
    :maxdepth: 1
    :caption: malcolm.modules.%(modulename)s

""" % dict(modulename=modulename, underline="=" * len(modulename))

    for doc in sorted(documents):
        text += "    %s <%s.rst>\n" % (doc, doc)

    write_if_different(rst_path, text)


def write_if_different(path, text):
    with open(path) as current:
        different = current.read() != text
    if different:
        with open(path, "w") as updated:
            updated.write(text)    


if __name__ == "__main__":
    generate_docs()
