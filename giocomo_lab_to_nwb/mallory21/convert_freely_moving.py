
from .processed import (
    convert_freely_moving_with_inertial_sensor,
    convert_freely_moving_without_inertial_sensor
)

convert_freely_moving_without_inertial_sensor(
    '/Volumes/easystore5T/data/Giocomo/nature_comm/src/processed/Freely_moving_data_without_inertial_sensor.mat')

convert_freely_moving_with_inertial_sensor(
    '/Volumes/easystore5T/data/Giocomo/nature_comm/src/processed/Freely_moving_data_with_inertial_sensor.mat')
