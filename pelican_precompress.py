# This file is part of the pelican-precompress plugin.
# Copyright 2019-2020 Kurt McKee <contactme@kurtmckee.org>
# Released under the MIT license.

from collections import deque
import functools
import gzip
import logging
import multiprocessing
import os
import pathlib
import shutil
from typing import Dict, Iterable, Optional, Set, Union
import zlib

__version__ = '1.2.0'

log = logging.getLogger(__name__)

# pelican doesn't have to be installed to run tests.
try:
    import pelican
except ModuleNotFoundError:
    log.debug('pelican is not installed.')
    pelican = None

# htmlmin support is optional.
try:
    import htmlmin
except ModuleNotFoundError:
    log.debug('htmlmin is not installed.')
    htmlmin = None

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

DEFAULT_HTML_EXTENSIONS: Set[str] = { '.htm', '.html', }

class FileSizeIncrease(Exception):
    """Indicate that the file size increased after compression."""
    pass


def copystat(src, dst):
    shutil.copystat(src, dst)
    stat = os.stat(src)
    os.chown(dst, stat.st_uid, stat.st_gid)


def get_paths_to_process(settings: Dict[str, pathlib.Path]) -> Iterable[pathlib.Path]:
    extensions = settings['PRECOMPRESS_TEXT_EXTENSIONS'] | settings['HTMLMIN_EXTENSIONS']
    for path in pathlib.Path(settings['OUTPUT_PATH']).rglob('*'):
        if path.suffix in extensions:
            yield path


def get_settings(instance) -> Dict[str, Union[bool, pathlib.Path, Set[str]]]:
    """Extract and validate the Pelican settings."""

    settings = {
        'OUTPUT_PATH': pathlib.Path(instance.settings['OUTPUT_PATH']),

        'PRECOMPRESS_BROTLI': instance.settings.get('PRECOMPRESS_BROTLI', bool(brotli)),
        'PRECOMPRESS_GZIP': instance.settings.get('PRECOMPRESS_GZIP', True),
        'PRECOMPRESS_ZOPFLI': instance.settings.get('PRECOMPRESS_ZOPFLI', bool(zopfli)),
        'PRECOMPRESS_OVERWRITE': instance.settings.get('PRECOMPRESS_OVERWRITE', False),
        'PRECOMPRESS_MIN_SIZE': instance.settings.get('PRECOMPRESS_MIN_SIZE', 20),
        'PRECOMPRESS_TEXT_EXTENSIONS': set(
            instance.settings.get('PRECOMPRESS_TEXT_EXTENSIONS', DEFAULT_TEXT_EXTENSIONS)
        ),

        'HTMLMIN_ENABLED': instance.settings.get('HTMLMIN_ENABLED', False),
        'HTMLMIN_EXTENSIONS': set(
            instance.settings.get('HTMLMIN_EXTENSIONS', DEFAULT_HTML_EXTENSIONS)
        ),
        # Merge the second dict (config file entries) over the first (defaults).
        # https://stackoverflow.com/a/26853961
        'HTMLMIN_OPTIONS': {**{
            # enabling this option tends to result
            # in larger compressed output
            'remove_optional_attribute_quotes': False,
            'pre_tags': ['pre', 'code', 'textarea']
        }, **instance.settings.get('HTMLMIN_OPTIONS', {})},
    }

    # If htmlmin is enabled, it must be installed.
    if settings['HTMLMIN_ENABLED'] and not htmlmin:
        log.error('Disabling HTML minification because htmlmin is not installed.')
        settings['HTMLMIN_ENABLED'] = False

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

    extensions = settings['PRECOMPRESS_TEXT_EXTENSIONS'] | settings['HTMLMIN_EXTENSIONS']

    # '.br' and '.gz' are excluded extensions.
    excluded_extensions = extensions & {'.br', '.gz'}
    if len(excluded_extensions):
        log.warning('Gzip and Brotli file extensions are excluded.')

    # All file extensions must start with a period.
    invalid_extensions = {
        extension
        for extension in extensions
        if not extension.startswith('.')
    }
    if len(invalid_extensions):
        log.warning('File extensions must start with a period.')

    for extension in excluded_extensions | invalid_extensions:
        if extension in settings['HTMLMIN_EXTENSIONS']:
            log.warning(f'Removing "{extension}" from the set of html file extensions to minify.')
            settings['HTMLMIN_EXTENSIONS'].remove(extension)
        if extension in settings['PRECOMPRESS_TEXT_EXTENSIONS']:
            log.warning(f'Removing "{extension}" from the set of text file extensions to pre-compress.')
            settings['PRECOMPRESS_TEXT_EXTENSIONS'].remove(extension)

    return settings


