import os

from annotypes import Anno, add_call_types

from malcolm.modules import scanning

from ..infos import FilePathTranslatorInfo
from .hdfwriterpart import HDFWriterPart, create_dataset_infos, greater_than_zero

with Anno("Approximate timeout before stopping writer"):
    AWriterTimeout = float


class HDFContinuousWriterPart(HDFWriterPart):
    """Writer part which keeps running forever"""

    # Allow CamelCase as these parameters will be serialized
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        context: scanning.hooks.AContext,
        part_info: scanning.hooks.APartInfo,
        generator: scanning.hooks.AGenerator,
        fileDir: scanning.hooks.AFileDir,
        formatName: scanning.hooks.AFormatName = "det",
        fileTemplate: scanning.hooks.AFileTemplate = "%s.h5",
    ) -> None:
        child = context.block_view(self.mri)
        # For first run then open the file
        # Disable position mode
        child.positionMode.put_value(False)
        # Setup our required settings
        file_dir = fileDir.rstrip(os.sep)
        if self.runs_on_windows:
            h5_file_dir = FilePathTranslatorInfo.translate_filepath(part_info, file_dir)
        else:
            h5_file_dir = file_dir
        filename = fileTemplate % formatName
        assert "." in filename, "File extension for %r should be supplied" % filename
        futures = child.put_attribute_values_async(
            dict(
                enableCallbacks=True,
                fileWriteMode="Stream",
                swmrMode=True,
                storeAttr=True,
                dimAttDatasets=True,
                lazyOpen=True,
                arrayCounter=0,
                filePath=h5_file_dir + os.sep,
                fileName=formatName,
                fileTemplate="%s" + fileTemplate,
            )
        )
        futures += child.put_attribute_values_async(
            dict(
                flushDataPerNFrames=1,
                flushAttrPerNFrames=0,
            )
        )
        # Wait for the previous puts to finish
        context.wait_all_futures(futures)
        # Reset numCapture back to 0
        child.numCapture.put_value(0)
        # Start the plugin
        child.start_async()
        # Start a future waiting for the first array
        self.array_future = child.when_value_matches_async(
            "arrayCounterReadback", greater_than_zero
        )
        # Return the dataset information
        dataset_infos = list(
            create_dataset_infos(formatName, part_info, generator, filename)
        )
        return dataset_infos

    @add_call_types
    def on_run(self, context: scanning.hooks.AContext) -> None:
        # Ensure we get at least one array
        context.wait_all_futures(self.array_future)

    @add_call_types
    def on_seek(self) -> None:
        pass
