"""Authors: Szonja Weigl, Luiz Tauffer and Ben Dichter."""
from pathlib import Path
from nwb_conversion_tools import NWBConverter, SpikeGLXRecordingInterface, SpikeGLXLFPInterface
from .virtualhallwaybehaviordatainterface import VirtualHallwayDataInterface


class VirtualHallwayNWBConverter(NWBConverter):
    """Conversion class for Virtual Hallway Task."""

    data_interface_classes = dict(
        SpikeGLXRecording=SpikeGLXRecordingInterface,
        SpikeGLXLFP=SpikeGLXLFPInterface,
        VirtualHallwayData=VirtualHallwayDataInterface
    )

    def get_metadata(self):
        metadata = super().get_metadata()
        behavior_file_path = Path(
            self.data_interface_objects['VirtualHallwayData'].source_data['file_path'])
        session_id = behavior_file_path.stem

        metadata['NWBFile'].update(
            institution='Stanford University School of Medicine',
            lab='Giocomo',
            session_id=session_id
        )

        return metadata
