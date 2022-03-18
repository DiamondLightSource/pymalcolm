.. _infos:

Infos
=====
This page lists all the `Infos <info_>` that are defined internal to Malcolm.
Note that Malcolm enabled support modules may add their own Info
derived classes.

Each module may define Infos for use in the parts it defines or in
other module's parts hosted in the controllers it defines.

builtin module Infos
--------------------

.. automodule:: malcolm.modules.builtin.infos
    :members:
    :noindex:

scanning module Infos
---------------------
These are used by parts hosted in a `RunnableController`

.. automodule:: malcolm.modules.scanning.infos
    :members:
    :noindex:


web module Infos
----------------
These are used by parts hosted in a `HTTPServerComms`.

.. automodule:: malcolm.modules.web.infos
    :members:
    :noindex:

