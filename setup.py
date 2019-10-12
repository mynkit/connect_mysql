# -*- coding: utf-8 -*-

from setuptools import find_packages, setup


def _requires_from_file(filename):
    return open(filename).read().splitlines()


setup(
    name="connect_mysql",
    version="0.0.2",
    python_requires=">=3.5",
    packages=find_packages(),
    install_requires=_requires_from_file('requirements.txt'),
    url="https://github.com/mynkit/connect_mysql",
)