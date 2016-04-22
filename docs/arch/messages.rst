.. _messages:

Messages and types
==================

The communication between Blocks in the same Process is by passing Python
dictionaries representing messages to each other's input queues. When the
Blocks are in different Processes, a serialization method and transport
protocol is needed. The simplest is JSON serialization over websockets or
ZeroMQ, and this is what is described below. The structures will also be
accessible via pvData over pvAccess, with the communication layer providing
translation of the messages to and from their Python dictionary equivalents.

The protocol is asymmetric, with different message types from client to server
than for server to client. Each client sent message contains an integer id which
will be contained in any server response. This id must be unique within the
scope of the client connection.

A Malcolm client makes a connection via one of the supported communication
protocols, and within that connection can communicate to the server by sending
the following message types:

- `Get`_: Get the structure of a Block or part of one
- `Put`_: Put a value to an Attribute
- `Post`_: Call a method of a Block
- `Subscribe`_: Subscribe to changes in a Block or part of one
- `Unsubscribe`_: Cancel one `Subscribe`_

A Malcolm server recieves messages from a number of clients, and sends the
following message types back:

- `Error`_: Return an error to any one of the client side requests
- `Update`_: Return a complete updated value to a subscription
- `Delta`_: Return incremental changes to a subscription
- `Return`_: Provide a return value to a `Post`_, `Get`_, `Put`_,
  `Unsubscribe`_, and indicate the cancellation of a `Subscribe`_

Get
---

This message will ask the server to serialize the ``endpoint`` and send it back
as a `Return`_ message. It will receive an `Error`_ message if the ``endpoint``
doesn't exist.

Dictionary with members:

- type
    String ``Get``.
- id
    Integer id which will be contained in any server response.
- endpoint
    List of strings specifying the path to the Block the Block or substructure
    of the Block that should be returned. The first element will be the name of
    the Block, and any subsequent elements will be paths to traverse within the
    Block structure. See :ref:`structure` for more details.

.. container:: toggle

    .. container:: header

        **Example**: Get the current value of the state attribute of
        ``BL18I:XSPRESS3``:

    .. include:: json/get_xspress3_state_value

.. container:: toggle

    .. container:: header

        **Example**: Get the entire ``BL18I:XSPRESS3`` structure:

    .. include:: json/get_xspress3

Put
---

This message will ask the server to put ``value`` to the ``endpoint`` of the
``block``. It will get a `Return`_ message when complete or an `Error`_ message
if the ``block`` or ``endpoint`` don't exist or aren't writeable. Only the value
fields of writeable Attributes accept Puts.

Dictionary with members:

- type
    String ``Put``.
- id
    Integer id which will be contained in any server response.
- endpoint
    List of strings specifying the path to the substructure of the Block that
    should be modified. The first element will be the name of the Block, and
    subsequent elements will be paths to traverse within the Block structure.
    See :ref:`structure` for more details.
- value
    Object value to be set. This will be the dictionary representation of the
    Attribute value type. For simple types this will just be a String or
    Integer. See :ref:`structure` for how more complex structures are
    represented.

.. container:: toggle

    .. container:: header

        **Example**: Put the file path of an HDF Writer object:

    .. include:: json/put_hdf_file_path

Post
----

This message will ask the server to post to an ``endpoint`` of a ``block`` with
some ``parameters``. This is typically used to call a method. It will get a
`Return`_ message when complete or an `Error`_ message if the ``block`` or
``endpoint`` don't exist or aren't Methods.

Dictionary with members:

- type
    String ``Post``.
- id
    Integer id which will be contained in any server response.
- endpoint
    List of strings specifying the path to the substructure
    of the Block that should be posted to. The first element will be the name of
    the Block, and the second will be the Method name. See :ref:`structure` for
    more details.
- parameters
    Dictionary of parameters that should be Posted. The keys of the dictionary
    are string parameter names, and the types of the values should match those
    described in the ``takes`` element of the Method. See :ref:`structure` for
    details.

.. container:: toggle

    .. container:: header

        **Example**: Call the configure() method of ``BL18I:XSPRESS3``:

    .. include:: json/post_xspress3_configure

Subscribe
---------

This message will ask the server to respond with a message every time the
``block`` (or ``endpoint`` of the ``block``) changes. If ``delta`` then the
server will respond with a `Delta`_ message listing what has changed,
otherwise it will respond with a `Update`_ message with the entire structure each
time. The first message received will give the current value, and subsequent
messages will be sent whenever it changes. It will receive an `Error`_ message
if the ``block`` or ``endpoint`` don't exist. When `Unsubscribe`_ is called with
the same id, a `Return`_ message will be received on that id with no value.

