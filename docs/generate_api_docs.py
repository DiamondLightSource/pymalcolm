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
        api_docs.write(".. module:: malcolm.modules\n\n")

        modules_root = os.path.join(repo_root, "malcolm", "modules")

        # Add the toctree
        api_docs.write(".. toctree::\n")
        api_docs.write("    :maxdepth: 1\n\n")

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
                documents = [
                    x[:-4] for x in os.listdir(docs_dir) if x.endswith(".rst")]
            else:
                os.mkdir(docs_build)
                documents = []
            dirs = sorted(os.listdir(module_root))
            # Make any parameters and defines docs
            for fname in ["parameters.py", "defines.py", "hooks.py", "infos.py",
                          "util.py"]:
                docname = "%s_api" % fname[:-3]
                if fname in dirs and docname not in documents:
                    # Make document for module
                    section = "malcolm.modules.%s.%s" % (modulename, fname[:-3])
                    make_automodule_doc(section, docs_build)
                    documents.append(docname)
            for dirname in ["blocks", "includes", "controllers", "parts"]:
                docname = "%s_api" % dirname
                if dirname in dirs and docname not in documents:
                    # Make document for module
                    section = "malcolm.modules.%s.%s" % (modulename, dirname)
                    make_automodule_doc(section, docs_build)
                    documents.append(docname)
            # Make the index if it doesn't exist
            if documents and "index" not in documents:
                make_index_doc(modulename, docs_build, documents)
            # Add to top level page
            if documents:
                api_docs.write("    %s/index\n" % modulename)


def make_automodule_doc(section, docs_build):
    docname = section.rsplit(".")[-1]
    with open(os.path.join(docs_build, docname + "_api.rst"), "w") as f:
        f.write(section + "\n")
        f.write("=" * len(section) + "\n\n")
        f.write(".. automodule:: %s\n" % section)
        f.write("    :members:\n")


def make_index_doc(modulename, docs_build, doc_dirs):
    with open(os.path.join(docs_build, "index.rst"), "w") as f:
        f.write(modulename + "\n")
        f.write("=" * len(modulename) + "\n\n")
        f.write(".. module:: malcolm.modules.%s\n\n" % modulename)
        f.write(".. toctree::\n")
        f.write("    :maxdepth: 1\n")
        f.write("    :caption: malcolm.modules.%s\n\n" % modulename)
        for doc in doc_dirs:
            f.write("    %s <%s>\n" % (doc[:-4], doc))


if __name__ == "__main__":
    generate_docs()
