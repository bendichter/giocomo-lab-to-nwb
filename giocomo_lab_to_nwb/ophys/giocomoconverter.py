from nwb_conversion_tools import NWBConverter, SbxImagingInterface, Suite2pSegmentationInterface
from .giocomovrdatainterface import GiocomoVRInterface
from pathlib import Path
import warnings
import jsonschema

class GiocomoImagingInterface(NWBConverter):

    data_interface_classes = dict(
        SbxImagingInterface=SbxImagingInterface,
        Suite2pSegmentationInterface=Suite2pSegmentationInterface,
        GiocomoVRInterface=GiocomoVRInterface
    )

    def __init__(self, source_data: [dict, str]):
        """
        Converts acquisition images from scanbox, segmentation data after Suite2p and behavioral VR
        data from pickled dataframes.
        Parameters
        ----------
        source_data : str
            path to the .mat/sbx file
        """
        if isinstance(source_data,dict):
            jsonschema.validate(source_data, self.get_source_schema())
            source_data_dict = source_data
        else:
            source_data = Path(source_data)
            assert source_data.suffix in ['.mat','.sbx'], 'source_data should be path to .mat/.sbx file'
            source_data_dict = dict(
                SbxImagingInterface=dict(file_path=str(source_data))
            )
            s2p_folder = source_data.with_suffix('')/'suite2p'
            if not s2p_folder.exists():
                warnings.warn('could not find suite2p')
            else:
                source_data_dict.update(Suite2pSegmentationInterface=dict(file_path=str(s2p_folder)))
            pkl_file = source_data.with_suffix('.pkl')
            if not pkl_file.exists():
                pkl_file = \
                    source_data.parents[3]/'VR_pd_pickles'/source_data.relative_to(source_data.parents[3]).with_suffix('.pkl')
                if not pkl_file.exists():
                    warnings.warn('could not find .pkl file')
                else:
                    source_data_dict.update(GiocomoVRInterface=dict(file_path=str(pkl_file)))
            else:
                source_data_dict.update(GiocomoVRInterface=dict(file_path=str(pkl_file)))
        super().__init__(source_data_dict)