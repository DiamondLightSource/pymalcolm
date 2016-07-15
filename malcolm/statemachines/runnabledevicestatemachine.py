from malcolm.core.statemachine import StateMachine


class RunnableDeviceStateMachine(StateMachine):

    READY = "Ready"
    IDLE = "Idle"
    CONFIGURING = "Configuring"
    PRERUN = "PreRun"
    RUNNING = "Running"
    POSTRUN = "PostRun"
    PAUSED = "Paused"
    REWINDING = "Rewinding"
    ABORTING = "Aborting"
    ABORTED = "Aborted"

    AFTER_RESETTING = IDLE

    def create_states(self):
        # Set transitions for normal states
        self.set_allowed(self.IDLE, self.CONFIGURING)
        self.set_allowed(
            self.READY, [self.PRERUN, self.REWINDING, self.RESETTING])
        self.set_allowed(self.CONFIGURING, self.READY)
        self.set_allowed(self.PRERUN, [self.RUNNING, self.REWINDING])
        self.set_allowed(self.RUNNING, [self.POSTRUN, self.REWINDING])
        self.set_allowed(self.POSTRUN, [self.IDLE, self.READY])
        self.set_allowed(self.PAUSED, [self.REWINDING, self.PRERUN])
        self.set_allowed(self.REWINDING, self.PAUSED)

        # Add Aborting to all normal states
        normal_states = [self.IDLE, self.READY, self.CONFIGURING, self.PRERUN,
                         self.RUNNING, self.POSTRUN, self.PAUSED,
                         self.RESETTING, self.REWINDING]
        for state in normal_states:
            self.set_allowed(state, self.ABORTING)

        # Set trself.set_allowednsitions for other stself.set_allowedtes
        self.set_allowed(self.ABORTING, self.ABORTED)
        self.set_allowed(self.ABORTED, self.RESETTING)
