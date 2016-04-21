.. _messages:

Messages and types
==================

There are a number of client side verbs:

- Get: Get the structure of a Block or part of one
- Put: Put a value to an Attribute
- Post: Call a method of a Block
- Subscribe: Subscribe to changes in a Block or part of one
- Unsubscribe: Cancel one Subscribe

And a number of server side verbs:

- Error: Return an error to any one of the client side requests
- Value: Return a complete value to a subscription
- Changes: Return incremental changes to a subscription
- Return: Provide a return value to a Post, Get, Put, Unsubscribe, and indicate
  the cancellation of a Subscribe

Changes
-------

Return a `diff stanza` as used by json_delta_


.. _json_delta:
    http://json-delta.readthedocs.org/en/latest/
    philosophy.html?highlight=stanzas

