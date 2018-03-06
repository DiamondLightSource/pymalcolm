from malcolm.yamlutil import make_include_creator, check_yaml_names

compoundmotor_collection = make_include_creator(
    __file__, "compoundmotor_collection.yaml")
cs_collection = make_include_creator(
    __file__, "cs_collection.yaml")
motor_records = make_include_creator(
    __file__, "motor_records.yaml")
rawmotor_collection = make_include_creator(
    __file__, "rawmotor_collection.yaml")
brick_collection = make_include_creator(
    __file__, "brick_collection.yaml")

__all__ = check_yaml_names(globals())
