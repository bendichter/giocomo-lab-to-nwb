from glob import glob
from pathlib import Path

from .malloryvrnwbconverter import MalloryVRNWBConverter, get_track_session_info

np_fpath = '/Volumes/easystore5T/data/Giocomo/nature_comm/src/spikeglx'
cell_info_files = glob('/Volumes/easystore5T/data/Giocomo/nature_comm/src/processed/cell_info_session*.mat')


for cell_info_file in cell_info_files:
    subject_id, session_id = get_track_session_info(cell_info_file)

    subject_session = '{}_{}'.format(subject_id, session_id[:4])

    session_fpath = next(Path(np_fpath).glob('{}*'.format(subject_session)))
    ap_file_path = next(session_fpath.glob('*_imec0/*imec0.ap.bin'))
    lf_file_path = next(session_fpath.glob('*_imec0/*imec0.lf.bin'))

    # Set some global conversion options here
    stub_test = True

    # Run the conversion
    source_data = dict(
        SpikeGLXRecording=dict(file_path=str(ap_file_path)),
        SpikeGLXLFP=dict(file_path=str(lf_file_path)),
        GiocomoTrackProcessed=dict(file_path=str(cell_info_file)),
        Events=dict(session_path=str(session_fpath))
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
