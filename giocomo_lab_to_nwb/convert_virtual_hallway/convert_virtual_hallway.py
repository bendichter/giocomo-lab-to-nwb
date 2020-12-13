"""Authors: Szonja Weigl, Luiz Tauffer and Ben Dichter."""
from pathlib import Path

from giocomo_lab_to_nwb import VirtualHallwayNWBConverter

base_path = Path('data/').resolve()
spikeglx_file_path = base_path.joinpath('G4_190620_keicontrasttrack_10secBaseline1_g0/'
                                        'G4_190620_keicontrasttrack_10secBaseline1_g0_imec0/'
                                        'G4_190620_keicontrasttrack_10secBaseline1_g0_t0.imec0.ap.bin')
virtual_hallway_file_path = base_path.joinpath('npI5_0417_baseline_1.mat')
nwb_file_path = base_path.joinpath('VirtualHallway_stub.nwb')

if base_path.is_dir():
    source_data = dict(
        SpikeGLXRecording=dict(file_path=str(spikeglx_file_path)),
        VirtualHallwayData=dict(file_path=str(virtual_hallway_file_path))
    )
    # Enabling stub_test is recommended for first conversion to allow fast testing/validation
    conversion_options = dict(
        SpikeGLXRecording=dict(stub_test=True)
    )

    converter = VirtualHallwayNWBConverter(source_data)
    metadata = converter.get_metadata()
    converter.run_conversion(
        nwbfile_path=str(nwb_file_path),
        metadata=metadata,
        conversion_options=conversion_options
    )
