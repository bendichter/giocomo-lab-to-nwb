from setuptools import setup

setup(
    name='giocomo_lab_to_nwb',
    version='0.1dev',
    description='tool to convert giocomo matlab data into NWB:N format',
    author='Kristin Quick',
    author_email='kristin@scenda.io',
    #packages=['giocomo_lab_to_nwb'],
    install_requires=['pynwb',
                      'numpy',
                      'scipy',
                      'hdf5storage',
                      'pytz',
                      'uuid',
                      'tkcalendar',
                      'PyYAML']
)
