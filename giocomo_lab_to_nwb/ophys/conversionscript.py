from pathlib import Path
from warnings import warn

from joblib import Parallel, delayed
from tqdm import tqdm

from .giocomoconverter import GiocomoImagingInterface


def converter(file_path: Path, nwb_file_path=None):
    try:
        print(f'converting {file_path.relative_to(file_path.parents[2])}')
        gio = GiocomoImagingInterface(str(file_path))
        if nwb_file_path is None:
            nwb_file_path = file_path.with_suffix('.nwb')
        gio.run_conversion(metadata=gio.get_metadata(),
                           nwbfile_path=str(nwb_file_path),
                           overwrite=True)
    except Exception as e:
        warn(f'could not convert: {e}')


def conversion_complete(source_path, parallelize: bool = True, n_jobs=10):
    """
    Convert all files in batch.
    Parameters
    ----------
    parallelize: bool
    n_jobs: int
    source_path: Path, str
        location of the source_folder containing datafiles
    """
    source_path = Path(source_path)
    for subject_id_path in source_path.iterdir():
        if subject_id_path.name[:-2].isdigit():
            print(f'converting for subject:{subject_id_path.name}')
            if parallelize:
                file_path_list = [i for i in subject_id_path.glob('*/*/*.sbx')]
                Parallel(n_jobs=n_jobs)(delayed(converter)(file_path) for file_path in file_path_list)
            else:
                file_path_list = tqdm([i for i in subject_id_path.glob('*/*/*.sbx')])
                for file_path in file_path_list:
                    file_path_list.set_postfix(current=f'writing: {file_path.name}')
                    converter(file_path)


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
    converter(Path(filepath), nwb_save_path)
