#!/usr/bin/env python3

from setuptools import find_packages, setup

tests_require = ['pytest']
docs_require = ['sphinx', 'sphinx-autodoc-typehints']

setup(
    name='opensp4000',
    packages=find_packages(),
    description='',
    license='BSD',
    platforms=['OS Independent'],
    keywords='',
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3'
    ],
    tests_require=tests_require,
    install_requires=[],
    setup_requires=[],
    scripts=['scripts/hddtemp_to_prom.py'],
    extras_require={
        'test': tests_require,
        'doc': docs_require
    },
    python_requires='>=3.5'
)