Dictionary with members:

- type
    String ``Subscribe``.
- id
    Integer id which will be contained in any server response.
- endpoint
    List of strings specifying the path to the Block the Block or substructure
    of the Block that should be returned. The first element will be the name of
    the Block, and any subsequent elements will be paths to traverse within the
    Block structure. See :ref:`structure` for more details.
- delta (optional)
    If given and is true then send `Delta`_ messages on updates, otherwise
    send `Update`_ messages.

.. container:: toggle

    .. container:: header

        **Example**: Subscribe to the value of the state attribute of
        ``BL18I:XSPRESS3``:

    .. include:: json/subscribe_xspress3_state_value

.. container:: toggle

    .. container:: header

        **Example**: Subscribe to deltas in the entire ``BL18I:XSPRESS3``
        structure:

    .. include:: json/subscribe_xspress3

Unsubscribe
-----------

This message will ask the server to stop sending notifications to a particular
subscription. It will receive an `Error`_ message if the id is not for a valid
subscription. A `Return`_ message will be received on that id with no value if
successful.

Dictionary with members:

- type
    String ``Unsubscribe``.
- id
    Integer id which was given in the `Subscribe`_ method.

.. container:: toggle

    .. container:: header

        **Example**: Unsubscribe from subscription id 0:

    .. include:: json/unsubscribe

Error
-----

This message is sent for a number of reasons:

- The client has sent a badly formed message
- The client has asked to interact with a nonexistant block or endpoint
- The `Put`_ or `Post`_ operation has thrown an error

Dictionary with members:

- type
    String ``Error``.
- id
    Integer id from original client message. If the id cannot be determined
    from the original message, -1 will be used.
- message
    Human readable error message

.. container:: toggle

    .. container:: header

        **Example**: Get on nonexistant block

    .. include:: json/error


Update
------

This message is sent in response to a `Subscribe`_ without the delta option. It
contains the serialized version of a Block or substructure of a Block.

Dictionary with members:

- type
    String ``Update``.
- id
    Integer id from original client `Subscribe`_.
- value
    Object current value of subscribed endpoint. This will be the dictionary
    representation of the Attribute value type. For simple types this will just
    be a String or Integer. See :ref:`structure` for how more complex structures
    are represented.

.. container:: toggle

    .. container:: header

        **Example**: A message sent when monitoring the state Attribute value of
        a block:

    .. include:: json/update_state_value


Delta
-------

This message is sent in response to a `Subscribe`_ with the delta option. It
contains a list of json_delta_ style stanzas of the difference between the last
transmitted value (if any) and the current value.

.. _json_delta:
    http://json-delta.readthedocs.org/en/latest/
    philosophy.html?highlight=stanzas

Dictionary with members:

- type
    String ``Delta``.
- id
    Integer id from original client `Subscribe`_.
- delta
    List of [``key path``, optional ``update``] stanzas.

    - ``key path`` is a path to the changed element within the subscribed path.
      This means that the original subscription path + this key path describes
      the full path to the changed element
    - ``update`` is the optional new value that should appear at ``key path``.
      If it doesn't exist then this stanza is an instruction to delete the node
      the key path points to.

.. container:: toggle

    .. container:: header

        **Example**: A message sent when monitoring the top level Block, and
        the state Attribute's value changed:

    .. include:: json/changes_state_value

Return
------

This message is sent to signify completion of an operation:

- In response to a `Get`_ to return the serialized version of an endpoint
- In response to a `Put`_ or `Unsubscribe`_ with no value to indicate successful
  completion
- In response to a `Post`_ with the return value of that Method call, or no
  value if nothing is returned

Dictionary with members:

- type
    String ``Return``.
- id
    Integer id from original client `Get`_, `Put`_, `Post`_ or `Unsubscribe`_.
- value (optional)
    Object return value if it exists. For `Get`_ this will be the structure of
    the endpoint. For `Post`_ this will be described by the ``returns`` element
    of the Method. See :ref:`structure` for more details.

.. container:: toggle

    .. container:: header

        **Example**: The return of a `Get`_ of a Blocks's state Attribute value:

    .. include:: json/return_state_value

.. container:: toggle

    .. container:: header

        **Example**: The successful completion of a `Put`_ or `Unsubscribe`_:

    .. include:: json/return


