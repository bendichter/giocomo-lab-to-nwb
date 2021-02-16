"""Authors: Szonja Weigl, Luiz Tauffer and Ben Dichter."""
from pathlib import Path
from typing import Optional

from nwb_conversion_tools import NWBConverter, SpikeGLXRecordingInterface, SpikeGLXLFPInterface
from pynwb import NWBFile, NWBHDF5IO
from pynwb.misc import Units
from scipy.io import loadmat
import numpy as np

from .virtualhallwaybehaviordatainterface import VirtualHallwayDataInterface
from ..utils import check_module


class VirtualHallwayNWBConverter(NWBConverter):
    """Conversion class for Virtual Hallway Task."""

    data_interface_classes = dict(
        SpikeGLXRecording=SpikeGLXRecordingInterface,
        SpikeGLXLFP=SpikeGLXLFPInterface,
        VirtualHallwayData=VirtualHallwayDataInterface
    )

    def get_metadata(self):
        metadata = super().get_metadata()
        behavior_file_path = Path(
            self.data_interface_objects['VirtualHallwayData'].source_data['file_path'])
        session_id = behavior_file_path.stem

        metadata['NWBFile'].update(
            institution='Stanford University School of Medicine',
            lab='Giocomo',
            session_id=session_id
        )

        return metadata

    def run_conversion(self, metadata: dict, save_to_file: bool = True,
                       nwbfile_path: Optional[str] = None,
                       overwrite: bool = False, nwbfile: [NWBFile] = None,
                       conversion_options: Optional[dict] = None):

        nwbfile = super().run_conversion(
            metadata=metadata,
            save_to_file=False,
            conversion_options=conversion_options
        )

        mat_file_name = self.data_interface_objects['VirtualHallwayData'].source_data['file_path']

        if Path(mat_file_name).is_file():
            virtual_hallway_data = loadmat(mat_file_name, struct_as_record=False, squeeze_me=True)

            xcoords = virtual_hallway_data['sp'].xcoords
            ycoords = virtual_hallway_data['sp'].ycoords
            num_recording_electrodes = xcoords.shape[0]
            if metadata['lab_meta_data']['high_pass_filtered']:
                filtering_desc = 'The raw voltage signals from the electrodes were high-pass filtered'
            else:
                filtering_desc = 'The raw voltage signals from the electrodes were not high-pass filtered'
            for idx in range(num_recording_electrodes):
                nwbfile.add_electrode(
                    id=idx,
                    x=np.nan,
                    y=np.nan,
                    z=np.nan,
                    rel_x=float(xcoords[idx]),
                    rel_y=float(ycoords[idx]),
                    imp=np.nan,
                    location='medial entorhinal cortex',
                    filtering=filtering_desc,
                    shank_electrode_number=idx,  # not sure
                    group=nwbfile.get_electrode_group()
                )

            # Add information about each unit, termed 'cluster' in giocomo data
            # create new columns in unit table
            nwbfile.add_unit_column(
                name='quality',
                description='labels given to clusters during manual sorting in phy '
                            '(1=MUA, 2=Good, 3=Unsorted)'
            )

            # cluster information
            cluster_ids = virtual_hallway_data['sp'].cids
            cluster_quality = virtual_hallway_data['sp'].cgs
            # spikes in time
            spike_times = virtual_hallway_data['sp'].st
            # the cluster_id that spiked at that time
            spike_cluster = virtual_hallway_data['sp'].clu
            for i, cluster_id in enumerate(cluster_ids):
                unit_spike_times = spike_times[spike_cluster == cluster_id]
                waveforms = virtual_hallway_data['sp'].temps[cluster_id]
                nwbfile.add_unit(
                    id=int(cluster_id),
                    spike_times=unit_spike_times,
                    quality=cluster_quality[i],
                    waveform_mean=waveforms,
                    electrode_group=nwbfile.get_electrode_group()
                )

            # create TemplateUnits units table to hold the results of the automatic spike sorting
            template_units = Units(
                name='TemplateUnits',
                description='units assigned during automatic spike sorting')
            template_units.add_column(
                name='tempScalingAmps',
                description='scaling amplitude applied to the template when extracting spike',
                index=True)
            # information on extracted spike templates
            spike_templates = virtual_hallway_data['sp'].spikeTemplates
            spike_template_ids = np.unique(spike_templates)
            # template scaling amplitudes
            temp_scaling_amps = virtual_hallway_data['sp'].tempScalingAmps
            for i, spike_template_id in enumerate(spike_template_ids):
                template_spike_times = spike_times[spike_templates == spike_template_id]
                temp_scaling_amps_per_template = temp_scaling_amps[
                    spike_templates == spike_template_id]
                template_units.add_unit(
                    id=int(spike_template_id),
                    spike_times=template_spike_times,
                    electrode_group=nwbfile.get_electrode_group(),
                    tempScalingAmps=temp_scaling_amps_per_template
                )

            spike_template_module = check_module(nwbfile, 'ecephys',
                                                        'units assigned during automatic spike sorting')
            spike_template_module.add(template_units)

        if nwbfile_path is None:
            raise TypeError(
                "A path to the output file must be provided, but nwbfile_path got value None")

        if Path(nwbfile_path).is_file() and not overwrite:
            mode = "r+"
        else:
            mode = "w"

        with NWBHDF5IO(nwbfile_path, mode=mode) as io:
            if mode == "r+":
                nwbfile = io.read()

            io.write(nwbfile)
        print(f"NWB file saved at {nwbfile_path}!")
