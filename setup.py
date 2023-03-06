#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os

from setuptools import find_packages, setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding="utf-8").read()


setup(
    name="pytest-tally",
    version="0.1.0",
    author="Jeff Wright",
    author_email="jeff.washcloth@gmail.com",
    license="MIT",
    url="https://github.com/jeffwright13/pytest-tally",
    description="A Pytest plugin to generate realtime summary stats, and display them in-console using a text-based dashboard.",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    py_modules=["pytest_tally"],
    python_requires=">=3.8",
    # install_requires=[
    # ],
    setup_requires=["setuptools_scm"],
    include_package_data=True,
    classifiers=[
        "Framework :: Pytest",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="pytest pytest-plugin testing tui textual html",
    entry_points={
        "pytest11": ["pytest_tally = pytest_tally.plugin"],
        "console_scripts": [
            "tally-rich = pytest_tally.clients.rich_dashboard:main",
        ],
    },
)
