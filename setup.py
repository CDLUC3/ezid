#!/usr/bin/env python

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
#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import os
import pathlib

import setuptools

EZID_META = dict(
    name='ezid',
    version='3.0.0',
    # packages=setuptools.find_packages(),
    # include_package_data=True,
    packages=[
        'settings',
        'ezidapp',
        'impl',
        'ui_tags',
        'tests',
        'tools',
        'ezidapp.management',
        'ezidapp.models',
        'ezidapp.management.commands',
        'impl.nog',
        'ui_tags.templatetags',
        'tests.util',
    ],
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
    return [
        "ez-{}=tools.{}:main".format(
            os.path.split(n)[1].replace("_", "-").replace(".py", ""),
            n.replace(".py", ""),
        )
        for n in os.listdir(tool_path)
        if n.endswith(".py") and not n.startswith("_")
    ]


def gen_install_requires():
    """Generate the list of setup dependencies based on the ./requirements.txt file

    We generate install_requires by using the dependencies declared in requirements.txt
    and modifying the versions to "pinned" instead of "compatible with".

    For the differences between `install_requires` and `requirements.txt`, see
    https://packaging.python.org/discussions/install-requires-vs-requirements/.
    """
    req_path = HERE_PATH / 'requirements.txt'
    return [req.replace('~=', '==').strip() for req in req_path.open().readlines()]


setuptools.setup(
    **EZID_META,
    entry_points={"console_scripts": gen_console_scripts()},
    install_requires=gen_install_requires(),
)
