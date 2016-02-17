Contributing
============

Contributions and issues are most welcome! All issues and pull requests are
handled through github on the `dls_controls repository`_. Also, please check for
any existing issues before filing a new one. If you have a great idea but it
involves big changes, please file a ticket before making a pull request! We
want to make sure you don't spend your time coding something that might not fit
the scope of the project.

.. _dls_controls repository: https://github.com/dls-controls/malcolm/issues

Running the tests
-----------------

To get the source source code and run the unit tests, run::

    $ git clone git://github.com/dls_controls/malcolm.git
    $ cd malcolm
    $ virtualenv env
    $ . env/bin/activate
    $ pip install nose
    $ python setup.py install
    $ python setup.py nosetests

While 100% code coverage does not make a library bug-free, it significantly
reduces the number of easily caught bugs! Please make sure coverage is at 100%
before submitting a pull request!

Code Quality
------------

For code quality, please run flake8::

    $ pip install flake8
    $ flake8 .

Code Styling
------------
Please arrange imports with the following style

.. code-block:: python

    # Standard library imports
    import os

    # Third party package imports
    from mock import patch

    # Local package imports
    from malcolm.version import __version__

Please follow `Google's python style`_ guide wherever possible.

.. _Google's python style: http://google-styleguide.googlecode.com/svn/trunk/pyguide.html

Building the docs
-----------------

When in the project directory::

    $ pip install -r requirements/docs.txt
    $ python setup.py build_sphinx
    $ open docs/_build/html/index.html

Release Checklist
-----------------

Before a new release, please go through the following checklist:

* Bump version in malcolm/version.py
* Add a release note in CHANGELOG.rst
* Git tag the version
* Upload to pypi::

    make publish

