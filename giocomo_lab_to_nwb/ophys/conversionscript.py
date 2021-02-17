from pathlib import Path

from tqdm import tqdm

from .giocomoconverter import GiocomoImagingInterface


def conversion_complete(source_path):
    """
    Convert all files in batch.
    Parameters
    ----------
    source_path: Path, str
        location of the source_folder containing datafiles
    """
    source_path = Path(source_path)

    for subject_id_path in source_path.iterdir():
        if subject_id_path.name[:-2].isdigit():
            print(f'converting for subject is:{subject_id_path.name}')
            file_path_list = tqdm([i for i in subject_id_path.glob('*/*/*.sbx')])
            for file_path in file_path_list:
                file_path_list.set_postfix(current=f'writing: {file_path.name}')
                try:
                    gio = GiocomoImagingInterface(str(file_path))
                    nwb_file_name = file_path.with_suffix('.nwb')
                    gio.run_conversion(metadata=gio.get_metadata(),
                                       nwbfile_path=str(nwb_file_name),
                                       overwrite=True)
                except Exception as e:
                    print(f'could not convert: {e}')


def convert_file(filepath: [Path, str, dict], nwb_save_path: [Path, str] = None):
    """
    Convert a single set of sbx, suite2p and VR data pickled files
    Parameters
    ----------
    filepath: [Path,str, dict]
        path to the sbx file. Or dict:
        {'SbxImagingInterface': path-to-sbxfile,
          'Suite2pSegmentationInterface': path-to-suite2p,
          'GiocomoVRInterface': path-to-vrpkl file
        }
    nwb_save_path: [Path,str]
        Optional, save location for nwb file.
    """
    if nwb_save_path is None:
        nwb_save_path = Path.cwd()/'sbx_nwb.nwb'
    gio = GiocomoImagingInterface(filepath)
    gio.run_conversion(metadata=gio.get_metadata(), nwbfile_path=str(nwb_save_path), overwrite=True)
