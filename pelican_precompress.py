# This file is part of the pelican-precompress plugin.
# Copyright 2019-2020 Kurt McKee <contactme@kurtmckee.org>
# Released under the MIT license.

import functools
import logging
import pathlib
from typing import Dict, Iterable, Set, Union
import zlib

__version__ = '1.0.0'

log = logging.getLogger(__name__)

# pelican doesn't have to be installed to run tests.
try:
    import pelican
except ModuleNotFoundError:
    log.debug('pelican is not installed.')
    pelican = None

# brotli support is optional.
try:
    import brotli
except ModuleNotFoundError:
    log.debug('brotli is not installed.')
    brotli = None

# zopfli support is optional.
try:
    import zopfli.gzip
except ModuleNotFoundError:
    log.debug('zopfli is not installed.')
    log.debug('Note: pelican_precompress only targets zopfli, not zopflipy.')
    zopfli = None


DEFAULT_TEXT_EXTENSIONS: Set[str] = {
    '.atom',
    '.css',
    '.htm',
    '.html',
    '.ini',
    '.js',
    '.json',
    '.py',
    '.rss',
    '.txt',
    '.xml',
    '.xsl',
}


class FileSizeIncrease(Exception):
    """Indicate that the file size increased after compression."""
    pass


def get_paths_to_compress(settings: Dict[str, pathlib.Path]) -> Iterable[pathlib.Path]:
    for path in pathlib.Path(settings['OUTPUT_PATH']).rglob('*'):
        if path.suffix in settings['PRECOMPRESS_TEXT_EXTENSIONS']:
            yield path


def get_settings(instance) -> Dict[str, Union[bool, pathlib.Path, Set[str]]]:
    """Extract and validate the Pelican settings."""

    settings = {
        'OUTPUT_PATH': pathlib.Path(instance.settings['OUTPUT_PATH']),
        'PRECOMPRESS_BROTLI': instance.settings.get('PRECOMPRESS_BROTLI', bool(brotli)),
        'PRECOMPRESS_GZIP': instance.settings.get('PRECOMPRESS_GZIP', True),
        'PRECOMPRESS_ZOPFLI': instance.settings.get('PRECOMPRESS_ZOPFLI', bool(zopfli)),
        'PRECOMPRESS_OVERWRITE': instance.settings.get('PRECOMPRESS_OVERWRITE', False),
        'PRECOMPRESS_TEXT_EXTENSIONS': set(
            instance.settings.get('PRECOMPRESS_TEXT_EXTENSIONS', DEFAULT_TEXT_EXTENSIONS)
        ),
    }

    # If brotli is enabled, it must be installed.
    if settings['PRECOMPRESS_BROTLI'] and not brotli:
        log.error('Disabling brotli pre-compression because it is not installed.')
        settings['PRECOMPRESS_BROTLI'] = False

    # If zopfli is enabled, it must be installed.
    if settings['PRECOMPRESS_ZOPFLI'] and not zopfli:
        log.error('Disabling zopfli pre-compression because it is not installed.')
        settings['PRECOMPRESS_ZOPFLI'] = False

    # If zopfli is enabled, disable gzip because it is redundant.
    if settings['PRECOMPRESS_ZOPFLI']:
        settings['PRECOMPRESS_GZIP'] = False

    # '.br' and '.gz' are excluded extensions.
    excluded_extensions = {
        extension
        for extension in {'.br', '.gz'}
        if extension in settings['PRECOMPRESS_TEXT_EXTENSIONS']
    }
    for count, extension in enumerate(excluded_extensions, 1):
        if count == 1:
            log.warning('gzip and brotli file extensions are excluded.')
        log.warning(f'Removing "{extension}" from the set of text file extensions to pre-compress.')
        settings['PRECOMPRESS_TEXT_EXTENSIONS'].remove(extension)

    # All file extensions must start with a period.
    invalid_extensions = {
        extension
        for extension in settings['PRECOMPRESS_TEXT_EXTENSIONS']
        if not extension.startswith('.')
    }
    for count, extension in enumerate(invalid_extensions, 1):
        if count == 1:
            log.warning('File extensions must start with a period.')
        log.warning(f'Removing "{extension}" from the set of text file extensions to pre-compress.')
        settings['PRECOMPRESS_TEXT_EXTENSIONS'].remove(extension)

    return settings


def compress_files(instance):
    settings = get_settings(instance)

    compressors = (
        # name (str), function (callable), enabled (bool), file extension (str)
        ('brotli', compress_with_brotli, settings['PRECOMPRESS_BROTLI'], '.br'),
        ('gzip', compress_with_gzip, settings['PRECOMPRESS_GZIP'], '.gz'),
        ('zopfli', compress_with_zopfli, settings['PRECOMPRESS_ZOPFLI'], '.gz'),
    )

    for path in get_paths_to_compress(settings):
        with path.open('rb') as file:
            data = file.read()

        for name, compress, enabled, extension in compressors:
            if not enabled:
                continue

            # Do not overwrite existing files.
            destination = path.with_name(path.name + extension)
            if destination.exists():
                if not settings['PRECOMPRESS_OVERWRITE']:
                    log.info(f'{destination} already exists. Skipping.')
                    continue
                log.warning(f'{destination} exists and will be overwritten.')

            try:
                blob = compress(data)
            except FileSizeIncrease:
                log.info(f'{name} compression caused "{path}" to become larger. Skipping.')
                continue

            with destination.open('wb') as file:
                file.write(blob)


def validate_file_sizes(wrapped):
    """Validate that every compression algorithm produces smaller files."""

    @functools.wraps(wrapped)
    def wrapper(data: bytes) -> bytes:
        blob = wrapped(data)
        if len(blob) >= len(data):
            raise FileSizeIncrease
        return blob

    return wrapper


@validate_file_sizes
def compress_with_brotli(data: bytes) -> bytes:
    """Compress binary data using brotli compression."""

    return brotli.compress(data, mode=brotli.MODE_TEXT, quality=11)


@validate_file_sizes
def compress_with_gzip(data: bytes) -> bytes:
    """Compress binary data using gzip compression."""

    compressor = zlib.compressobj(level=9, wbits=16 + zlib.MAX_WBITS)
    return compressor.compress(data) + compressor.flush()


@validate_file_sizes
def compress_with_zopfli(data: bytes) -> bytes:
    """Compress binary data using zopfli compression."""

    return zopfli.gzip.compress(data)


def register():
    # Wait until all of the files are written.
    pelican.signals.finalized.connect(compress_files)
