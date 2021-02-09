"""Authors: Szonja Weigl, Luiz Tauffer and Ben Dichter."""
from pathlib import Path
import os
import yaml
from isodate import duration_isoformat
from datetime import timedelta

from giocomo_lab_to_nwb import VirtualHallwayNWBConverter

# Base folder path containing recording data and behavior
base_path = Path('data/').resolve()
spikeglx_base_path = base_path.joinpath('G4_190620_keicontrasttrack_10secBaseline1_g0/'
                                        'G4_190620_keicontrasttrack_10secBaseline1_g0_imec0/')
spikeglx_file_path = spikeglx_base_path.joinpath(
    'G4_190620_keicontrasttrack_10secBaseline1_g0_t0.imec0.ap.bin')
spikeglx_lfp_file_path = spikeglx_base_path.joinpath(
    'G4_190620_keicontrasttrack_10secBaseline1_g0_t0.imec0.lf.bin')

virtual_hallway_file_path = base_path.joinpath('npI5_0417_baseline_1.mat')
nwb_file_path = base_path.joinpath('VirtualHallway.nwb')

# Enter Session and Subject information here - uncomment any fields you want to include
session_description = ""

subject_info = dict(
    # description="Enter optional subject description here",
    # weight="Enter subject weight here",
    # age=duration_isoformat(timedelta(days=0)),  # Enter the age of the subject in days
    # species="Mus musculus",
    # genotype="Enter subject genotype here",
    # sex="Enter subject sex here"
)

# Set some global conversion options here
# Enabling stub_test is recommended for first conversion to allow fast testing/validation
stub_test = True

# Automatically performs conversion based on above filepaths and options
source_data = dict(
    SpikeGLXRecording=dict(file_path=str(spikeglx_file_path)),
    SpikeGLXLFP=dict(file_path=str(spikeglx_lfp_file_path)),
    VirtualHallwayData=dict(file_path=str(virtual_hallway_file_path))
)

conversion_options = dict(
    SpikeGLXRecording=dict(stub_test=stub_test),
    SpikeGLXLFP=dict(stub_test=stub_test)
)

converter = VirtualHallwayNWBConverter(source_data)
metadata = converter.get_metadata()
if 'Subject' not in metadata:
    metadata['Subject'] = subject_info

if os.path.exists('metafile.yml'):
    with open('metafile.yml', 'r') as meta:
        meta_conf = yaml.safe_load(meta)

    lab_meta_data = meta_conf['NWBFile'].pop('lab_meta_data')
    metadata.update(lab_meta_data=lab_meta_data)

    for k in meta_conf['NWBFile']:
        metadata['NWBFile'][k] = metadata['NWBFile'].get(k, meta_conf['NWBFile'][k])

    for k in meta_conf['Subject']:
        metadata['Subject'][k] = metadata['Subject'].get(k, meta_conf['Subject'][k])

if session_description:
    metadata['NWBFile'].update(session_description=session_description)

converter.run_conversion(
    nwbfile_path=str(nwb_file_path),
    metadata=metadata,
    conversion_options=conversion_options
)
