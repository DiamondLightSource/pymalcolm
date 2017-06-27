from .statefulcontroller import StatefulController


class ClientComms(StatefulController):
    """Abstract class for dispatching requests to a server and responses to
    a method"""

    def send_to_server(self, request):
        """Abstract method to dispatch request to a server

        Args:
            request (Request): The message to pass to the server
        """
        raise NotImplementedError(
            "Abstract method that must be implemented by deriving class")
