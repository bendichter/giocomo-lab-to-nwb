from pathlib import Path
from pynwb import NWBFile
from hdmf.backends.hdf5.h5_utils import H5DataIO
from pynwb.behavior import Position, SpatialSeries
from nwb_conversion_tools.tools.nwb_helpers import get_module
from ndx_events import Events
import pandas as pd

from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils.types import FolderPathType

class Wen21EventsInterface(BaseDataInterface):
    def __init__(self, session_path: FolderPathType):
        super().__init__(session_path=session_path)

    def run_conversion(
        self,
        nwb_file: NWBFile,
        metadata: dict
    ):

        behavior_module = get_module(nwb_file, "behavior")
        session_path = Path(self.source_data["session_path"])

        # Add positions
        position_file_path_list = list(session_path.glob("*position.txt"))
        for position_file_path in position_file_path_list:
            position_file_name = position_file_path.name
            file_epoch_name = position_file_name.split("_position")[0].partition("train1")
            if len(file_epoch_name) > 0:
                file_epoch_name = file_epoch_name[1:]
            df_data = pd.read_csv(
                position_file_path,
                sep="\t",
                names=["position", "timestamps", "x1", "x2"],
            )

            pos_obj = Position(name=f"position during epoch {file_epoch_name[1:]}")

            spatial_series_object = SpatialSeries(
                name="position",
                description="position within the virtual reality wheel",
                data=H5DataIO(df_data.position.values, compression="gzip"),
                reference_frame="unknown",
                unit="cm",
                conversion="0.100",
                timestamps=df_data.timestamps.values,
            )

            pos_obj.add_spatial_series(spatial_series_object)
            behavior_module.add_data_interface(pos_obj)

        # Add lick events
        lick_file_path_list = list(session_path.glob("*licks.txt"))
        for lick_file_path in lick_file_path_list:

            lick_file_name = lick_file_path.name
            file_epoch_name = lick_file_name.split("_licks")[0].partition("train1")[-1]
            if len(file_epoch_name) > 0:
                file_epoch_name = file_epoch_name[1:]

            licks_file_path = lick_file_path_list[0]
            df_data = pd.read_csv(licks_file_path, sep="\t", names=["pos", "time"])

            lick_timestamps = df_data.time.values
            events = Events(
                name=f"licks{file_epoch_name}",
                description="times when the subject licked in seconds",
                timestamps=lick_timestamps,
            )

            behavior_module.add(events)

        # Add reward times
        reward_file_path_list = list(session_path.glob("*reward_times.txt"))
        for reward_file_path in reward_file_path_list:
            reward_file_name = reward_file_path.name
            file_epoch_name = reward_file_name.split("_reward")[0].partition("train1")
            if len(file_epoch_name) > 0:
                file_epoch_name = file_epoch_name[1:]

            df_data = pd.read_csv(
                reward_file_path, sep="\t", names=["reward_time_stamps", "x1"]
            )

            events = Events(
                name=f"reward_times_in_epoch {file_epoch_name[1:]}",
                description="times when subjects received a reward",
                timestamps=df_data.reward_time_stamps.values,
            )
            behavior_module.add(events)

        # Add intervals
        
        
        # Add epochs
        