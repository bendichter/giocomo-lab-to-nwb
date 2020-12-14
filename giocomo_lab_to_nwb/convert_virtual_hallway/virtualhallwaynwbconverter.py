"""Authors: Szonja Weigl, Luiz Tauffer and Ben Dichter."""
from datetime import datetime
from pathlib import Path

from nwb_conversion_tools import NWBConverter, SpikeGLXRecordingInterface
from .virtualhallwaybehaviordatainterface import VirtualHallwayDataInterface


class VirtualHallwayNWBConverter(NWBConverter):
    """Conversion class for Virtual Hallway Task."""

    data_interface_classes = dict(
        SpikeGLXRecording=SpikeGLXRecordingInterface,
        VirtualHallwayData=VirtualHallwayDataInterface
    )

    def get_metadata(self):
        """Load task specific metadata from .meta file"""

        metadata = super().get_metadata()

        bin_file_path = Path(self.data_interface_objects['SpikeGLXRecording'].source_data['file_path'])
        meta_file_path = bin_file_path.with_suffix('.meta')

        if meta_file_path.is_file():
            with meta_file_path.open('r') as meta_file:
                metadata_from_bin = meta_file.read().splitlines()

            metadata_dict = {x.split('=')[0]: x.split('=')[1] for x in metadata_from_bin}
            file_create_date = metadata_dict['fileCreateTime']
            session_start_time = datetime.fromisoformat(file_create_date)

            metadata['NWBFile'].update(
                session_start_time=session_start_time,
            )

        else:
            print(f"Warning: no meta file detected at {bin_file_path.parent}!")

        return metadata
