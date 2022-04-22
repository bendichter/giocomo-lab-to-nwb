from pathlib import Path
from pynwb import NWBFile, TimeSeries
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

    def run_conversion(self, nwbfile: NWBFile, metadata: dict):

        behavior_module = get_module(nwbfile, "behavior")
        session_path = Path(self.source_data["session_path"])
        track_label = next(_ for _ in session_path.name.split("_") if "john" in _)
        no_name_epoch_name = "No name"

        # Add lick events
        file_path_list = list(session_path.glob("*licks.txt"))
        file_path_list = [path for path in file_path_list if track_label in path.name]
        df_data_list = []
        for licks_file_path in file_path_list:

            lick_file_name = licks_file_path.name
            file_epoch_name = lick_file_name.split("_licks")[0].partition("train1")[-1]
            if len(file_epoch_name) > 0:
                file_epoch_name = file_epoch_name[1:]

            df_data = pd.read_csv(licks_file_path, sep="\t", names=["position", "time"])
            df_data_list.append(df_data)

        df_data_concatenated = pd.concat(df_data_list)
        df_data_concatenated.sort_values(by="time", inplace=True)
        lick_timestamps = df_data_concatenated.time.values
        lick_positions = df_data_concatenated.position.values

        position_on_lick_series = TimeSeries(
            name="lick events",
            description="lick events timestamps and their corresponding position",
            data=lick_positions,
            unit="m",
            conversion=0.01,
            timestamps=lick_timestamps,
        )

        behavior_module.add(position_on_lick_series)

        # Add reward times
        file_path_list = list(session_path.glob("*reward_times.txt"))
        file_path_list = [path for path in file_path_list if track_label in path.name]
        df_data_list = []
        for reward_file_path in file_path_list:
            reward_file_name = reward_file_path.name
            file_epoch_name = reward_file_name.split("_reward")[0].partition("train1")
            if len(file_epoch_name) > 0:
                file_epoch_name = file_epoch_name[1:]

            df_data = pd.read_csv(reward_file_path, sep="\t", names=["reward_time_stamps", "x1"])

            df_data_list.append(df_data)

        df_data_concatenated = pd.concat(df_data_list)
        df_data_concatenated.sort_values(by="reward_time_stamps", inplace=True)

        events = Events(
            name=f"reward_times",
            description="timestamps for rewards",
            timestamps=df_data_concatenated.reward_time_stamps.values,
        )
        behavior_module.add(events)

        # Add positions
        file_path_list = list(session_path.glob("*position.txt"))
        file_path_list = [path for path in file_path_list if track_label in path.name]
        df_data_list = []
        for position_file_path in file_path_list:
            position_file_name = position_file_path.name
            file_epoch_name = position_file_name.split("_position")[0].partition("train1")
            if len(file_epoch_name) > 0:
                file_epoch_name = file_epoch_name[-1]

            df_data = pd.read_csv(
                position_file_path,
                sep="\t",
                names=["position", "timestamps", "x1", "x2"],
            )
            df_data["epoch"] = file_epoch_name[1:] if file_epoch_name else no_name_epoch_name
            df_data_list.append(df_data)

        df_data_concatenated = pd.concat(df_data_list)
        df_data_concatenated.sort_values(by="timestamps", inplace=True)
        pos_obj = Position(name=f"position within the virtual reality wheel")

        spatial_series_object = SpatialSeries(
            name="position",
            description="position within the virtual reality wheel",
            data=H5DataIO(df_data_concatenated.position.values, compression="gzip"),
            reference_frame="unknown",
            unit="m",
            conversion=0.01,
            timestamps=df_data_concatenated.timestamps.values,
        )

        pos_obj.add_spatial_series(spatial_series_object)
        behavior_module.add_data_interface(pos_obj)

        # Add epochs from the position file (the one with the highest temporal resolution available)
        df_epochs = df_data_concatenated.groupby("epoch").agg({"timestamps": ["min", "max"]})["timestamps"]
        df_epochs = df_epochs.sort_values(by="min").reset_index()
        df_epochs = df_epochs.rename(columns={"min":"start_time", 'max':"stop_time", "epoch":"epoch_name"})
        rows_as_dicts = df_epochs.T.to_dict().values()
        
        nwbfile.add_epoch_column(name="epoch_name", description="the name of the epoch")
        [nwbfile.add_epoch(**row_dict) for row_dict in rows_as_dicts]

        # Add trial time intervals
        file_path_list = list(session_path.glob("*trial_times.txt"))
        file_path_list = [path for path in file_path_list if track_label in path.name]
        df_data_list = []
        for trial_file_path in file_path_list:
            trial_file_name = trial_file_path.name
            file_epoch_name = trial_file_name.split("_trial")[0].partition("train1")
            if len(file_epoch_name) > 0:
                file_epoch_name = file_epoch_name[-1]

            df_data = pd.read_csv(
                trial_file_path,
                sep="\t",
                names=["stop_time", "x1", "x2", "x3"],
            )
            df_data["epoch"] = file_epoch_name[1:] if file_epoch_name else no_name_epoch_name
            df_data_list.append(df_data)

        
        df_data_concatenated = pd.concat(df_data_list).reset_index()
        df_data_concatenated.sort_values(by="stop_time", inplace=True)
        
        first_trial_time = nwbfile.epochs.start_time[:][1]
        df_data_concatenated["start_time"] = df_data_concatenated.stop_time.shift(1).fillna(first_trial_time)
        rows_as_dicts = df_data_concatenated[["start_time", "stop_time", "epoch"]].T.to_dict().values()
        nwbfile.add_trial_column(name="epoch", description="epoch")
        [nwbfile.add_trial(**row_dict) for row_dict in rows_as_dicts]