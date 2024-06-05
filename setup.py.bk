#!/usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Setup for EZID

Front end to setuptools, generates installer metadata and provides a convenient way
of setting up EZID locally.

Example usage in a pyenv based development environment:

Setup:
    $ python install --upgrade pip wheel
    $ python setup.py develop
    $ pyenv rehash

* Find available EZID tools by typing `ez-<tab>` on the shell.

Create a wheel install file:
    python install --upgrade pip wheel
    python setup.py bdist_wheel
"""

import os
import pathlib

import setuptools

EZID_META = dict(
    name='ezid',
    version='3.0.0',
    packages=setuptools.find_packages(),
    # include_package_data=True,
    url='https://ezid.cdlib.org/',
    license='http://creativecommons.org/licenses/BSD/',
    author='Regents of the University of California',
    author_email='',
    description='EZID',
    setup_requires=[
        "setuptools_git >= 1.1",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="persistent identifier id",
)

HERE_PATH = pathlib.Path(__file__).parent


def gen_console_scripts():
    """Generate command line stubs for the modules in the tools folders."""
    tool_path = HERE_PATH / 'tools'
    stub_list = []
    for p in tool_path.glob('*.py'):
        if p.name.startswith('_'):
            continue
        module_name = p.with_suffix('').name
        tool_name = 'ez-{}'.format(module_name.replace('_', '-'))
        stub_name = "{}=tools.{}:main".format( tool_name, module_name)
        stub_list.append(stub_name)
    return stub_list


def gen_install_requires():
    """Generate the list of setup dependencies based on the ./requirements.txt file

    We generate install_requires by using the dependencies declared in requirements.txt
    and modifying the versions to "pinned" instead of "compatible with".

    For the differences between `install_requires` and `requirements.txt`, see
    https://packaging.python.org/discussions/install-requires-vs-requirements/.
    """
    req_path = HERE_PATH / 'requirements.txt'
    return [req.replace('~=', '==').strip() for req in req_path.open().readlines()]


# TODO: Adjust as needed and call
def mk_paths():
    """Create directories required by EZID"""
    (HERE_PATH / '../logs').mkdir(parents=True, exist_ok=True)
    (HERE_PATH / '../download/public').mkdir(parents=True, exist_ok=True)
    (HERE_PATH / './db').mkdir(parents=True, exist_ok=True)
    (HERE_PATH / '../logs/transaction.log').touch()


setuptools.setup(
    **EZID_META,
    entry_points={"console_scripts": gen_console_scripts()},
    install_requires=gen_install_requires(),
)
