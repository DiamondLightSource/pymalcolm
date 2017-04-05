from malcolm.yamlutil import make_include_creator

compoundmotor_collection = make_include_creator(
    __file__, "compoundmotor_collection.yaml")
motor_records = make_include_creator(__file__, "motor_records.yaml")
rawmotor_collection = make_include_creator(__file__, "rawmotor_collection.yaml")
trajectory_collection = make_include_creator(
    __file__, "trajectory_collection.yaml")

del make_include_creator
