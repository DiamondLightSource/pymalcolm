from malcolm.yamlutil import make_block_creator

detector_runnable_block = make_block_creator(
    __file__, "detector_runnable_block.yaml")
hdf_writer_block = make_block_creator(
    __file__, "hdf_writer_block.yaml")
position_labeller_block = make_block_creator(
    __file__, "position_labeller_block.yaml")
sim_detector_driver_block = make_block_creator(
    __file__, "sim_detector_driver_block.yaml")
sim_detector_runnable_block = make_block_creator(
    __file__, "sim_detector_runnable_block.yaml")
stats_plugin_block = make_block_creator(
    __file__, "stats_plugin_block.yaml")

del make_block_creator
