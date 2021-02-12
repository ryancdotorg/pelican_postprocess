..  This file is part of the pelican_precompress plugin.
..  Copyright 2019-2021 Kurt McKee <contactme@kurtmckee.org>
..  Released under the MIT license.

Changelog
*********

Unreleased changes
==================



1.1.1
=====

*Released 13 July 2020*

*   Fix a bytes/str oversight in the release process.



1.1.0
=====

*Released 13 July 2020*

*   Compress files in parallel on multi-core CPU's.
*   Add a ``PRECOMPRESS_MIN_SIZE`` option to skip files that are too small.
*   Add a ``requirements-dev.txt`` file for easier development and releases.
*   Automate the release process.

**Contributors**

*   `Ryan Castellucci`_



1.0.0
=====

*Released 5 February 2020*

*   Initial release
*   Support brotli, zopfli, and gzip static compression.



..  Contributor links
..  -----------------

..  _Ryan Castellucci: https://github.com/ryancdotorg/
