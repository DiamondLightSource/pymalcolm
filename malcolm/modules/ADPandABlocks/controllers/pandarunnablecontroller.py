from annotypes import Anno

from malcolm.modules import ADCore, scanning, pandablocks, builtin
from ..parts.pandadatasetbussespart import PandADatasetBussesPart

with Anno("Prefix for areaDetector records"):
    APrefix = str
# Re-export the things we are reusing from pandablocks
AMri = pandablocks.controllers.AMri
AConfigDir = pandablocks.controllers.AConfigDir
AHostname = pandablocks.controllers.AHostname
APort = pandablocks.controllers.APort
APollPeriod = pandablocks.controllers.APollPeriod
ATemplateDesigns = pandablocks.controllers.ATemplateDesigns
AInitialDesign = pandablocks.controllers.AInitialDesign
AUseGit = pandablocks.controllers.AUseGit
ADescription = pandablocks.controllers.ADescription


class PandAStatefulBlockController(
    pandablocks.controllers.pandablockcontroller.PandABlockController,
        builtin.controllers.StatefulController):
    pass


class PandARunnableController(pandablocks.controllers.PandAManagerController,
                              scanning.controllers.RunnableController):
    def __init__(self,
                 mri,  # type: AMri
                 config_dir,  # type: AConfigDir
                 prefix,  # type: APrefix
                 hostname="localhost",  # type: AHostname
                 port=8888,  # type: APort
                 poll_period=0.1,  # type: APollPeriod
                 template_designs="",  # type: ATemplateDesigns
                 initial_design="",  # type: AInitialDesign
                 use_git=True,  # type: AUseGit
                 description="",  # type: ADescription
                 ):
        # type: (...) -> None
        super(PandARunnableController, self).__init__(
            mri=mri,
            config_dir=config_dir,
            hostname=hostname,
            port=port,
            poll_period=poll_period,
            template_designs=template_designs,
            initial_design=initial_design,
            use_git=use_git,
            description=description,
        )
        self.prefix = prefix

    def _make_busses(self):
        # type: () -> PandADatasetBussesPart
        return PandADatasetBussesPart("busses", self._client)

    def _make_child_block(self, block_name, block_data):
        if block_name == "PCAP":
            controller = PandAStatefulBlockController(
                self._client, self.mri, block_name, block_data,
                self._doc_url_base)
            # Add the areaDetector control parts
            _, ps = ADCore.includes.adbase_parts(prefix=self.prefix)
            for p in ps:
                controller.add_part(p)
            child_part = ADCore.parts.DetectorDriverPart(
                name=block_name, mri=controller.mri, main_dataset_useful=False)
            return controller, child_part
        else:
            return super(PandARunnableController, self). \
                _make_child_block(block_name, block_data)
