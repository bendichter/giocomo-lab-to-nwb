from nwb_conversion_tools import NWBConverter, SpikeGLXRecordingInterface, SpikeGLXLFPInterface, PhySortingInterface

class Wen21NWBConverter(NWBConverter):
    data_interface_classes = dict(
        SpikeGLXRecording=SpikeGLXRecordingInterface,
        SpikeGLXLFP=SpikeGLXLFPInterface,
        PhySorting=PhySortingInterface,
    )
