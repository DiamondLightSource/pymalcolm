from malcolm.compat import OrderedDict


class StateSet(object):
    def __init__(self):
        self._allowed = OrderedDict()
        # These are all the states we can possibly be in
        self.possible_states = []

    def transition_allowed(self, initial_state, target_state):
        """
        Check if a transition between two states is allowed

        Args:
            initial_state(str): Initial state
            target_state(str): Target state

        Returns:
            bool: True if allowed, False if not
        """
        assert initial_state in self._allowed, \
            "%s is not in %s" % (initial_state, list(self._allowed))
        return target_state in self._allowed[initial_state]

    def set_allowed(self, initial_state, allowed_states):
        """Add an allowed transition state

        Args:
            initial_state (str): Initial state
            allowed_states (str or list): state or list of states that
                initial_state can transition to
        """
        if not isinstance(allowed_states, list):
            allowed_states = [allowed_states]

        self._allowed.setdefault(initial_state, set()).update(allowed_states)
        for state in allowed_states + [initial_state]:
            if state not in self.possible_states:
                self.possible_states.append(state)
