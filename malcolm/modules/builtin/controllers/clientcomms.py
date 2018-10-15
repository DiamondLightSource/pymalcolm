from .statefulcontroller import StatefulController


class ClientComms(StatefulController):
    """Abstract class for dispatching requests to a server and responses to
    a method"""

    def sync_proxy(self, mri, block):
        """Abstract method telling the ClientComms to sync this proxy Block
        with its remote counterpart. Should wait until it is connected

        Args:
            mri (str): The mri for the remote block
            block (BlockModel): The local proxy Block to keep in sync
        """
        raise NotImplementedError(self)

    def send_put(self, mri, attribute_name, value):
        """Abstract method to dispatch a Put to the server

        Args:
            mri (str): The mri of the Block
            attribute_name (str): The name of the Attribute within the Block
            value: The value to put
        """
        raise NotImplementedError(self)

    def send_post(self, mri, method_name, **params):
        """Abstract method to dispatch a Post to the server

        Args:
            mri (str): The mri of the Block
            method_name (str): The name of the Method within the Block
            params: The parameters to send

        Returns:
            The return results from the server
        """
        raise NotImplementedError(self)
