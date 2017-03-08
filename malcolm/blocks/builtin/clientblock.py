from malcolm.core import method_takes, REQUIRED
from malcolm.vmetas.builtin import StringMeta

@method_takes("mri", StringMeta("MRI for the client block"), REQUIRED)
def ClientBlock(process, params):
    return process.make_client_block(params.mri)
