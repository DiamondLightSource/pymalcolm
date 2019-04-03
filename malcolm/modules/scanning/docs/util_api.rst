util
====

.. automodule:: malcolm.modules.scanning.util
    :members:

.. autoclass:: RunnableStates
    :members:

    This state set covers controllers and parts that can be configured and then
    run, and have the ability to pause and rewind. Unlabelled transitions take
    place in response to internal actions, labelled transitions are triggered
    externally.

    .. digraph:: runnable_states

        newrank=true;  // Sensible ranking of clusters
        bgcolor=transparent
        compound=true
        rankdir=LR
        node [fontname=Arial fontsize=10 shape=rect style=filled fillcolor="#8BC4E9"]
        graph [fontname=Arial fontsize=11]
        edge [fontname=Arial fontsize=10 arrowhead=vee]
        Fault [fillcolor="#F03232"]
        Disabled [fillcolor="#AAAAAA"]

        subgraph cluster_normal {
            subgraph cluster_abortable {
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
                PostRun -> Finished
                PostRun -> Armed
                PostRun -> Seeking [label="pause()"]
                Finished [fillcolor="#BBE7BB"]
                Finished -> Seeking [label="pause()"]
                Finished -> Configuring [label="configure()" weight=30]
                Seeking -> Armed
                Seeking -> Paused
                Paused -> Seeking [label="put\nsteps"]
                Paused -> Running [label="resume()"]
            }
            Aborted [fillcolor="#FFBE89"]
            Resetting -> Ready
            Seeking -> Aborting [ltail=cluster_abortable label="abort()"]
            Aborting -> Aborted
            Aborted -> Resetting [label="reset()"]
            Armed -> Resetting [label="reset()"]
            Finished -> Resetting [label="reset()"]
        }
        Aborted -> Disabling [ltail=cluster_normal label="disable()"]
        Aborted -> Fault [ltail=cluster_normal label="on_error"]

        Fault -> Resetting [label="reset()"]
        Fault -> Disabling [label="disable()"]
        Disabling -> Fault [label="on_error"]
        Disabling -> Disabled
        Disabled -> Resetting [label="reset()"]

        {rank=min Ready Resetting Fault}
        {rank=same Loading Saving Configuring}
        {rank=same Armed Seeking Finished Aborted Disabling}
        {rank=max Paused Running PostRun Aborting Disabled}

