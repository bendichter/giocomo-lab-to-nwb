# This script grabs SpikeGLX data and stores it in .nwb files.
# authors: Luiz Tauffer and Ben Dichter
# written for Giocomo Lab
# ------------------------------------------------------------------------------
from nwbn_conversion_tools.ephys.acquisition.spikeglx.spikeglx import Spikeglx2NWB
from ndx_labmetadata_giocomo import LabMetaData_ext
import pynwb
from pynwb.file import Subject
from pynwb.misc import Units
from pynwb.behavior import Position, BehavioralEvents

import numpy as np
import hdf5storage
import copy
import os
import sys
import yaml


def conversion_function(source_paths, f_nwb, metadata, add_spikeglx=False, add_processed=False):
    """
    Copy data stored in a set of .npz files to a single NWB file.

    Parameters
    ----------
    source_paths : dict
        Dictionary with paths to source files/directories. e.g.:
        {'spikeglx data': {'type': 'file', 'path': ''}
         'processed data': {'type': 'file', 'path': ''}}
    f_nwb : str
        Path to output NWB file, e.g. 'my_file.nwb'.
    metadata : dict
        Dictionary containing metadata
    add_spikeglx: bool
    add_processed: bool
    """

    # Source files
    npx_file_path = None
    mat_file_path = None
    for k, v in source_paths.items():
        if source_paths[k]['path'] != '':
            if k == 'spikeglx data':
                npx_file_path = source_paths[k]['path']
            if k == 'processed data':
                mat_file_path = source_paths[k]['path']

    # Remove lab_meta_data from metadata, it will be added later
    metadata0 = copy.deepcopy(metadata)
    metadata0['NWBFile'].pop('lab_meta_data', None)

    # Create nwb
    nwbfile = pynwb.NWBFile(**metadata0['NWBFile'])

    # If adding processed data
    if add_processed:
        # Source matlab data
        matfile = hdf5storage.loadmat(mat_file_path)

        # Adding trial information
        nwbfile.add_trial_column(
            name='trial_contrast',
            description='visual contrast of the maze through which the mouse is running'
        )
        trial = np.ravel(matfile['trial'])
        trial_nums = np.unique(trial)
        position_time = np.ravel(matfile['post'])
        # matlab trial numbers start at 1. To correctly index trial_contract vector,
        # subtracting 1 from 'num' so index starts at 0
        for num in trial_nums:
            trial_times = position_time[trial == num]
            nwbfile.add_trial(start_time=trial_times[0],
                              stop_time=trial_times[-1],
                              trial_contrast=matfile['trial_contrast'][num-1][0])

        # create behavior processing module
        behavior = nwbfile.create_processing_module(
            name='behavior',
            description='behavior processing module'
        )

        # Add mouse position
        position = Position(name=metadata['Behavior']['Position']['name'])
        meta_pos_names = [sps['name'] for sps in metadata['Behavior']['Position']['spatial_series']]

        # Position inside the virtual environment
        pos_vir_meta_ind = meta_pos_names.index('VirtualPosition')
        meta_vir = metadata['Behavior']['Position']['spatial_series'][pos_vir_meta_ind]
        position_virtual = np.ravel(matfile['posx'])
        sampling_rate = 1/(position_time[1] - position_time[0])
        position.create_spatial_series(
            name=meta_vir['name'],
            data=position_virtual,
            starting_time=position_time[0],
            rate=sampling_rate,
            reference_frame=meta_vir['reference_frame'],
            conversion=meta_vir['conversion'],
            description=meta_vir['description'],
            comments=meta_vir['comments']
            )

        # Physical position on the mouse wheel
        pos_phys_meta_ind = meta_pos_names.index('PhysicalPosition')
        meta_phys = metadata['Behavior']['Position']['spatial_series'][pos_phys_meta_ind]
        physical_posx = position_virtual
        trial_gain = np.ravel(matfile['trial_gain'])
        for num in trial_nums:
            physical_posx[trial == num] = physical_posx[trial == num]/trial_gain[num-1]
        position.create_spatial_series(
            name=meta_phys['name'],
            data=physical_posx,
            starting_time=position_time[0],
            rate=sampling_rate,
            reference_frame=meta_phys['reference_frame'],
            conversion=meta_phys['conversion'],
            description=meta_phys['description'],
            comments=meta_phys['comments']
        )

        behavior.add(position)

        # Add timing of lick events, as well as mouse's virtual position during lick event
        lick_events = BehavioralEvents(name=metadata['Behavior']['BehavioralEvents']['name'])
        meta_ts = metadata['Behavior']['BehavioralEvents']['time_series']
        meta_ts['data'] = np.ravel(matfile['lickx'])
        meta_ts['timestamps'] = np.ravel(matfile['lickt'])
        lick_events.create_timeseries(**meta_ts)

        behavior.add(lick_events)

        # Add the recording device, a neuropixel probe
        recording_device = nwbfile.create_device(name=metadata['Ecephys']['Device'][0]['name'])

        # Add ElectrodeGroup
        electrode_group = nwbfile.create_electrode_group(
            name=metadata['Ecephys']['ElectrodeGroup'][0]['name'],
            description=metadata['Ecephys']['ElectrodeGroup'][0]['description'],
            location=metadata['Ecephys']['ElectrodeGroup'][0]['location'],
            device=recording_device
        )

        # Add information about each electrode
        xcoords = np.ravel(matfile['sp'][0]['xcoords'][0])
        ycoords = np.ravel(matfile['sp'][0]['ycoords'][0])
        data_filtered_flag = matfile['sp'][0]['hp_filtered'][0][0]
        if metadata['NWBFile']['lab_meta_data']['high_pass_filtered']:
            filter_desc = 'The raw voltage signals from the electrodes were high-pass filtered'
        else:
            filter_desc = 'The raw voltage signals from the electrodes were not high-pass filtered'
        num_recording_electrodes = xcoords.shape[0]
        recording_electrodes = range(0, num_recording_electrodes)

        # create electrode columns for the x,y location on the neuropixel  probe
        # the standard x,y,z locations are reserved for Allen Brain Atlas location
        nwbfile.add_electrode_column('relativex','electrode x-location on the probe')
        nwbfile.add_electrode_column('relativey','electrode y-location on the probe')
        for idx in recording_electrodes:
            nwbfile.add_electrode(
                id=idx,
                x=np.nan,
                y=np.nan,
                z=np.nan,
                relativex=float(xcoords[idx]),
                relativey=float(ycoords[idx]),
                imp=np.nan,
                location='medial entorhinal cortex',
                filtering=filter_desc,
                group=electrode_group
            )

        # Add information about each unit, termed 'cluster' in giocomo data
        # create new columns in unit table
        nwbfile.add_unit_column(
            name='quality',
            description='labels given to clusters during manual sorting in phy '
                '(1=MUA, 2=Good, 3=Unsorted)'
        )

        # cluster information
        cluster_ids = matfile['sp'][0]['cids'][0][0]
        cluster_quality = matfile['sp'][0]['cgs'][0][0]
        # spikes in time
        spike_times = np.ravel(matfile['sp'][0]['st'][0])  # the time of each spike
        spike_cluster = np.ravel(matfile['sp'][0]['clu'][0])  # the cluster_id that spiked at that time
        for i, cluster_id in enumerate(cluster_ids):
            unit_spike_times = spike_times[spike_cluster == cluster_id]
            waveforms = matfile['sp'][0]['temps'][0][cluster_id]
            nwbfile.add_unit(
                id=int(cluster_id),
                spike_times=unit_spike_times,
                quality=cluster_quality[i],
                waveform_mean=waveforms,
                electrode_group=electrode_group
            )

        # Trying to add another Units table to hold the results of the automatic spike sorting
        # create TemplateUnits units table
        template_units = Units(
            name='TemplateUnits',
            description='units assigned during automatic spike sorting'
        )
        template_units.add_column(
            name='tempScalingAmps',
            description='scaling amplitude applied to the template when extracting spike',
            index=True
        )
        # information on extracted spike templates
        spike_templates = np.ravel(matfile['sp'][0]['spikeTemplates'][0])
        spike_template_ids = np.unique(spike_templates)
        # template scaling amplitudes
        temp_scaling_amps = np.ravel(matfile['sp'][0]['tempScalingAmps'][0])
        for i, spike_template_id in enumerate(spike_template_ids):
            template_spike_times = spike_times[spike_templates == spike_template_id]
            temp_scaling_amps_per_template = temp_scaling_amps[spike_templates == spike_template_id]
            template_units.add_unit(
                id=int(spike_template_id),
                spike_times=template_spike_times,
                electrode_group=electrode_group,
                tempScalingAmps=temp_scaling_amps_per_template
            )

        # create ecephys processing module
        spike_template_module = nwbfile.create_processing_module(
            name='ecephys',
            description='units assigned during automatic spike sorting'
        )
        # add template_units table to processing module
        spike_template_module.add(template_units)

    # Add other fields
    # Add lab_meta_data
    if 'lab_meta_data' in metadata['NWBFile']:
        lab_metadata = LabMetaData_ext(
            name=metadata['NWBFile']['lab_meta_data']['name'],
            acquisition_sampling_rate=metadata['NWBFile']['lab_meta_data']['acquisition_sampling_rate'],
            number_of_electrodes=metadata['NWBFile']['lab_meta_data']['number_of_electrodes'],
            file_path=metadata['NWBFile']['lab_meta_data']['file_path'],
            bytes_to_skip=metadata['NWBFile']['lab_meta_data']['bytes_to_skip'],
            raw_data_dtype=metadata['NWBFile']['lab_meta_data']['raw_data_dtype'],
            high_pass_filtered=metadata['NWBFile']['lab_meta_data']['high_pass_filtered'],
            movie_start_time=metadata['NWBFile']['lab_meta_data']['movie_start_time'],
            subject_brain_region=metadata['NWBFile']['lab_meta_data']['subject_brain_region']
        )
        nwbfile.add_lab_meta_data(lab_metadata)

    # add information about the subject of the experiment
    if 'Subject' in metadata:
        experiment_subject = Subject(**metadata['Subject'])
        nwbfile.subject = experiment_subject

    # If adding SpikeGLX data
    if add_spikeglx:
        # Create extractor for SpikeGLX data
        extractor = Spikeglx2NWB(nwbfile=nwbfile, metadata=metadata0, npx_file=npx_file_path)
        # Add acquisition data
        extractor.add_acquisition(es_name='ElectricalSeries', metadata=metadata['Ecephys'])
        # Run spike sorting method
        # extractor.run_spike_sorting()
        # Save content to NWB file
        extractor.save(to_path=f_nwb)
    else:
        # Write to nwb file
        with pynwb.NWBHDF5IO(f_nwb, 'w') as io:
            io.write(nwbfile)
            print(nwbfile)

    # Check file was saved and inform on screen
    print('File saved at:')
    print(f_nwb)
    print('Size: ', os.stat(f_nwb).st_size/1e6, ' mb')


# If called directly fom terminal
if __name__ == '__main__':

    if len(sys.argv) < 4:
        print('Error: Please provide source files, nwb file name and metafile.')

    source_paths = {}
    source_paths['spikeglx data'] = {'type': 'file', 'path': sys.argv[1]}
    f_nwb = sys.argv[2]

    # Load metadata from YAML file
    metafile = sys.argv[3]
    with open(metafile) as f:
       metadata = yaml.safe_load(f)

    conversion_function(source_paths=source_paths,
                        f_nwb=f_nwb,
                        metadata=metadata)
