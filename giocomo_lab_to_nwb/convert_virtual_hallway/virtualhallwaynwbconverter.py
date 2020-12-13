"""Authors: Szonja Weigl, Luiz Tauffer and Ben Dichter."""
import yaml
from nwb_conversion_tools import NWBConverter, SpikeGLXRecordingInterface
from .virtualhallwaybehaviordatainterface import VirtualHallwayDataInterface


class VirtualHallwayNWBConverter(NWBConverter):
    """Conversion class for Virtual Hallway Task."""

    data_interface_classes = dict(
        SpikeGLXRecording=SpikeGLXRecordingInterface,
        VirtualHallwayData=VirtualHallwayDataInterface
    )

    def get_metadata(self):
        """Load task specific metadata from metafile.yml"""

        metadata = super().get_metadata()
        with open('metafile.yml', 'r') as meta_file:
            meta_config = yaml.safe_load(meta_file)

        metadata.update(Subject=dict())
        for field in metadata:
            [metadata[field].update({k: meta_config[field][k]}) for k in
             meta_config[field] if meta_config[field][k] != 'ADDME']

        return metadata
