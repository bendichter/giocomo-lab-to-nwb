from pathlib import Path
import dateutil
from datetime import datetime

from wen21nwbconverter import Wen21NWBConverter
from nwb_conversion_tools.utils import dict_deep_update, load_dict_from_file

# To be changed in the running system
data_path = Path("/media/heberto/TOSHIBA EXT/Wen/")
output_path = Path("/media/heberto/TOSHIBA EXT/nwb/")

general_metadata_path = Path("./giocomo_lab_to_nwb/wen22/metadata.yml")
stub_test = True
if stub_test:
    output_path = output_path.parent / "nwb_stub"
spikeextractors_backend = False

session_path_list = [path for path in data_path.iterdir() if path.name != "VR"]
# session_path_list = [session_path_list[-1]]
for session_path in session_path_list:
    # Determine relevant file paths and initialize variables
    session_id = session_path.name
    device = "imec0"
    directory_with_data_path = session_path / f"{session_id}_{device}"

    source_data = dict()
    conversion_options = dict()

    # Verbose
    print("====================================")
    print(f"{session_id=}")

    # Raw signal spikeglx
    signal_kind = "ap"
    ap_file_name = f"{directory_with_data_path.stem.replace('g0_', 'g0_t0.')}.{signal_kind}.bin"
    ap_file_path = directory_with_data_path / ap_file_name
    source_data.update(
        SpikeGLXRecording=dict(file_path=str(ap_file_path), spikeextractors_backend=spikeextractors_backend)
    )
    conversion_options.update(SpikeGLXRecording=dict(stub_test=stub_test))

    # LFP signa spikeglx
    signal_kind = "lf"
    lf_file_name = f"{directory_with_data_path.stem.replace('g0_', 'g0_t0.')}.{signal_kind}.bin"
    lf_file_path = directory_with_data_path / lf_file_name
    source_data.update(SpikeGLXLFP=dict(file_path=str(lf_file_path), spikeextractors_backend=spikeextractors_backend))
    conversion_options.update(SpikeGLXLFP=dict(stub_test=stub_test))

    # Spikes
    phy_directory_path = directory_with_data_path
    source_data.update(PhySorting=dict(folder_path=str(phy_directory_path), exclude_cluster_groups=["noise", "mua"]))
    conversion_options.update(PhySorting=dict(stub_test=stub_test))

    # Behavior
    source_data.update(Behavior=dict(session_path=str(session_path)))

    # Metadata
    converter = Wen21NWBConverter(source_data=source_data)
    metadata = converter.get_metadata()

    session_start_time = datetime.fromisoformat(metadata["NWBFile"]["session_start_time"])
    tzinfo = dateutil.tz.gettz("America/Los_Angeles")
    session_start_time = session_start_time.replace(tzinfo=tzinfo).isoformat()
    metadata["NWBFile"].update(session_description=session_id, session_start_time=session_start_time)
    metadata_from_yaml = load_dict_from_file(general_metadata_path)
    metadata = dict_deep_update(metadata, metadata_from_yaml)

    ## Subject metadata
    subject = session_id.split("_")[0]
    subject_metadata_from_yaml = load_dict_from_file(general_metadata_path.with_stem("subject_metadata"))
    subject_metadata = subject_metadata_from_yaml[subject]
    metadata["Subject"] = dict_deep_update(metadata["Subject"], subject_metadata)

    # Run conversion
    nwb_file_name = f"{session_id}.nwb"
    nwbfile_path = output_path / nwb_file_name
    converter.run_conversion(
        nwbfile_path=str(nwbfile_path),
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=True,
    )
