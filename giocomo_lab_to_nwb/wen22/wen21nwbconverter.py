from nwb_conversion_tools import NWBConverter, SpikeGLXRecordingInterface, SpikeGLXLFPInterface, PhySortingInterface
from wen21behaviorinterface import Wen21EventsInterface

class Wen21NWBConverter(NWBConverter):
    data_interface_classes = dict(
        SpikeGLXRecording=SpikeGLXRecordingInterface,
        SpikeGLXLFP=SpikeGLXLFPInterface,
        PhySorting=PhySortingInterface,
        Behavior=Wen21EventsInterface
    )
