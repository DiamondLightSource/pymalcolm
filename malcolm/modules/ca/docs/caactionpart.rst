CAActionPart
------------

.. module:: malcolm.modules.ca.parts

.. autoclass:: CAActionPart
    :members:

    Commonly a group of pvs are used to represent a method call like this::

        caput(pv, wait=True)
        assert caget(statusPv) == goodStatus

    This `Part` wraps up this design pattern as a Malcolm method
