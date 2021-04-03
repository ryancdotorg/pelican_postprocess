# This file is part of the pelican-postprocess plugin.
# Copyright 2019-2021 Kurt McKee <contactme@kurtmckee.org>
# Released under the MIT license.

import pathlib
import setuptools

import pelican_postprocess

with pathlib.Path('README.rst').open('r') as file:
    long_description = file.read()

setuptools.setup(
    name='pelican_postprocess',
    version=pelican_postprocess.__version__,
    author='Kurt McKee',
    author_email='contactme@kurtmckee.org',
    description='Pre-compress your Pelican site using gzip, zopfli, and brotli!',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/kurtmckee/pelican_precompress',
    py_modules=['pelican_postprocess'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Pelican :: Plugins',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Internet :: WWW/HTTP :: Site Management',
    ],
    python_requires='~=3.6',
)
