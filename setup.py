"""Setup configuration for zuspec-be-hdlsim."""
from setuptools import setup, find_namespace_packages

setup(
    name='zuspec-be-hdlsim',
    version='0.1.0',
    description='Zuspec HDL simulation backend',
    packages=find_namespace_packages(where='src'),
    package_dir={'': 'src'},
    python_requires='>=3.9',
    install_requires=[
        'zuspec-dataclasses',
    ],
)
