import datetime

import numpy as np
from pynwb import NWBFile

from ..read_axona import importspikes

spikes_fpath = '/Volumes/easystore5T/data/Giocomo/maze_and_free_to_publish/raw/052301.6'


def read_spikes(spikes_fpath):

    name = 'tetrode{}'.format(spikes_fpath.split('.')[-1])

    data_dict, params = importspikes(spikes_fpath)
    data = np.swapaxes(
        np.dstack(
            [data_dict['ch{}'.format(i)] for i in range(1, 5)]
        ), 1, 2)

    timestamps = data['t'].ravel()

    return dict(name=name, data=data, timestamps=timestamps)


nwbfile = NWBFile('aa', 'bb', datetime.datetime.now())

tetrodes = ['tetrode5', 'tetrode6']

electrodes_dict = dict()
for itetrode, tetrode in enumerate(tetrodes):
    device = nwbfile.create_device(tetrode)
    nwbfile.add_electrode_group(
        name=tetrode,
        description='a 4-wired probe',
        location='entorhinal cortex',
        device=device
    )
    for _ in range(4):
        nwbfile.add_electrode(
            x=np.nan,
            y=np.nan,
            z=np.nan,
            location='entorhinal cortex',
            filtering='unknown'
        )
    electrodes_dict.update({
        tetrode: nwbfile.create_electrode_table_region(
            list(range(itetrode * 4, itetrode * 4 + 4)),
            description='electrodes for ' + tetrode,
            name=tetrode + '_electrodes'
        )
    })

