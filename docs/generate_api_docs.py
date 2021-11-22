import os
import shutil

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
build_dir = os.path.join(repo_root, "docs", "build")
modules_root = os.path.join(repo_root, "malcolm", "modules")


def generate_docs():
    # Add entries for each module
    modules = []

    for modulename in sorted(os.listdir(modules_root)):
        # Ignore files
        if not os.path.isdir(os.path.join(modules_root, modulename)):
            continue
        module_build_dir = os.path.join(build_dir, modulename)

        # Copy across any files that are in the docs dir of the module
        module_docs = os.path.join(modules_root, modulename, "docs")
        manual_gen_docs = []
        if os.path.isdir(module_docs):
            for fname in os.listdir(module_docs):
                src_path = os.path.join(module_docs, fname)
                dest_path = os.path.join(module_build_dir, fname)
                if os.path.isfile(src_path):
                    with open(src_path) as f:
                        text = f.read()
                    write_if_different(dest_path, text)
                    manual_gen_docs.append(fname)

        # Walk the tree finding documents that need to exist
        # {doc_name: rst_name}
        documents = {}
        dirs = sorted(os.listdir(os.path.join(modules_root, modulename)))

        # Make any parameters and defines docs
        for fname in [
            "parameters.py",
            "defines.py",
            "infos.py",
            "util.py",
            "hooks.py",
            "blocks",
            "includes",
            "controllers",
            "parts",
        ]:
            if fname in dirs:
                if fname.endswith(".py"):
                    doc_name = fname[:-3]
                else:
                    doc_name = fname
                rst_name = doc_name + "_api.rst"
                documents[doc_name] = rst_name
                if rst_name not in manual_gen_docs:
                    # Make one up
                    section = "malcolm.modules.%s.%s" % (modulename, doc_name)
                    rst_path = os.path.join(module_build_dir, rst_name)
                    make_automodule_doc(section, rst_path)

        # Add an index if we need to
        if "index.rst" in manual_gen_docs:
            got_index = True
        elif documents:
            # Or make one up
            rst_path = os.path.join(module_build_dir, "index.rst")
            make_index_doc(modulename, rst_path, documents)
            got_index = True
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
""" % dict(
        section=section, underline="=" * len(section)
    )

    write_if_different(rst_path, text)


def make_index_doc(modulename, rst_path, documents):
    text = """
%(modulename)s
%(underline)s

.. module:: malcolm.modules.%(modulename)s

.. toctree::
    :maxdepth: 1
    :caption: malcolm.modules.%(modulename)s

""" % dict(
        modulename=modulename, underline="=" * len(modulename)
    )

    for doc_name, rst_name in sorted(documents.items()):
        text += "    %s <%s>\n" % (doc_name, rst_name)

    write_if_different(rst_path, text)


def write_if_different(path, text):
    if os.path.exists(path):
        with open(path) as current:
            different = current.read() != text
    else:
        different = True
    if different:
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(path, "w") as updated:
            updated.write(text)


if __name__ == "__main__":
    generate_docs()
