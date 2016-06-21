from malcolm.core.statemachine import StateMachine


class RunnableDeviceStateMachine(StateMachine):

    IDLE = "Idle"
    CONFIGURING = "Configuring"
    PRERUN = "PreRun"
    RUNNING = "Running"
    POSTRUN = "PostRun"
    PAUSED = "Paused"
    REWINDING = "Rewinding"
    ABORTING = "Aborting"
    ABORTED = "Aborted"

    def __init__(self, name):
        super(RunnableDeviceStateMachine, self).__init__(name)
        
        a = self.set_allowed

        # Set transitions for normal states
        a(self.IDLE, self.CONFIGURING)
        a(self.READY, [self.PRERUN, self.REWINDING, self.RESETTING])
        a(self.CONFIGURING, self.READY)
        a(self.PRERUN, [self.RUNNING, self.REWINDING])
        a(self.RUNNING, [self.POSTRUN, self.REWINDING])
        a(self.POSTRUN, [self.IDLE, self.READY])
        a(self.RESETTING, self.IDLE)
        a(self.PAUSED, [self.REWINDING, self.PRERUN])
        a(self.REWINDING, self.PAUSED)

        # Add Aborting to all normal states
        normal_states = [self.IDLE, self.READY, self.CONFIGURING, self.PRERUN,
                         self.RUNNING, self.POSTRUN, self.PAUSED,
                         self.RESETTING, self.REWINDING]
        for state in normal_states:
            a(state, self.ABORTING)

        # Set transitions for other states
        a(self.ABORTING, self.ABORTED)
        a(self.ABORTED, self.RESETTING)
