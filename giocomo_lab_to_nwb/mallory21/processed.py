import datetime

import h5py
import numpy as np
from pynwb import NWBFile, NWBHDF5IO, TimeSeries
from pynwb.behavior import Position, SpatialSeries
from pynwb.file import Subject
from pytz import timezone
from scipy.io import loadmat
from tqdm import tqdm

from .utils import get_data, get_str

year = '19'


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

        session_start_time = datetime.datetime.strptime(year + session_id[:4], '%y%m%d')
        session_start_time = timezone('US/Pacific').localize(session_start_time)

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
            lab='Giocomo Lab',
            institution='Stanford University',
            experiment_description='arena size (cm): {}'.format(data['arena_size_cm']),
            subject=Subject(subject_id=subject_id)
        )

        behavior = nwbfile.create_processing_module(
            name='behavior',
            description='contains processed behavioral data'
        )

        spatial_series = SpatialSeries(
            name='position',
            data=np.c_[data['body_position_x'], data['body_position_y']],
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

        # test read
        with NWBHDF5IO(subject_id + session_id + '.nwb', 'r') as io:
            io.read()


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
            x: get_data(file, x, row) for x in (
                'time',
                'body_position_x',
                'body_position_y',
                'body_speed',
                'arena_size_cm',
                'azimuthal_head_direction',
                'azimuthal_head_velocity'
            )
        }

        subject_id = get_str(file, 'animal_id', row)

        all_spike_times = [get_data(file, 'spike_times', row) for row in session]
        cell_ids = [get_str(file, 'cell_id', row).split('_')[-1] for row in session]

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

        session_start_time = timezone('US/Pacific').localize(session_start_time)

        nwbfile = NWBFile(
            session_description='free exploration.',
            identifier=session_id,
            session_start_time=session_start_time,
            lab='Giocomo',
            institution='Stanford University',
            experiment_description='arena size (cm): {}'.format(data['arena_size_cm']),
            subject=Subject(subject_id=subject_id, species="Mus musculus")
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

        # test read
        with NWBHDF5IO(subject_id + session_id + '.nwb', 'r') as io:
            io.read()
