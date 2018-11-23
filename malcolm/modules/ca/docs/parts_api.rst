parts
=====

.. autoclass:: malcolm.modules.ca.parts.CAActionPart
    :members:

    Commonly a group of pvs are used to represent a method call like this::

        caput(pv, wait=True)
        assert caget(status_pv) == good_status, \
            "Action failed with message: %s" % caget(message_pv)

    This `Part` wraps up this design pattern as a Malcolm `Method`


.. automodule:: malcolm.modules.ca.parts
    :members:
    :exclude-members: CAActionPart
    

