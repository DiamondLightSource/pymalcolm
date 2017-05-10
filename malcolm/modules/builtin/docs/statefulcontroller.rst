StatefulStates and StatefulController
-------------------------------------

.. module:: malcolm.modules.builtin.controllers

.. autoclass:: StatefulStates
    :members:

    This state set covers controllers and parts that can be disabled and reset,
    and that can enter an error state. Unlabelled transitions take place in
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
        {rank=min Disabled Resetting}
        {rank=max Fault}
        Resetting -> Disabling [ltail=cluster_normal label="disable()"]
        Ready -> Fault [ltail=cluster_normal label="on_error"]

        Fault -> Resetting [label="reset()"]
        Fault -> Disabling [label="disable()"]
        Disabling -> Fault [label="on_error"]
        Disabling -> Disabled
        Disabled -> Resetting [label="reset()"]


.. autoclass:: StatefulController
    :members:
