import h5py

year = '19'


def get_data(file: h5py.File, str_: str, row=0):
    return file[file['cell_info'][str_][row][0]][:].ravel()


def get_str(file: h5py.File, str_: str, row=0) -> str:
    return ''.join([chr(x) for x in file[file['cell_info'][str_][row][0]]])


def get_track_session_info(fpath: str):
    file = h5py.File(fpath, 'r')
    return get_str(file, 'animal_id'), get_str(file, 'session_id')
