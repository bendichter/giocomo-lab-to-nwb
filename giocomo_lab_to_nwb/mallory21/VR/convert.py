from glob import glob
import os

from .utils import get_track_session_info
from .malloryvrnwbconverter import MalloryVRNWBConverter

np_fpath = '/Volumes/easystore5T/data/Giocomo/nature_comm/src/spikeglx'
cell_info_files = glob('/Volumes/easystore5T/data/Giocomo/nature_comm/src/processed/cell_info_session*.mat')


cell_info_file = cell_info_files[1]
subject_id, session_id = get_track_session_info(cell_info_file)

subject_session = '{}_{}'.format(subject_id, session_id[:4])

ap_file_path = glob(
    os.path.join(
        np_fpath,
        '{}*'.format(subject_session),
        '*_imec0',
        '*imec0.ap.bin'
    )
)[0]

lf_file_path = glob(
    os.path.join(
        np_fpath,
        '{}*'.format(subject_session),
        '*_imec0',
        '*imec0.lf.bin'
    )
)[0]


# Set some global conversion options here
stub_test = False

# Run the conversion
source_data = dict(
    SpikeGLXRecording=dict(file_path=str(ap_file_path)),
    SpikeGLXLFP=dict(file_path=str(lf_file_path)),
    GiocomoTrackProcessed=dict(file_path=str(cell_info_file))
)
conversion_options = dict(
    SpikeGLXRecording=dict(stub_test=stub_test),
    SpikeGLXLFP=dict(stub_test=stub_test)
)

converter = MalloryVRNWBConverter(source_data=source_data)
metadata = converter.get_metadata()

converter.run_conversion(
    nwbfile_path='/Volumes/easystore5T/data/Giocomo/nature_comm/nwb/{}_{}.nwb'.format(subject_id, session_id),
    metadata=metadata,
    conversion_options=conversion_options,
    overwrite=True
)
