controllers
===========

.. module:: malcolm.modules.builtin.controllers

.. autoclass:: ServerComms
    :members:

.. autoclass:: ClientComms
    :members:

.. autoclass:: BasicController
    :members:

.. autoclass:: ProxyController
    :members:

.. autoclass:: StatefulStates
    :members:

    This state set covers controllers and parts that can be disabled and have
    faults, but otherwise have no state. Unlabelled transitions take place in
    response to internal actions, labelled transitions are triggered externally.

    .. digraph:: stateful_states

        bgcolor=transparent
        compound=true
        rankdir=LR
        node [fontname=Arial fontsize=10 shape=Mrecord style=filled fillcolor="#8BC4E9"]
        graph [fontname=Arial fontsize=11]
        edge [fontname=Arial fontsize=10 arrowhead=vee]
        Fault [fillcolor="#F03232"]
        Disabled [fillcolor="#AAAAAA"]

        subgraph cluster_normal {
            Ready [fillcolor="#BBE7BB"]
            Resetting -> Ready
        }
        Resetting -> Disabling [ltail=cluster_normal label="disable()"]
        Resetting -> Fault [ltail=cluster_normal label="on_error"]

        Fault -> Resetting [label="reset()"]
        Fault -> Disabling [label="disable()"]
        Disabling -> Fault [label="on_error"]
        Disabling -> Disabled
        Disabled -> Resetting [label="reset()"]

.. autoclass:: StatefulController
    :members:

.. autoclass:: ManagerStates
    :members:

    This state set covers controllers and parts that have loadable and savable
    child state. Unlabelled transitions take place in response to internal
    actions, labelled transitions are triggered externally.

    .. digraph:: manager_states

        bgcolor=transparent
        compound=true
        rankdir=LR
        node [fontname=Arial fontsize=10 shape=Mrecord style=filled fillcolor="#8BC4E9"]
        graph [fontname=Arial fontsize=11]
        edge [fontname=Arial fontsize=10 arrowhead=vee]
        Fault [fillcolor="#F03232"]
        Disabled [fillcolor="#AAAAAA"]

        subgraph cluster_normal {
            Ready [fillcolor="#BBE7BB"]
            Ready -> Saving [label="save()"]
            Saving -> Ready [weight=0]
            Ready -> Loading [label="put\ndesign"]
            Loading -> Ready [weight=0]
            Resetting -> Ready
        }
        Resetting -> Disabling [ltail=cluster_normal label="disable()"]
        Resetting -> Fault [ltail=cluster_normal label="on_error"]

        Fault -> Resetting [label="reset()"]
        Fault -> Disabling [label="disable()"]
        Disabling -> Fault [label="on_error"]
        Disabling -> Disabled
        Disabled -> Resetting [label="reset()"]

.. autoclass:: ManagerController
    :members:
