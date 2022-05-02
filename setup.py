from setuptools import setup, find_packages

# Get the long description from the README file
with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='giocomo_lab_to_nwb',
    version='0.2.0',
    description='convert Giocomo Neuropixel data into NWB:N format',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Kristin Quick',
    author_email='kristin@scenda.io',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['pynwb',
                      'numpy',
                      'scipy',
                      'hdf5storage',
                      'pytz',
                      'uuid',
                      'tkcalendar',
                      'PyYAML',
                      'nwbn_conversion_tools==0.1.1',
                      'ndx_labmetadata_giocomo',
                      ]
)
