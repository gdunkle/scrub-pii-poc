# coding: utf-8

from setuptools import setup, find_packages
try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError: # for pip <= 9.0.3
    from pip.req import parse_requirements
    
setup(
    name='run-textract',
    version='1.0',
    description='Runs textract on files dropped into the raw document bucket',
    author='AWS Solutions Builders',
    license='ASL',
    zip_safe=False,
    packages=['run_textract'],
    package_dir={'run_textract': '.'},
    include_package_data=False,
    install_requires=[
        'run-textract==1.0'
    ],
    classifiers=[
        'Programming Language :: Python :: 3.8',
    ],
)
