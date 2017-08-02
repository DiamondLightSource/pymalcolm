controllers
===========

.. module:: malcolm.modules.scanning.controllers

.. autoclass:: RunnableStates
    :members:

    This state set covers controllers and parts that can be configured and then
    run, and have the ability to pause and rewind. Unlabelled transitions take
    place in response to internal actions, labelled transitions are triggered
    externally.

    .. digraph:: runnable_states

        bgcolor=transparent
        compound=true
        rankdir=LR
        node [fontname=Arial fontsize=10 shape=Mrecord style=filled fillcolor="#8BC4E9"]
        graph [fontname=Arial fontsize=11]
        edge [fontname=Arial fontsize=10 arrowhead=vee]
        Fault [fillcolor="#F03232"]
        Disabled [fillcolor="#AAAAAA"]

        subgraph cluster_normal {
            subgraph cluster_abortable {
                {rank=min Ready}
                {rank=same Configuring Loading Saving}
                {rank=same Armed Seeking}
                {rank=max Running Paused PostRun}
                Ready [fillcolor="#BBE7BB"]
                Ready -> Configuring [label="configure()" weight=30]
                Ready -> Saving [label="save()"]
                Saving -> Ready [weight=0]
                Ready -> Loading [label="put\ndesign"]
                Loading -> Ready [weight=0]
                Armed [fillcolor="#BBE7BB"]
                Configuring -> Armed
                Armed -> Running [label="run()"]
                Armed -> Seeking [label="put\nsteps"]
                Running -> PostRun
                Running -> Seeking [label="pause()"]
                PostRun -> Ready [weight=30]
                PostRun -> Armed
                Seeking -> Armed
                Seeking -> Paused
                Paused -> Seeking [label="put\nsteps"]
                Paused -> Running [label="resume()"]
            }
            Aborted [fillcolor="#FFBE89"]
            Resetting -> Ready
            Ready -> Aborting [ltail=cluster_abortable label="abort()"]
            Aborting -> Aborted
            Aborted -> Resetting
        }
        Aborting -> Disabling [ltail=cluster_normal label="disable()"]
        Aborted -> Fault [ltail=cluster_normal label="on_error"]

        Fault -> Resetting [label="reset()"]
        Fault -> Disabling [label="disable()"]
        Disabling -> Fault [label="on_error"]
        Disabling -> Disabled
        Disabled -> Resetting [label="reset()"]

.. autoclass:: RunnableController
    :members:


