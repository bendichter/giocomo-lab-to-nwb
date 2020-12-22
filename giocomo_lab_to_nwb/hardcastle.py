import datetime
from glob import glob
from os import path
from tqdm import tqdm

import h5py
import numpy as np
from ndx_task import Task, Tasks
from pynwb import NWBFile, NWBHDF5IO, TimeSeries
from pynwb.behavior import Position, SpatialSeries, EyeTracking
from pynwb.file import Subject
from scipy.io import loadmat


def get_data(file: h5py.File, str_: str, row=0):
    return file[file['cell_info'][str_][row][0]][:].ravel()


def get_str(file: h5py.File, str_: str, row=0) -> str:
    return ''.join([chr(x) for x in file[file['cell_info'][str_][row][0]]])


def convert_track_file(fpath: str):
    file = h5py.File(fpath, 'r')
    cell_info = file['cell_info']

    cell_ids = [''.join([chr(x[0]) for x in file[x[0]]]) for x in cell_info['cell_id']]
    animal_id = get_str(file, 'animal_id')
    session_id = get_str(file, 'session_id')

    times = get_data(file, 'time')
    body_pos = get_data(file, 'body_position')
    body_speed = get_data(file, 'body_speed')
    horizontal_eye_pos = get_data(file, 'horizontal_eye_position')
    vertial_eye_pos = get_data(file, 'vertical_eye_position')
    horizontal_eye_vel = get_data(file, 'horiztonal_eye_velocity')
    vertial_eye_vel = get_data(file, 'vertical_eye_velocity')
    trial_contrast = get_data(file, 'trial_contrast')

    all_spike_times = [file[x[0]][:].ravel() for x in cell_info['spike_times']]

    year = '20'

    session_start_time = datetime.datetime.strptime(year + session_id[:4], '%y%m%d')

    nwbfile = NWBFile(
        session_description='straight track.',
        identifier=session_id,
        session_start_time=session_start_time,
        lab='Giocomo',
        institution='Stanford University',
        experiment_description='trial contrast: {}'.format(int(trial_contrast[0])),
        subject=Subject(
            subject_id=animal_id
        )
    )

    nwbfile.add_lab_meta_data(
        Tasks(
            tasks=[
                Task(
                    name='straight track',
                    description='subject running on straight track in virtual reality',
                    navigation=True
                )
            ]
        )
    )

    behavior = nwbfile.create_processing_module(
        name='behavior',
        description='contains processed behavioral data'
    )

    spatial_series = SpatialSeries(
        name='position',
        data=body_pos,
        timestamps=times,
        conversion=.01,
        reference_frame='on track. Position is in VR.'
    )

    behavior.add(
        Position(
            spatial_series=spatial_series
        )
    )

    behavior.add(
        TimeSeries(
            name='body_speed',
            data=body_speed,
            timestamps=spatial_series,
            unit='cm/s'
        )
    )

    behavior.add(
        EyeTracking(
            spatial_series=SpatialSeries(
                name='eye_position',
                data=np.c_[horizontal_eye_pos, vertial_eye_pos],
                timestamps=spatial_series,
                reference_frame='unknown'
            )
        )
    )

    behavior.add(
        TimeSeries(
            name='eye velocity',
            data=np.c_[horizontal_eye_vel, vertial_eye_vel],
            timestamps=spatial_series,
            unit='unknown'
        )
    )

    for spike_times, cell_id in zip(all_spike_times, cell_ids):
        id_ = int(cell_id.split('_')[-1])
        nwbfile.add_unit(spike_times=spike_times, id=id_)

    with NWBHDF5IO(fpath[:-3] + 'nwb', 'w') as io:
        io.write(nwbfile)


def convert_freely_moving_with_inertial_sensor(fpath: str):

    matdata = loadmat(fpath)
    nrows = len(matdata['cell_info']['cell_id'][0])

    session_ids = [matdata['cell_info']['cell_id'][0][row][0].split('_')[:2] for row in range(nrows)]

    inverse = np.unique(session_ids, axis=0, return_index=True, return_inverse=True)[2]

    inds = []
    last = -1
    for row, index in enumerate(inverse):
        if index == last:
            inds[-1].append(row)
        else:
            last = index
            inds.append([row])

    for session in tqdm(inds):

        row = session[0]
        subject_id, session_id = matdata['cell_info']['cell_id'][0][row][0].split('_')[:2]

        year = '20'
        session_start_time = datetime.datetime.strptime(year + session_id[:4], '%y%m%d')

        data = {x: matdata['cell_info'][x][0][row].ravel() for x in
                (
                    'time',
                    'body_position_x',
                    'body_position_y',
                    'body_speed',
                    'azimuthal_head_direction',
                    'azimuthal_head_velocity',
                    'arena_size_cm',
                    'pitch',
                    'roll'
                )
                }

        data['cell_ids'] = [matdata['cell_info']['cell_id'][0][row][0].split('_')[2] for row in session]
        data['spike_times'] = [matdata['cell_info']['spike_times'][0][row].ravel() for row in session]

        nwbfile = NWBFile(
            session_description='free exploration.',
            identifier=session_id,
            session_start_time=session_start_time,
            lab='Giocomo',
            institution='Stanford University',
            experiment_description='arena size (cm): {}'.format(data['arena_size_cm'])
        )

        nwbfile.add_lab_meta_data(
            Tasks(
                tasks=[
                    Task(
                        name='free exploration',
                        description='subject freely exploring environment',
                        navigation=True
                    )
                ]
            )
        )

        behavior = nwbfile.create_processing_module(
            name='behavior',
            description='contains processed behavioral data'
        )

        spatial_series = SpatialSeries(
            name='position',
            data=np.c_[
                data['body_position_x'],
                data['body_position_y']
            ],
            timestamps=data['time'],
            conversion=.01,
            reference_frame='unknown'
        )

        behavior.add(
            Position(
                spatial_series=spatial_series
            )
        )

        behavior.add(
            TimeSeries(
                name='body_speed',
                data=data['body_speed'],
                timestamps=spatial_series,
                unit='cm/s'
            )
        )

        behavior.add(
            TimeSeries(
                name='head_direction',
                description='azimuth, pitch, roll',
                data=np.c_[
                    data['azimuthal_head_direction'],
                    data['pitch'],
                    data['roll']
                ],
                timestamps=spatial_series,
                unit='radians'
            )
        )

        behavior.add(
            TimeSeries(
                name='azimuthal_head_velocity',
                data=data['azimuthal_head_velocity'],
                unit='radians/s',
                timestamps=spatial_series
            )
        )

        nwbfile.add_unit_column('cell_id', 'string-based cell id')
        for spike_times, cell_id in zip(data['spike_times'], data['cell_ids']):
            nwbfile.add_unit(spike_times=spike_times, cell_id=cell_id)

        with NWBHDF5IO(subject_id + session_id + '.nwb', 'w') as io:
            io.write(nwbfile)


def convert_freely_moving_without_inertial_sensor(fpath: str):

    file = h5py.File(fpath, 'r')

    nrows = len(file['cell_info']['cell_id'])
    session_ids = [get_str(file, 'cell_id', row).split('_')[:2] for row in range(nrows)]

    inverse = np.unique(session_ids, axis=0, return_index=True, return_inverse=True)[2]

    inds = []
    last = -1
    for row, index in enumerate(inverse):
        if index == last:
            inds[-1].append(row)
        else:
            last = index
            inds.append([row])

    for session in tqdm(inds):
        row = session[0]
        data = {
            x: get_data(file, x, row) for x in ('time', 'body_position_x', 'body_position_y', 'body_speed',
                                                'arena_size_cm', 'azimuthal_head_direction', 'azimuthal_head_velocity')
        }

        subject_id = get_str(file, 'animal_id', row)

        all_spike_times = [get_data(file, 'spike_times', row) for row in session]
        cell_ids = [get_str(file, 'cell_id', row).split('_')[-1] for row in session]

        year = '20'
        if subject_id in ('Reeves', 'Ringo'):  # e.g. 'Ringo_29_July_04+01+02+03_T1C2'
            components = get_str(file, 'cell_id', row).split('_')
            session_id = '_'.join(components[1:-1])
            session_start_time = datetime.datetime.strptime(year + ''.join(components[1:-2]), '%y%d%B')

        elif subject_id in ('Ella', 'Barbara'):  # e.g. 'Ella_1029_2+_1_T1C2'
            components = get_str(file, 'cell_id', row).split('_')
            session_id = '_'.join(components[1:-1])
            try:
                session_start_time = datetime.datetime.strptime(year + components[1], '%y%m%d')
            except:
                session_start_time = datetime.datetime.strptime(year + components[1], '%yk%m%d')

        elif subject_id in ('Magnolia', 'Azalea', 'Camelia', 'Crocus', 'Lupine'):  # e.g. 'Magnolia_rectangle_013001_T1C1'
            components = get_str(file, 'cell_id', row).split('_')
            session_id = '_'.join(components[1:-1])
            session_start_time = datetime.datetime.strptime(year + components[2][:4], '%y%m%d')

        else:
            session_id = get_str(file, 'cell_id', row).split('_')[1]
            session_start_time = datetime.datetime.strptime(year + session_id[:4], '%y%m%d')

        nwbfile = NWBFile(
            session_description='free exploration.',
            identifier=session_id,
            session_start_time=session_start_time,
            lab='Giocomo',
            institution='Stanford University',
            experiment_description='arena size (cm): {}'.format(data['arena_size_cm'])
        )

        nwbfile.add_lab_meta_data(
            Tasks(
                tasks=[
                    Task(
                        name='free exploration',
                        description='subject freely exploring environment',
                        navigation=True
                    )
                ]
            )
        )

        behavior = nwbfile.create_processing_module(
            name='behavior',
            description='contains processed behavioral data')

        spatial_series = SpatialSeries(
            name='position',
            data=np.c_[data['body_position_x'], data['body_position_y']],
            timestamps=data['time'],
            conversion=.01,
            reference_frame='unknown'
        )

        behavior.add(Position(spatial_series=spatial_series))

        behavior.add(TimeSeries(
            name='body_speed',
            data=data['body_speed'],
            timestamps=spatial_series,
            unit='cm/s'))

        behavior.add(TimeSeries(
            name='head_direction',
            description='azimuth',
            data=data['azimuthal_head_direction'],
            timestamps=spatial_series,
            unit='radians'))

        behavior.add(TimeSeries(
            name='azimuthal_head_velocity',
            data=data['azimuthal_head_velocity'],
            unit='radians/s',
            timestamps=spatial_series))

        nwbfile.add_unit_column('cell_id', 'string-based cell id')
        for spike_times, cell_id in zip(all_spike_times, cell_ids):
            nwbfile.add_unit(spike_times=spike_times, cell_id=cell_id)

        with NWBHDF5IO(subject_id + session_id + '.nwb', 'w') as io:
            io.write(nwbfile)


#cell_info_files = glob('/Volumes/easystore5T/data/Giocomo/maze_and_free_to_publish/src/cell_info_session*.mat')
#for cell_info_file in cell_info_files:
#    convert_track_file(cell_info_file)

#convert_all('/Volumes/easystore5T/data/Giocomo/maze_and_free_to_publish/src')
#convert_freely_moving('/Volumes/easystore5T/data/Giocomo/maze_and_free_to_publish/src/Freely_moving_data_with_inertial_sensor.mat')
#fpath = '/Volumes/easystore5T/data/Giocomo/maze_and_free_to_publish/src/Freely_moving_data_without_inertial_sensor.mat'
#convert_freely_moving_without_inertial_sensor(fpath)


#convert_freely_moving_without_inertial_sensor('/Volumes/easystore5T/data/Giocomo/maze_and_free_to_publish/src/Freely_moving_data_without_inertial_sensor.mat')
#convert_freely_moving_with_inertial_sensor(
# '/Volumes/easystore5T/data/Giocomo/maze_and_free_to_publish/src/Freely_moving_data_with_inertial_sensor.mat')

#cell_info_files = glob('/Volumes/easystore5T/data/Giocomo/maze_and_free_to_publish/src/cell_info_session*.mat')
#for cell_info_file in cell_info_files:
#    convert_track_file(cell_info_file)

convert_track_file('/Volumes/easystore5T/data/Giocomo/maze_and_free_to_publish/src/cell_info_session11.mat')
