import os


def generate_docs():

    repo_root = os.path.abspath('../')

    # open the .rst file
    api_docs = open(repo_root + '/docs/dev/api.rst', 'w')

    # add header
    api_docs.write('Malcolm API\n===========\n\n')

    modules_root = repo_root + '/malcolm'
    # create entries in the .rst file for each module

    excluded_files = ['__init__.py']

    for root, _, modules in os.walk(modules_root, topdown=True):
        modules.sort()
        if '__' not in root and len(root.split("pymalcolm/malcolm/")) > 1:
            modules[:] = [m for m in modules if m.split('.')[-1] == 'py']
            modules[:] = [m for m in modules if m not in excluded_files]

            add_module_entry(api_docs, root, modules)

    add_indices_and_tables(api_docs)


def add_module_entry(module, _root, modules_list):
    pkg_path = _root.split('pymalcolm/malcolm/')[1]
    sub_section = pkg_path.replace('/', '.')

    module.write(sub_section.capitalize() + '\n' + '-' * len(sub_section) + '\n')
    module.write('\n..  toctree::\n')

    for file_ in modules_list:
        file_path = sub_section + '_api/' + file_
        module.write(' ' * 4 + file_path.split('.py')[0] + '\n')
    module.write('\n\n')


def add_indices_and_tables(f):
    f.write('Indices and tables\n')
    f.write('==================\n')
    f.write('* :ref:`genindex`\n')
    f.write('* :ref:`modindex`\n')
    f.write('* :ref:`search`\n')

if __name__ == "__main__":
    generate_docs()
