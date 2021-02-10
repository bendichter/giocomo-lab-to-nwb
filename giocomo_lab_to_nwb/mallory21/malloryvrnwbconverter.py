import datetime
from pathlib import Path
from typing import Optional, Union

import h5py
import numpy as np
import pandas as pd
from ndx_events import Events
from nwb_conversion_tools import NWBConverter, SpikeGLXRecordingInterface, SpikeGLXLFPInterface
from nwb_conversion_tools.basedatainterface import BaseDataInterface
from pynwb import NWBFile, TimeSeries
from pynwb.behavior import Position, SpatialSeries, EyeTracking
from pynwb.file import Subject
from pytz import timezone

from giocomo_lab_to_nwb.utils import check_module

OptionalArrayType = Optional[Union[list, np.ndarray]]
PathType = Union[Path, str]

year = '19'


def get_data(file: h5py.File, str_: str, row=0):
    return file[file['cell_info'][str_][row][0]][:].ravel()


def get_str(file: h5py.File, str_: str, row=0) -> str:
    return ''.join([chr(x) for x in file[file['cell_info'][str_][row][0]]])


def get_track_session_info(fpath: str):
    file = h5py.File(fpath, 'r')
    return get_str(file, 'animal_id'), get_str(file, 'session_id')


class GiocomoTrackProcessedInterface(BaseDataInterface):

    @classmethod
    def get_source_schema(cls):
        return dict(
            required=['file_path'],
            properties=dict(
                file_path=dict(type='string')
            )
        )

    def get_metadata(self):
        file_path = self.source_data['file_path']

        subject_id, session_id = get_track_session_info(file_path)
        self.subject_id = subject_id
        self.datestr = session_id[:4]

        session_start_time = datetime.datetime.strptime(year + self.datestr, '%y%m%d')
        session_start_time = timezone('US/Pacific').localize(session_start_time)

        file = h5py.File(file_path, 'r')
        trial_contrast = get_data(file, 'trial_contrast')

        return dict(
            NWBFile=dict(
                session_description='straight track virtual reality.',
                identifier=session_id,
                session_start_time=session_start_time,
                lab='Giocomo',
                institution='Stanford University',
                experiment_description='trial contrast: {}'.format(int(trial_contrast[0])),
                subject=Subject(
                    subject_id=subject_id
                )
            )
        )

    def run_conversion(self, nwbfile: NWBFile, metadata: dict):
        file_path = self.source_data['file_path']

        file = h5py.File(file_path, 'r')
        cell_info = file['cell_info']

        cell_ids = [''.join([chr(x[0]) for x in file[x[0]]]) for x in cell_info['cell_id']]

        times = get_data(file, 'time')
        body_pos = get_data(file, 'body_position')
        body_speed = get_data(file, 'body_speed')
        horizontal_eye_pos = get_data(file, 'horizontal_eye_position')
        vertial_eye_pos = get_data(file, 'vertical_eye_position')
        horizontal_eye_vel = get_data(file, 'horiztonal_eye_velocity')
        vertial_eye_vel = get_data(file, 'vertical_eye_velocity')

        all_spike_times = [file[x[0]][:].ravel() for x in cell_info['spike_times']]

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
                name='eye_velocity',
                data=np.c_[horizontal_eye_vel, vertial_eye_vel],
                timestamps=spatial_series,
                unit='unknown'
            )
        )

        for spike_times, cell_id in zip(all_spike_times, cell_ids):
            id_ = int(cell_id.split('_')[-1])
            nwbfile.add_unit(spike_times=spike_times, id=id_)

        return nwbfile


class MalloryEventsInterface(BaseDataInterface):

    @classmethod
    def get_source_schema(cls):
        return dict(
            required=['session_path'],
            properties=dict(
                session_path=dict(type='string')
            )
        )

    def run_conversion(
            self,
            nwbfile: NWBFile,
            metadata: dict = None,
            write_licks: bool = True,
            write_rewards: bool = True,
            write_trials: bool = True
    ):

        session_fpath = self.source_data['session_path']

        behav_mod = check_module(nwbfile, 'behavior')

        if write_licks:
            lick_timestamps = pd.read_csv(
                next(Path(session_fpath).glob('*{}.txt'.format('licks'))),
                sep='\t',
                names=['pos', 'time']
            )['time'].values

            events = Events(
                name='licks',
                description='times when the subject licked in seconds',
                timestamps=lick_timestamps
            )
            behav_mod.add(events)

        # rewards
        if write_rewards:
            rewards_timestamps = pd.read_csv(
                next(Path(session_fpath).glob('*{}.txt'.format('reward_times'))),
                sep='\t',
                names=['time', 'rewards']
            )['time'].values

            events = Events(
                name='rewards',
                description='times when the subject was rewarded in seconds',
                timestamps=rewards_timestamps
            )
            behav_mod.add(events)

        # trials
        if write_trials:
            df = pd.read_csv(
                next(Path(session_fpath).glob('*{}.txt'.format('trial_times'))),
                sep='\t',
                names=[
                    'start_time',
                    'visual_contrast',
                    'running_wheel_gain',
                    'reward'
                ]
            )

            nwbfile.add_trial_column(
                'visual_contrast',
                'the visual contrast setting of that trial'
            )

            nwbfile.add_trial_column(
                'running_wheel_gain',
                'how to match distance on running wheel to distance in'
                ' virtual environment'
            )

            nwbfile.add_trial_column(
                'reward',
                'if the particular trial is rewarded or not'
            )

            for i in range(len(df)):
                kwargs = df.iloc[i].to_dict()
                kwargs['reward'] = bool(kwargs['reward'])

                if i == len(df) - 1:
                    kwargs.update(stop_time=np.nan)
                else:
                    kwargs.update(stop_time=df.iloc[i + 1]['start_time'])

                nwbfile.add_trial(**kwargs)


class MalloryVRNWBConverter(NWBConverter):
    data_interface_classes = dict(
        SpikeGLXRecording=SpikeGLXRecordingInterface,
        SpikeGLXLFP=SpikeGLXLFPInterface,
        GiocomoTrackProcessed=GiocomoTrackProcessedInterface,
        Events=MalloryEventsInterface
    )
