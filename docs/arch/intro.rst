Introduction
============

Malcolm can be considered to be a distributed object system. This document will
use a number of terms to identify key components of Malcolm:

- Process: A Malcolm instance containing a number of Blocks along with various
  communication modules to communicate with other Malcolm instances. A Process
  can be a client of or a server to a number of other Processes.
- Block: An object consisting of a number of Attributes and Methods. It should
  be designed to be as small and self contained as possible, and complex logic
  should be implemented by nesting Blocks. For example, a detector driver would
  be a Block, as would an HDF writer, but there would also be a higher level
  detector Block to co-ordinate the low level Blocks. There would then be a top
  level mapping scan Block the co-ordinated the detector Block and a motion
  trajectory block to perform the scan. Any Block may be synchronized among a
  number of Processes, the Block acting as the server will perform the logic,
  and the client copies will expose the same API as the server Block to the end
  user.
- Attributes: Hold the current value of a piece of data of a fixed simple type
  like Int, Float, String, Enum, IntArray, Table or a named Map. You can Get
  and Subscribe to changes in all Attributes, and Put to Attributes with a
  defined setter. In a client Block, Attributes will mirror the value of the
  Block acting as a server, with a Put operation being forwarded to the server
  Block.
- Methods: Expose a function call. You can Call a Method with a (possibly empty)
  Map of arguments, and it will return a (possibly empty) Map of return values.
  In a client Block, the Call will be forwarded to the server Block, and the
  return value returned to the caller.

For example, in the following diagram, Process1 is hosting two Blocks, and
Process2 has a client of Block 2 as a local object.

.. uml::
    !include docs/style.iuml

    frame Process1 {
        frame Block1 {
            [Attribute 1]
            [Attribute 2]
            [Method 1]
        }

        frame Block2 {
            [Attribute 1] as B2.A1
            [Method 1] as B2.M1
        }
    }

    frame Process2 {
        frame Block2Client {
            [Attribute 1] as B2C.A1
            [Method 1] as B2C.M1
        }
    }

    B2C.A1 --> B2.A1
    B2C.M1 --> B2.M1


