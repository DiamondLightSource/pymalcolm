from annotypes import add_call_types

from malcolm.core import Context, Queue
from malcolm.modules import builtin
from malcolm.modules.scanning.controllers import RunnableController
from malcolm.modules.scanning.hooks import (
    ConfigureHook,
    PostConfigureHook,
    PreConfigureHook,
    ReportStatusHook,
)
from malcolm.modules.scanning.util import ConfigureParams, RunnableStates

ss = RunnableStates


class EthercatContinuousRunnableController(RunnableController):
    def do_configure(self, state: str, params: ConfigureParams) -> None:
        if state == ss.FINISHED:
            # If we were finished then do a reset before configuring
            self.run_hooks(
                builtin.hooks.ResetHook(p, c)
                for p, c in self.create_part_contexts().items()
            )
        # Clear out any old part contexts now rather than letting gc do it
        for context in self.part_contexts.values():
            context.unsubscribe_all()
        # These are the part tasks that abort() and pause() will operate on
        self.part_contexts = self.create_part_contexts()
        # So add one for ourself too so we can be aborted
        assert self.process, "No attached process"
        self.part_contexts[self] = Context(self.process)
        # Store the params for use in seek()
        self.configure_params = params
        # Tell everything to get into the right state to Configure
        self.run_hooks(PreConfigureHook(p, c) for p, c in self.part_contexts.items())
        # This will calculate what we need from the generator, possibly a long
        # call
        params.generator.prepare()
        # Set the steps attributes that we will do across many run() calls
        self.total_steps.set_value(1)
        self.completed_steps.set_value(0)
        self.configured_steps.set_value(1)
        # No reporting of steps so set to 0
        self.steps_per_run = 0
        # Get any status from all parts
        part_info = self.run_hooks(
            ReportStatusHook(p, c) for p, c in self.part_contexts.items()
        )
        # Run the configure command on all parts, passing them info from
        # ReportStatus. Parts should return any reporting info for PostConfigure
        completed_steps = 0
        steps_to_do = 1
        part_info = self.run_hooks(
            ConfigureHook(p, c, completed_steps, steps_to_do, part_info, **kw)
            for p, c, kw in self._part_params()
        )
        # Take configuration info and reflect it as attribute updates
        self.run_hooks(
            PostConfigureHook(p, c, part_info) for p, c in self.part_contexts.items()
        )
        # Update the completed and configured steps to say we are now done
        self.configured_steps.set_value(steps_to_do)
        self.completed_steps.set_value(steps_to_do)
        self.completed_steps.meta.display.set_limitHigh(steps_to_do)
        # Reset the progress of all child parts
        self.progress_updates = {}
        self.resume_queue = Queue()

    @add_call_types
    def pause(self) -> None:
        pass

    @add_call_types
    def resume(self) -> None:
        pass
