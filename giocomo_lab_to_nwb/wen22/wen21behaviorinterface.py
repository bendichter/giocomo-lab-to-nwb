from pathlib import Path
from warnings import warn

import pandas as pd
import numpy as np

from pynwb import NWBFile, TimeSeries
from hdmf.backends.hdf5.h5_utils import H5DataIO
from ndx_events import Events
from pynwb.behavior import Position, SpatialSeries
from nwb_conversion_tools.basedatainterface import BaseDataInterface
from nwb_conversion_tools.utils.types import FolderPathType
from nwb_conversion_tools.tools.nwb_helpers import get_module
from spikeinterface.extractors import SpikeGLXRecordingExtractor


class Wen21EventsInterface(BaseDataInterface):
    def __init__(self, session_path: FolderPathType):
        super().__init__(session_path=session_path)

    def calculate_behavioral_offset_with_nidq_channel(self, df_epochs: pd.DataFrame):
        """Calculates the offset in time between the timestamps in the behavioral files and the niqst files."""

        session_path = Path(self.source_data["session_path"])
        # Calculate shift
        stream_id = "nidq"
        nidq_file_name = f"{session_path.stem.replace('g0', 'g0_t0')}.{stream_id}.bin"
        nidq_file_path = session_path / nidq_file_name

        offset_for_behavioral_time_stamps = 0
        if nidq_file_path.is_file():
            nidq_extractor = SpikeGLXRecordingExtractor(session_path, stream_id=stream_id)
            channel = "nidq#XA2"  # The channel that indicates change in epoch
            recording_nidq = nidq_extractor

            # Get time stamps of changes
            epoch_change_trace = recording_nidq.get_traces(channel_ids=[channel]).ravel()
            times = recording_nidq.get_times()

            # Binarize
            epoch_change_trace_bin = np.zeros(epoch_change_trace.shape, dtype=int)
            epoch_change_trace_bin[epoch_change_trace > (np.max(epoch_change_trace) // 2)] = 1

            epoch_start_idxs = np.where(np.diff(epoch_change_trace_bin) > 0)[0]
            df_epochs["epoch_start_by_niqd"] = times[epoch_start_idxs][: df_epochs.shape[0]]
            df_epochs["behavioral_to_signal_shift"] = df_epochs["start_time"] - df_epochs["epoch_start_by_niqd"]
            offset_for_behavioral_time_stamps = df_epochs["behavioral_to_signal_shift"].mean()
        else:
            warn(f"nidq file not found for session with sessio_path {session_path}")

        return offset_for_behavioral_time_stamps

    def run_conversion(self, nwbfile: NWBFile, metadata: dict):

        behavior_module = get_module(nwbfile, "behavior")
        session_path = Path(self.source_data["session_path"])
        track_label = next(_ for _ in session_path.name.split("_") if "john" in _)
        no_name_epoch_name = "No name"

        # Get positions and epochs to calculate beahavioral shift
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

        df_position_data = pd.concat(df_data_list)
        df_position_data.sort_values(by="timestamps", inplace=True)

        # Obtain epochs the from the position data (the one with the highest temporal resolution available)
        df_epochs = df_position_data.groupby("epoch").agg({"timestamps": ["min", "max"]})["timestamps"]
        df_epochs = df_epochs.sort_values(by="min").reset_index()
        df_epochs = df_epochs.rename(columns={"min": "start_time", "max": "stop_time", "epoch": "epoch_name"})

        # Calculate with the offset with the nidq channel
        offset_for_behavioral_time_stamps = self.calculate_behavioral_offset_with_nidq_channel(df_epochs=df_epochs)

        # Offset the position and epochs which have already been calculated
        df_position_data["timestamps"] -= offset_for_behavioral_time_stamps
        df_epochs["start_time"] -= offset_for_behavioral_time_stamps
        df_epochs["stop_time"] -= offset_for_behavioral_time_stamps

        # Add positions to the nwb_file
        position_data = df_position_data.position.values.astype("float", copy=False)
        position_timestamps = df_position_data.timestamps.values.astype("float", copy=False)
        pos_obj = Position(name=f"position within the virtual reality wheel")
        spatial_series_object = SpatialSeries(
            name="position",
            description="position within the virtual reality wheel",
            data=H5DataIO(position_data, compression="gzip"),
            reference_frame="unknown",
            unit="m",
            conversion=0.01,
            timestamps=position_timestamps,
        )

        # Add epochs to the nwb-file
        pos_obj.add_spatial_series(spatial_series_object)
        behavior_module.add_data_interface(pos_obj)

        df_epochs.drop(columns=["epoch_start_by_niqd", "behavioral_to_signal_shift"], inplace=True)
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
        df_data_concatenated["stop_time"] -= offset_for_behavioral_time_stamps

        first_trial_time = nwbfile.epochs.start_time[:][1]
        df_data_concatenated["start_time"] = df_data_concatenated.stop_time.shift(1).fillna(first_trial_time)
        rows_as_dicts = df_data_concatenated[["start_time", "stop_time", "epoch"]].T.to_dict().values()
        nwbfile.add_trial_column(name="epoch", description="epoch")
        [nwbfile.add_trial(**row_dict) for row_dict in rows_as_dicts]

        # Add lick events
        file_path_list = list(session_path.glob("*licks.txt"))
        file_path_list = [path for path in file_path_list if track_label in path.name]
        df_data_list = []
        for licks_file_path in file_path_list:
            df_data = pd.read_csv(licks_file_path, sep="\t", names=["position", "time"])
            df_data_list.append(df_data)

        df_data_concatenated = pd.concat(df_data_list)
        df_data_concatenated.sort_values(by="time", inplace=True)
        df_data_concatenated["time"] -= offset_for_behavioral_time_stamps

        lick_timestamps = df_data_concatenated.time.values.astype("float", copy=False)
        lick_positions = df_data_concatenated.position.values.astype("float", copy=False)

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
            df_data = pd.read_csv(reward_file_path, sep="\t", names=["reward_time_stamps", "x1"])
            df_data_list.append(df_data)

        df_data_concatenated = pd.concat(df_data_list)
        df_data_concatenated.sort_values(by="reward_time_stamps", inplace=True)
        df_data_concatenated["reward_time_stamps"] -= offset_for_behavioral_time_stamps

        reward_timestamps = df_data_concatenated.reward_time_stamps.values.astype("float", copy=False)
        events = Events(
            name=f"reward_times",
            description="timestamps for rewards",
            timestamps=reward_timestamps,
        )
        behavior_module.add(events)
