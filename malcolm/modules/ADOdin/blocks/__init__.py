from malcolm.yamlutil import check_yaml_names, make_block_creator

odin_driver_block = make_block_creator(__file__, "odin_driver_block.yaml")

odin_runnable_block = make_block_creator(__file__, "odin_runnable_block.yaml")

odin_writer_block = make_block_creator(__file__, "odin_writer_block.yaml")

__all__ = check_yaml_names(globals())
