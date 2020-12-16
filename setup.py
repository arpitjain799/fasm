#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017-2020  The SymbiFlow Authors.
#
# Use of this source code is governed by a ISC-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/ISC
#
# SPDX-License-Identifier: ISC

import setuptools
import os
import re
import sys
import subprocess

from distutils.version import LooseVersion
from setuptools import Extension
from setuptools.command.build_ext import build_ext
from Cython.Build import cythonize
import traceback

with open("README.md", "r") as fh:
    long_description = fh.read()


# Based on: https://www.benjack.io/2018/02/02/python-cpp-revisited.html
# GitHub: https://github.com/benjaminjack/python_cpp_example
class CMakeExtension(Extension):
    def __init__(self, name, sourcedir='', prefix=''):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)
        self.prefix = prefix


class CMakeBuild(build_ext):
    def copy_extensions_to_source(self):
        original_extensions = list(self.extensions)
        self.extensions = [
            ext for ext in self.extensions
            if not isinstance(ext, CMakeExtension)
        ]
        super().copy_extensions_to_source()
        self.extensions = original_extensions

    def run(self):
        try:
            super().run()

            try:
                out = subprocess.check_output(['cmake', '--version'])
            except OSError:
                raise RuntimeError(
                    "CMake must be installed to build "
                    "the following extensions: " + ", ".join(
                        e.name for e in self.extensions))

            cmake_version = LooseVersion(
                re.search(r'version\s*([\d.]+)', out.decode()).group(1))
            if cmake_version < '3.7.0':
                raise RuntimeError("CMake >= 3.7.0 is required.")

            for ext in self.extensions:
                self.build_extension(ext)

        except BaseException as e:
            print(
                "Failed to build ANTLR parser, "
                "falling back on slower textX parser. Error:\n", e)
            traceback.print_exc()

    def build_extension(self, ext):
        if isinstance(ext, CMakeExtension):
            extdir = os.path.join(
                os.path.abspath(
                    os.path.dirname(self.get_ext_fullpath(ext.name))),
                ext.prefix)
            cmake_args = [
                '-DCMAKE_INSTALL_PREFIX=' + extdir,
                '-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
                '-DPYTHON_EXECUTABLE=' + sys.executable
            ]

            cfg = 'Debug' if self.debug else 'Release'
            build_args = ['--config', cfg]
            cmake_args += ['-DCMAKE_BUILD_TYPE=' + cfg]
            build_args += ['--', '-j2']

            env = os.environ.copy()
            env['CXXFLAGS'] = '{} -DVERSION_INFO=\\"{}\\"'.format(
                env.get('CXXFLAGS', ''), self.distribution.get_version())
            if not os.path.exists(self.build_temp):
                os.makedirs(self.build_temp)
            os.environ["CXXFLAGS"] = "-fPIC"
            os.environ["CFLAGS"] = "-fPIC"
            subprocess.check_call(
                ['cmake', ext.sourcedir] + cmake_args,
                cwd=self.build_temp,
                env=env)
            subprocess.check_call(
                ['cmake', '--build', '.'] + build_args, cwd=self.build_temp)
            subprocess.check_call(
                ['cmake', '--install', '.'], cwd=self.build_temp)
            subprocess.check_call(['ctest'], cwd=self.build_temp)
            print()  # Add an empty line for cleaner output
        else:
            super().build_extension(ext)


setuptools.setup(
    name="fasm",
    version="0.0.2",
    author="SymbiFlow Authors",
    author_email="symbiflow@lists.librecores.org",
    description="FPGA Assembly (FASM) Parser and Generation library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SymbiFlow/fasm",
    packages=setuptools.find_packages(exclude=('tests*', )),
    install_requires=['textx'],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: ISC License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ['fasm=fasm:main'],
    },
    ext_modules=[
        CMakeExtension('parse_fasm', sourcedir='src', prefix='fasm/parser')
    ] + cythonize("fasm/parser/antlr_to_tuple.pyx"),
    cmdclass={
        'build_ext': CMakeBuild,
    },
)
