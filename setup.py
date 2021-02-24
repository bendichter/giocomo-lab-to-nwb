# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

# Get the long description from the README file
with open('README.md', 'r') as f:
    long_description = f.read()

# Get requirements
with open('requirements.txt') as f:
    install_requires = f.read().strip().split('\n')

setup(
    name='giocomo_lab_to_nwb',
    version='0.2.0',
    description='NWB conversion scripts and tutorials',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Kristin Quick, Luiz Tauffer, Szonja Weigl and Ben Dichter',
    author_email='ben.dichter@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['*.yml', '*.json']},
    install_requires=install_requires
)