def process_files(instance):
    settings = get_settings(instance)

    # *formats* contains the following information:
    #
    # name (str), file extension (str), compressor (callable), decompressor (callable)
    #
    enabled_formats = []
    if settings['PRECOMPRESS_BROTLI']:
        enabled_formats.append(
            ('brotli', '.br', compress_with_brotli, decompress_with_brotli),
        )
    if settings['PRECOMPRESS_GZIP']:
        enabled_formats.append(
            ('gzip', '.gz', compress_with_gzip, decompress_with_gzip),
        )
    if settings['PRECOMPRESS_ZOPFLI']:
        enabled_formats.append(
            ('zopfli', '.gz', compress_with_zopfli, decompress_with_gzip),
        )

    pending = deque()
    pool = multiprocessing.Pool()
    minimum_size = settings['PRECOMPRESS_MIN_SIZE']
    def run_compressors(data, path):
        if path.suffix in settings['PRECOMPRESS_TEXT_EXTENSIONS']:
            # Ignore files smaller than the minimum size.
            if minimum_size and path.stat().st_size < minimum_size:
                log.info(f'{path} is less than {minimum_size} bytes. Skipping.')
                return

            # run each enabled compressor
            for enabled_format in enabled_formats:
                pool.apply_async(compress_worker, (data, path, enabled_format, settings))

    for path in get_paths_to_process(settings):
        data = path.read_bytes()

        # for files being processed by htmlmin, that needs to finish before
        # the compressors run - the AsyncResult object is saved to the pending
        # queue so that we can check for completion before compressing
        if settings['HTMLMIN_ENABLED'] and path.suffix in settings['HTMLMIN_EXTENSIONS']:
            pending.append(pool.apply_async(htmlmin_worker, (data, path, settings)))
        else:
            run_compressors(data, path)

    while len(pending):
        for result in list(pending):
            # 0.001 is one millisecond - this is somewhat arbitrary and may
            # need to be adjusted. If it's too small, a lot of CPU time will be
            # spent iterating through the pending results. If it's too large,
            # a lot of wall time will be spent idly waiting for htmlmin.
            result.wait(0.001)
            if result.ready():
                pending.remove(result)
                run_compressors(*result.get())

    pool.close()
    pool.join()


def htmlmin_worker(data, path, settings):
    try:
        with open(path, 'wb') as f:
            rawhtml = data.decode('utf-8')
            minhtml = htmlmin.minify(rawhtml, **settings['HTMLMIN_OPTIONS'])
            data = minhtml.encode('utf-8')
            f.seek(0)
            f.write(data)
            f.truncate()
            return (data, path)
    except Exception as e:
        log.exception(f'Minification of {path} failed!')


def compress_worker(data, path, enabled_format, settings):
    name, extension, compressor, decompressor = enabled_format

    destination = path.with_name(path.name + extension)
    if destination.exists():
        # Do not overwrite existing files if forbidden.
        if not settings['PRECOMPRESS_OVERWRITE']:
            log.info(f'{destination} already exists. Skipping.')
            return

        # Don't re-compress if the input hasn't changed.
        destination_data = decompressor(destination)
        if data == destination_data:
            copystat(path, destination)
            log.info(f'{destination} exists with correct data. Skipping.')
            return

        log.warning(f'{destination} exists and will be overwritten.')

        # Prevent existing, non-matching (or corrupt) files from remaining
        # if the file size increases, below.
        destination.unlink()

    try:
        blob = compressor(data)
    except FileSizeIncrease:
        log.info(f'{name} compression caused "{path}" to become larger. Skipping.')
        return
    except Exception as e:
        log.exception(f'Compression of "{path}" with {name} failed!')
        return

    with destination.open('wb') as file:
        file.write(blob)

    copystat(path, destination)


def validate_file_sizes(wrapped):
    """Validate that every compression algorithm produces smaller files."""

    @functools.wraps(wrapped)
    def wrapper(data: bytes) -> bytes:
        blob = wrapped(data)
        if len(blob) >= len(data):
            raise FileSizeIncrease
        return blob

    return wrapper


def decompress_with_brotli(path: pathlib.Path) -> Optional[bytes]:
    """Decompress a file using brotli decompression."""

    try:
        return brotli.decompress(path.read_bytes())
    except brotli.error:
        return None


@validate_file_sizes
def compress_with_brotli(data: bytes) -> bytes:
    """Compress binary data using brotli compression."""

    return brotli.compress(data, mode=brotli.MODE_TEXT, quality=11)


def decompress_with_gzip(path: pathlib.Path) -> Optional[bytes]:
    """Decompress a file using gzip decompression."""

    try:
        return gzip.decompress(path.read_bytes())
    except OSError:
        return None


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
    pelican.signals.finalized.connect(process_files)
