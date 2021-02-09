from .giocomoconverter import GiocomoImagingInterface
from pathlib import Path

source_path = r'C:\Users\Saksham\Documents\NWB\roiextractors\testdatasets\GiocomoData'
sbx_path = r'C:\Users\Saksham\Documents\NWB\roiextractors\testdatasets\GiocomoData\4139265.5\10_02_2019\TwoTOwer_foraging\TwoTower_foraging_003_006_small.sbx'

def conversion_complete(source_path):
    """
    Convert all files in batch.
    Parameters
    ----------
    source_path: Path, str
        location of the source_folder containing datafiles
    """
    for subject_id_path in source_path.iterdir():
        if subject_id_path.name[:-2].isdigit():
            for date_path in subject_id_path.iterdir():
                for task_path in date_path.iterdir():
                    for file_path in task_path.iterdir():
                        if file_path.suffix == '.sbx' and 'small' in str(file_path):
                            print(file_path)
                            try:
                                gio = GiocomoImagingInterface(str(file_path))
                                nwb_file_name = file_path.with_suffix('.nwb')
                                gio.run_conversion(metadata=gio.get_metadata(),
                                                   nwbfile_path=str(nwb_file_name),
                                                   overwrite=True)
                                print(f'converted nwb file for {str(file_path)}')
                            except Exception as e:
                                print(f'could not convert: {e}')


def convert_file(sbx_filepath: [Path, str], nwb_save_path: [Path,str] = None):
    """
    Convert a single set of sbx, suite2p and VR data pickled files
    Parameters
    ----------
    sbx_filepath: [Path,str]
        path to the sbx file.
    nwb_save_path: [Path,str]
        Optional, save location for nwb file.
    """
    if nwb_save_path is None:
        nwb_save_path = Path.cwd()/'gio_nwb.nwb'
    gio = GiocomoImagingInterface(sbx_filepath)
    gio.run_conversion(metadata=gio.get_metadata(), nwbfile_path=str(nwb_save_path),overwrite=True)