from annotypes import Anno

from malcolm.modules import ADCore, builtin, pandablocks, scanning

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
    builtin.controllers.StatefulController,
):
    pass


class PandARunnableController(
    pandablocks.controllers.PandAManagerController,
    scanning.controllers.RunnableController,
):
    def __init__(
        self,
        mri: AMri,
        config_dir: AConfigDir,
        prefix: APrefix,
        hostname: AHostname = "localhost",
        port: APort = 8888,
        poll_period: APollPeriod = 0.1,
        template_designs: ATemplateDesigns = "",
        initial_design: AInitialDesign = "",
        use_git: AUseGit = True,
        description: ADescription = "",
    ) -> None:
        super().__init__(
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

    def _make_busses(self) -> PandADatasetBussesPart:
        return PandADatasetBussesPart("busses", self._client)

    def _make_child_block(self, block_name, block_data):
        if block_name == "PCAP":
            controller = PandAStatefulBlockController(
                self._client, self.mri, block_name, block_data, self._doc_url_base
            )
            # Add the areaDetector control parts
            _, ps = ADCore.includes.adbase_parts(prefix=self.prefix)
            for p in ps:
                controller.add_part(p)
            child_part = ADCore.parts.DetectorDriverPart(
                name=block_name, mri=controller.mri, main_dataset_useful=False
            )
            return controller, child_part
        else:
            return super()._make_child_block(block_name, block_data)
