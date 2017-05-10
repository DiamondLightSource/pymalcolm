import os
import shutil


repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def generate_docs():
    build_dir = os.path.join(repo_root, "docs", "build")
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)
    os.mkdir(build_dir)

    # open the .rst file
    fname = os.path.join(repo_root, "docs", "build", "api.rst")
    with open(fname, 'w') as api_docs:

        # add header
        api_docs.write('Malcolm API\n===========\n\n')
        malcolm_root = os.path.join(repo_root, 'malcolm')

        # add the tags docs
        section = "malcolm"
        docnames = ["tags_api"]
        doc_dir = os.path.join("..", "developer_docs")
        add_module_entry(api_docs, section, doc_dir, docnames)

        # add the core docs
        section = "malcolm.core"
        docnames = filter_py_docnames(malcolm_root, 'core')
        doc_dir = os.path.join("..", "developer_docs", "core_api")
        add_module_entry(api_docs, section, doc_dir, docnames)

        # create entries in the .rst file for each module
        modules_root = os.path.join(malcolm_root, 'modules')
        for modulename in sorted(os.listdir(modules_root)):
            module_root = os.path.join(modules_root, modulename)
            if not os.path.isdir(module_root):
                continue
            # Copy the docs dir if it exists
            docs_build = os.path.join(repo_root, "docs", "build", modulename)
            docs_dir = os.path.join(module_root, "docs")
            if os.path.isdir(docs_dir):
                shutil.copytree(docs_dir, docs_build)
            else:
                os.mkdir(docs_build)
            dirs = sorted(os.listdir(module_root))
            if "parameters.py" in dirs:
                section = "malcolm.modules.%s" % (modulename,)
                docnames = ["parameters"]
                add_module_entry(api_docs, section, modulename, docnames)
            for dirname in ["blocks", "includes"]:
                if dirname in dirs:
                    # Document all the produced blocks
                    section = "malcolm.modules.%s.%s" % (modulename, dirname)
                    docnames = filter_yaml_docnames(module_root, dirname)
                    for docname in docnames:
                        make_yaml_doc(section, docs_build, docname)
                    add_module_entry(api_docs, section, modulename, docnames)
            for dirname in ["controllers", "parts", "infos", "vmetas"]:
                if dirname in dirs:
                    # Only document places we know python files will live
                    section = "malcolm.modules.%s.%s" % (modulename, dirname)
                    docnames = filter_py_docnames(module_root, dirname)
                    add_module_entry(api_docs, section, modulename, docnames)
        add_indices_and_tables(api_docs)


def filter_py_docnames(root, dirname):
    filenames = [f[:-3] for f in sorted(os.listdir(os.path.join(root, dirname)))
                 if f.endswith(".py") and f != "__init__.py"]
    return filenames


def filter_yaml_docnames(root, dirname):
    filenames = [f[:-5] + "_api"
                 for f in sorted(os.listdir(os.path.join(root, dirname)))
                 if f.endswith(".yaml")]
    return filenames


def make_yaml_doc(section, docs_build, docname):
    with open(os.path.join(docs_build, docname + ".rst"), "w") as f:
        docname = docname[:-4]
        f.write(docname + "\n")
        f.write("-" * len(docname) + "\n\n")
        f.write(".. module:: %s\n\n" % section)
        f.write(".. autofunction:: %s\n\n" % docname)


def add_module_entry(api_docs, section, doc_dir, docnames):
    api_docs.write(section + '\n' + '-' * len(section) + '\n')
    api_docs.write('\n..  toctree::\n')
    for docname in docnames:
        api_docs.write(' ' * 4 + os.path.join(doc_dir, docname) + '\n')
    api_docs.write("\n")


def add_indices_and_tables(f):
    f.write('Indices and tables\n')
    f.write('==================\n')
    f.write('* :ref:`genindex`\n')
    f.write('* :ref:`modindex`\n')
    f.write('* :ref:`search`\n')


if __name__ == "__main__":
    generate_docs()
