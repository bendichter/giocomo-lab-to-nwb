"""Authors: Szonja Weigl, Luiz Tauffer and Ben Dichter."""
from pathlib import Path

from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import get_base_schema, get_schema_from_hdmf_class
from pynwb.behavior import SpatialSeries
from pynwb import NWBFile
from scipy.io import loadmat


class VirtualHallwayDataInterface(BaseDataInterface):
    """Conversion class for the Virtual Hallway Task behavioral interface."""

    @classmethod
    def get_source_schema(cls):
        """Compile input schemas from each of the data interface classes."""
        return dict(
            required=['file_path'],
            properties=dict(
                file_path=dict(type='string')
            )
        )

    def get_metadata_schema(self):
        """Compile metadata schemas from each of the data interface objects."""
        metadata_schema = get_base_schema()
        metadata_schema['properties']['SpatialSeries'] = get_schema_from_hdmf_class(SpatialSeries)
        required_fields = ['SpatialSeries']
        for field in required_fields:
            metadata_schema['required'].append(field)
        return metadata_schema

    def run_conversion(self, nwbfile: NWBFile, metadata: dict):
        """TODO"""
        mat_file_name = self.source_data['file_path']

        if Path(mat_file_name).is_file():
            visual_hallway_data = loadmat(mat_file_name, struct_as_record=False, squeeze_me=True)

