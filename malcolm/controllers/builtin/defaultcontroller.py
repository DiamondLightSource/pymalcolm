from malcolm.core import Controller, DefaultStateMachine, Hook, \
    method_writeable_in, method_takes


sm = DefaultStateMachine


class DefaultController(Controller):
    # The stateMachine that this controller implements
    stateMachine = sm()

    Reset = Hook()
    """Called at reset() to reset all parts to a known good state

    Args:
        context (Task): The context used to perform operations on child blocks
    """

    Disable = Hook()
    """Called at disable() to stop all parts updating their attributes

    Args:
        context (Task): The context used to perform operations on child blocks
    """

    def do_initial_reset(self):
        self.process.spawn(self.reset)

    @method_takes()
    def disable(self):
        self.try_stateful_function(sm.DISABLING, sm.DISABLED, self.do_disable)

    def do_disable(self):
        self.run_hook(self.Disable, self.create_part_tasks())

    @method_writeable_in(sm.DISABLED, sm.FAULT)
    def reset(self):
        self.try_stateful_function(
            sm.RESETTING, self.stateMachine.AFTER_RESETTING, self.do_reset)

    def do_reset(self):
        self.run_hook(self.Reset, self.create_part_tasks())

    def go_to_error_state(self, exception):
        if self.state.value != sm.FAULT:
            self.log_exception("Fault occurred while running stateful function")
            self.transition(sm.FAULT, str(exception))

    def try_stateful_function(self, start_state, end_state, func, *args,
                              **kwargs):
        try:
            self.transition(start_state, start_state)
            func(*args, **kwargs)
            self.transition(end_state, end_state)
        except Exception as e:  # pylint:disable=broad-except
            self.go_to_error_state(e)
            raise

    def set_block_children(self):
        for child in self._part_fields:
            if isinstance(child, AttributeModel):
                states = child.meta.writeable_in
            else:
                states = child.writeable_in
            children[name] = child
            if states:
                for state in states:
                    assert state in self.stateMachine.possible_states, \
                        "State %s is not one of the valid states %s" % \
                        (state, self.stateMachine.possible_states)
            elif writeable_func is not None:
                states = [
                    state for state in self.stateMachine.possible_states
                    if state not in (sm.DISABLING, sm.DISABLED)]
            else:
                continue
            self.register_child_writeable(name, states)
            if writeable_func:
                writeable_functions[name] = functools.partial(
                    self.call_writeable_function, writeable_func)

    def create_attributes(self):
        """MethodModel that should provide Attribute instances for Block

        Yields:
            tuple: (string name, Attribute, callable put_function).
        """
        # Add the state, status and busy attributes
        self.state = ChoiceMeta(
            "State of Block", self.stateMachine.possible_states, label="State"
        ).make_attribute()
        yield "state", self.state, None
        self.status = StringMeta(
            "Status of Block", label="Status"
        ).make_attribute()
        yield "status", self.status, None
        self.busy = BooleanMeta(
            "Whether Block busy or not", label="Busy"
        ).make_attribute()
        yield "busy", self.busy, None


    def transition(self, state, message):
        """
        Change to a new state if the transition is allowed

        Args:
            state(str): State to transition to
            message(str): Status message
        """
        with self.lock:
            if self.stateMachine.is_allowed(
                    initial_state=self.state.value, target_state=state):
                self._do_transition(state, message)
            else:
                raise TypeError("Cannot transition from %s to %s" %
                                (self.state.value, state))

    def _do_transition(self, state, message):
        # transition is allowed, so set attributes
        changes = []
        changes.append([["state", "value"], state])
        changes.append([["status", "value"], message])
        changes.append([["busy", "value"],
                        state in self.stateMachine.busy_states])

        # say which children are now writeable
        for name in self.block:
            try:
                writeable = self.children_writeable[state][name]
            except KeyError:
                continue
            child = self.block[name]
            if isinstance(child, Attribute):
                changes.append([[name, "meta", "writeable"], writeable])
            elif isinstance(child, MethodModel):
                changes.append([[name, "writeable"], writeable])
                for ename in child.takes.elements:
                    path = [name, "takes", "elements", ename, "writeable"]
                    changes.append([path, writeable])

        self.log_debug("Transitioning to %s", state)
        self.block.apply_changes(*changes)

    def register_child_writeable(self, name, states):
        """
        Set the states that the given method can be called in

        Args:
            name (str): Child name that will be set writeable or not
            states (list[str]): states where method is writeable
        """
        for state in self.stateMachine.possible_states:
            writeable_dict = self.children_writeable.setdefault(state, {})
            is_writeable = state in states
            writeable_dict[name] = is_writeable