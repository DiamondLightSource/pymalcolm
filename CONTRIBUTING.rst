Contributing
============

Contributions and issues are most welcome! All issues and pull requests are
handled through github on the `dls_controls repository`_. Also, please check for
any existing issues before filing a new one. If you have a great idea but it
involves big changes, please file a ticket before making a pull request! We
want to make sure you don't spend your time coding something that might not fit
the scope of the project.

.. _dls_controls repository: https://github.com/dls-controls/pymalcolm/issues

Setup
-----

The simplest way to set up the Python environment is with pipenv_.

Then all you need to do is download the source code and create the environment
with developer packages::

    $ git clone git://github.com/dls-controls/pymalcolm.git
    $ cd pymalcolm
    $ pipenv install --dev

.. _pipenv: https://www.python.org/dev/peps/pep-0440

Running the tests
-----------------

Once the environment is created tests can be run using pipenv::

    $ pipenv run tests


While 100% code coverage does not make a library bug-free, it significantly
reduces the number of easily caught bugs! Please make sure coverage remains the
same or is improved by a pull request!

Code Styling
------------
Black and isort are used to format the code and order imports to a consistent
style. Running these commands will reformat code and reorder imports for you::

    $ pipenv run black malcolm/ tests/
    $ pipenv run isort malcolm/ tests/

Flake8 is then used to check the formatting to ensure conventions such
as PEP8 are followed. There is a script in the Pipfile so it can be run with::

    $ pipenv run flake8

Finally, Mypy is used as a type checker.::

    $ pipenv run mypy malcolm/ tests/

Mypy, isort and Black checks are performed as part of running the tests. Flake8
is checked separately. Both sets of checks are run in CI jobs when commits are
pushed to GitHub using GitHub Actions.

It is reccommended to perform these checks before committing to ensure your
code is correctly formatted and there are no typing issues.

References:

* Black: https://black.readthedocs.io/en/stable/
* isort: https://pycqa.github.io/isort/
* Flake8: https://flake8.pycqa.org/en/latest/
* Mypy: https://mypy.readthedocs.io/en/stable/

Docs follow the underlining convention::

    Headling 1 (page title)
    =======================

    Heading 2
    ---------

    Heading 3
    ~~~~~~~~~

Coding Conventions
------------------

Any class that takes Annotypes in __init__() will either define those Annotypes
or import them from its superclass. The Annotypes should all appear in the
Class namespace so that any further subclasses can in turn import the
necessary types. To facilitate this and create a tidy namespace, use import
in __init__.py. To allow 're-import' of the superclass symbols, it is
necessary to pull them into a variable local to the namespace (in fact this
is only required for the IDE, but also shows more explicitly what we are doing).

For example, in malcolm.modules.builtin.blockpart create copies of the
imported Annotypes (The comment is also a convention):

.. code-block:: python

    from ..util import set_tags, AWriteable, AConfig, AGroup, AWidget

    with Anno("Initial value of the created attribute"):
        AValue = str

    # Pull re-used annotypes into our namespace in case we are subclassed
    APartName = APartName
    AMetaDescription = AMetaDescription
    AWriteable = AWriteable
    AConfig = AConfig
    AGroup = AGroup
    AWidget = AWidget

Next import all the Annotypes from blockpart and its superclasses in
malcolm.modules.builtin.__init__.py:

.. code-block:: python

    from .blockpart import BlockPart, APartName, AMetaDescription, AWriteable, \
    AConfig, AGroup, AWidget

When importing from core.modules, import the entire module only. This
means that all references to the contents of this module will then have an
explicit module namespace. e.g.:

.. code-block:: python

    from malcolm.modules import builtin, scanning

    def setup(self, registrar):
        registrar.hook(scanning.hooks.ConfigureHook, self.configure)

Note that this does not apply when importing symbols from other files within
the same malcolm module. In this case use relative imports (importing a
parent module is a circular import).
e.g. in malcolm.modules.demo.filewriterpart.py:

.. code-block:: python

    from ..util import make_gaussian_blob, interesting_pattern


When implementing a part do all hook registration using registrar.hook
in the setup function (not in __init__). e.g.:

.. code-block:: python

    class MotionChildPart(builtin.parts.ChildPart):
        """Provides control of a `counter_block` within a `RunnableController`"""
        # Generator instance
        _generator = None  # type: scanning.hooks.AGenerator
        # Where to start
        _completed_steps = None  # type: int
        # How many steps to do
        _steps_to_do = None  # type: int
        # When to blow up
        _exception_step = None  # type: int
        # Which axes we should be moving
        _axes_to_move = None  # type: scanning.hooks.AAxesToMove

        def setup(self, registrar):
            # type: (PartRegistrar) -> None
            super(MotionChildPart, self).setup(registrar)
            # Hooks
            registrar.hook(scanning.hooks.PreConfigureHook, self.reload)
            registrar.hook((scanning.hooks.ConfigureHook,
                            scanning.hooks.PostRunArmedHook,
                            scanning.hooks.SeekHook), self.configure)
            registrar.hook(scanning.hooks.RunHook, self.run)
            # Tell the controller to expose some extra configure parameters
            registrar.report(scanning.hooks.ConfigureHook.create_info(
                self.configure))

Also do not override __init__() just to declare Attributes,
instead declare them at the class level and initialise to None, then
create the Attribute model in setup.

TODO: add convenience for supplying private properties as per MotionChildPart

.. code-block:: python

    class CounterPart(Part):
        """Defines a counter `Attribute` with zero and increment `Method` objects"""

        #: Writeable Attribute holding the current counter value
        counter = None  # type: AttributeModel
        #: Writeable Attribute holding the amount to increment() by
        delta = None  # type: AttributeModel

        def setup(self, registrar):
            # type: (PartRegistrar) -> None
            super(CounterPart, self).setup(registrar)
            # Add some Attribute and Methods to the Block
            self.counter = NumberMeta(
                "float64", "The current value of the counter",
                tags=[config_tag(), Widget.TEXTINPUT.tag()]
            ).create_attribute_model()
            registrar.add_attribute_model(
                "counter", self.counter, self.counter.set_value)

            self.delta = NumberMeta(
                "float64", "The amount to increment() by",
                tags=[config_tag(), Widget.TEXTINPUT.tag()]
            ).create_attribute_model(initial_value=1)
            registrar.add_attribute_model(
                "delta", self.delta, self.delta.set_value)


Building the docs
-----------------

When in the project directory::

    $ pip install -r requirements/docs.txt
    $ python setup.py build_sphinx
    $ firefox docs/_build/html/index.html

Release Checklist
-----------------

Before a new release, please go through the following checklist:

* Choose a new PEP440_ compliant release number (but with dashes until we move to python3)
* Add a release note in CHANGELOG.rst
* Git tag the version with message from CHANGELOG
* Push to github and travis will make a release on pypi
* Push to internal gitlab and do a dls-release.py of the tag

.. _PEP440: https://www.python.org/dev/peps/pep-0440
