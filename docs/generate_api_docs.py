import os
import shutil


repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def generate_docs():
    build_dir = os.path.join(repo_root, "docs", "build")
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)
    os.mkdir(build_dir)

    # open the .rst file
    fname = os.path.join(repo_root, "docs", "build", "modules_api.rst")
    with open(fname, "w") as api_docs:

        # add header
        api_docs.write("malcolm.modules\n")
        api_docs.write("===============\n\n")
        modules_root = os.path.join(repo_root, "malcolm", "modules")

        # Add the toctree
        api_docs.write(".. toctree::\n")
        api_docs.write("    :maxdepth: 1\n")
        api_docs.write("    :caption: malcolm.modules\n\n")

        # Add entries for each module
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
            doc_dirs = []
            # Make any parameters and defines docs
            for fname in ["parameters.py", "defines.py"]:
                if fname in dirs:
                    doc_dirs.append(fname[:-3])
            for dirname in ["blocks", "includes"]:
                if dirname in dirs:
                    # Document all the produced blocks
                    section = "malcolm.modules.%s.%s" % (modulename, dirname)
                    functions = filter_yaml_functions(module_root, dirname)
                    make_yaml_doc(section, docs_build, functions)
                    doc_dirs.append(dirname)
            for dirname in ["controllers", "parts", "infos", "vmetas"]:
                if dirname in dirs:
                    # Only document places we know python files will live
                    doc_dirs.append(dirname)
            # Make the index if it doesn't exist
            if doc_dirs and "index.rst" not in dirs:
                make_index_doc(modulename, docs_build, doc_dirs)
            # Add to top level page
            if doc_dirs:
                api_docs.write("    %s/index\n" % modulename)


def filter_yaml_functions(root, dirname):
    filenames = [f[:-5] for f in sorted(os.listdir(os.path.join(root, dirname)))
                 if f.endswith(".yaml")]
    return filenames


def make_yaml_doc(section, docs_build, functions):
    docname = section.rsplit(".")[-1]
    with open(os.path.join(docs_build, docname + "_api.rst"), "w") as f:
        f.write(docname + "\n")
        f.write("-" * len(docname) + "\n\n")
        f.write(".. module:: %s\n\n" % section)
        for function in functions:
            f.write(".. autofunction:: %s\n\n" % function)


def make_index_doc(modulename, docs_build, doc_dirs):
    with open(os.path.join(docs_build, "index.rst"), "w") as f:
        f.write(modulename + "\n")
        f.write("-" * len(modulename) + "\n\n")
        f.write(".. toctree::\n")
        f.write("    :maxdepth: 1\n")
        f.write("    :caption: malcolm.modules.%s\n\n" % modulename)
        for doc in doc_dirs:
            f.write("    %s_api\n" % doc)


if __name__ == "__main__":
    generate_docs()
