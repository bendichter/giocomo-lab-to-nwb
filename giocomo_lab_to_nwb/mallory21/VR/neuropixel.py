import pandas as pd
import os
from glob import glob
from ndx_events import Events

from giocomo_lab_to_nwb.utils import check_module


def find_path(subject_id, datestr, np_fpath, label='licks'):
    lick_paths = glob(
        os.path.join(
            np_fpath,
            '{}_{}*'.format(subject_id, datestr),
            '*{}.txt'.format(label)
        )
    )

    if len(lick_paths) == 1:
        return lick_paths[0]


def read_licks(lick_fpath):
    return pd.read_csv(
        lick_fpath,
        sep='\t',
        names=['pos', 'time']
    )['time'].values


def read_rewards(reward_fpath):
    return pd.read_csv(
        reward_fpath,
        sep='\t',
        names=['time', 'reward']
    )['time'].values


def add_events(nwbfile, name, description, timestamps):

    events = Events(
        name=name,
        description=description,
        timestamps=timestamps
    )
    behav_mod = check_module(nwbfile, 'behavior')
    behav_mod.add(events)

