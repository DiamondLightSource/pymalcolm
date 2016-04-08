Threading Model
===============

There are a number of threads:

- 1 for the main Process, blocking on its Queue and a scheduler
- a thread pool for servicing any device input

The rule is, only ever block on your Queue.
