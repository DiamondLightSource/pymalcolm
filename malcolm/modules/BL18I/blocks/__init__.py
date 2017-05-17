from malcolm.yamlutil import make_block_creator, check_yaml_names

i18_fine_theta_manager_block = make_block_creator(
    __file__, "i18_fine_theta_manager_block.yaml")

i18_pmac_manager_block = make_block_creator(
    __file__, "i18_pmac_manager_block.yaml")

i18_table01_manager_block = make_block_creator(
    __file__, "i18_table01_manager_block.yaml")

i18_table03_manager_block = make_block_creator(
    __file__, "i18_table03_manager_block.yaml")

__all__ = check_yaml_names(globals())
