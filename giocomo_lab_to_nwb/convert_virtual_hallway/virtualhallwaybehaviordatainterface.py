"""Authors: Szonja Weigl, Luiz Tauffer and Ben Dichter."""
from pathlib import Path

from hdmf.backends.hdf5 import H5DataIO
from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils import get_base_schema, get_schema_from_hdmf_class
from pynwb.behavior import SpatialSeries, BehavioralEvents
from pynwb import NWBFile, TimeSeries
from pynwb.misc import Units
from scipy.io import loadmat
import numpy as np

from ndx_labmetadata_giocomo import LabMetaData_ext


def check_module(nwbfile, name, description=None):
    """
    Check if processing module exists. If not, create it. Then return module.

    Parameters
    ----------
    nwbfile: pynwb.NWBFile
    name: str
    description: str | None (optional)

    Returns
    -------
    pynwb.module

    """
    if name in nwbfile.modules:
        return nwbfile.modules[name]
    else:
        if description is None:
            description = name
        return nwbfile.create_processing_module(name, description)


class VirtualHallwayDataInterface(BaseDataInterface):
    """Conversion class for the Virtual Hallway Task behavioral interface."""

    @classmethod
    def get_source_schema(cls):
        """Compile input schemas from each of the data interface classes."""
        return dict(
            required=['file_path'],
            properties=dict(
                file_path=dict(type='string')
            )
        )

    def get_metadata_schema(self):
        """Compile metadata schemas from each of the data interface objects."""
        metadata_schema = get_base_schema()
        metadata_schema['properties']['SpatialSeries'] = get_schema_from_hdmf_class(SpatialSeries)
        required_fields = ['SpatialSeries']
        for field in required_fields:
            metadata_schema['required'].append(field)
        return metadata_schema

    def run_conversion(self, nwbfile: NWBFile, metadata: dict):
        """Conversion function for the Virtual Hallway task behavior interface."""

        # Add lab metadata to nwbfile
        if 'lab_meta_data' in metadata:
            if 'neurodata_type' in metadata['lab_meta_data']:
                metadata['lab_meta_data'].pop('neurodata_type')
            lab_meta_data = LabMetaData_ext(**metadata['lab_meta_data'])
            nwbfile.add_lab_meta_data(lab_meta_data)

        mat_file_name = self.source_data['file_path']
        if Path(mat_file_name).is_file():
            virtual_hallway_data = loadmat(mat_file_name, struct_as_record=False, squeeze_me=True)

            # Add trial information
            trials = virtual_hallway_data['trial']
            times = virtual_hallway_data['post']
            trial_nums = np.unique(trials)
            for trial_num in trial_nums:
                nwbfile.add_trial(start_time=times[trials == trial_num][0],
                                  stop_time=times[trials == trial_num][-1])

            # matlab trial numbers start at 1. To correctly index trial_contract vector,
            # subtracting 1 from 'trial_num' so index starts at 0
            trial_contrast = [virtual_hallway_data['trial_contrast'][num - 1] for num in trial_nums]
            nwbfile.add_trial_column(name='trial_contrast',
                                     description='visual contrast of the maze through '
                                                 'which the mouse is running',
                                     data=trial_contrast)

            # Add mouse virtual position as TimeSeries object
            virtual_position = virtual_hallway_data['posx']
            sampling_rate = 1 / (times[1] - times[0])
            position_ts = TimeSeries(name='VirtualPosition',
                                     data=H5DataIO(virtual_position, compression="gzip"),
                                     unit='meter',
                                     conversion=0.01,
                                     resolution=np.nan,
                                     rate=sampling_rate,
                                     starting_time=times[0],
                                     description='Subject position in the virtual hallway.',
                                     comments='Values should be between 0 and 4 meters. '
                                              'Values greater than 4 meters mean that the mouse'
                                              ' briefly exited the maze.')

            # Add mouse physical position
            physical_position = []
            for trial_num in trial_nums:
                trial_position = virtual_position[trials == trial_num]
                trial_gain = virtual_hallway_data['trial_gain'][trial_num - 1]
                physical_position.extend(trial_position / trial_gain)

            physical_position_ts = TimeSeries(name='PhysicalPosition',
                                              data=H5DataIO(physical_position, compression="gzip"),
                                              unit='meter',
                                              conversion=0.01,
                                              resolution=np.nan,
                                              rate=sampling_rate,
                                              starting_time=times[0],
                                              description='Physical location on the wheel measured'
                                                          ' since the beginning of the trial.',
                                              comments='Physical location found by dividing '
                                                       'the virtual position by the trial_gain.')

            # Add lick events
            events_ts = TimeSeries(name='LickEvents',
                                   data=H5DataIO(virtual_hallway_data['lickx'],
                                                 compression="gzip"),
                                   unit='meter',
                                   conversion=0.01,
                                   resolution=np.nan,
                                   timestamps=H5DataIO(virtual_hallway_data['lickt'],
                                                       compression="gzip"),
                                   description='Subject position in virtual hallway '
                                               'during the lick.')

            lick_events = BehavioralEvents(name='BehavioralEvents',
                                           time_series=events_ts)

            behavioral_processing_module = check_module(nwbfile, 'behavior',
                                                        'contains processed behavioral data')
            behavioral_processing_module.add_data_interface(position_ts)
            behavioral_processing_module.add_data_interface(physical_position_ts)
            behavioral_processing_module.add_data_interface(lick_events)

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
