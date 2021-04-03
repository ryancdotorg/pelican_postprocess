..  This file is part of the pelican_postprocess plugin.
..  Copyright 2019-2021 Kurt McKee <contactme@kurtmckee.org>
..  Released under the MIT license.

pelican_postprocess
*******************

**NOTE: This is a fork of Kurt McKee’s pelican_precompress plugin which adds
support for running files through htmlmin prior to compression. The
documentation is not fully updated.**

*Pre-compress your Pelican site using gzip, zopfli, and brotli!*

----

Are you using `Pelican`_, the static site generator? If so, great!
Are you pre-compressing your static files to have the fastest site possible?
If not, install **pelican_postprocess** today!
It's the plugin that makes your visitors happy and saves you money!


Installation
============

There are three steps required to start using static compression:

#.  Install the plugin and any supporting Python packages you want.
#.  Configure Pelican to use the pelican_postprocess plugin.
#.  Configure your web server to use static, pre-compressed files.


1. Install the Python modules
-----------------------------

At minimum, you'll need to install the pelican_postprocess plugin.
It will automatically generate gzip files because gzip is built into the
Python standard library.

However, if you want highly-optimized gzip files you'll need the zopfli module.
And if you want to have the very best compression currently available, you'll
need to install the brotli module (which will require extra work in step 3).

..  code-block:: shell-session

    $ ~~pip install pelican_postprocess~~
    $ pip install zopfli  # This produces smaller gzip'd files. Use it!
    $ pip install brotli  # This requires extra work in step 3.

Further reading: `zopfli`_, `brotli`_


2. Configure Pelican
--------------------

You'll need to import the plugin and add it to the list of active plugins.
Feel free to copy and paste the code below into your Pelican configuration file.
Just uncomment and edit the configuration lines to your liking...or leave
them alone because the defaults are awesome!

..  code-block:: python3

    PLUGINS = [pelican_postprocess]

    # PRECOMPRESS_GZIP = True or False
    # PRECOMPRESS_ZOPFLI = True or False
    # PRECOMPRESS_BROTLI = True or False
    # PRECOMPRESS_OVERWRITE = False
    # PRECOMPRESS_MIN_SIZE = 20
    # PRECOMPRESS_TEXT_EXTENSIONS = {
    #     '.atom',
    #     '.css',
    #     '.html',
    #     '.but-the-default-extensions-are-pretty-comprehensive',
    # }

Further reading: `Pelican plugins`_


3. Configure nginx
------------------

nginx supports gzip compression right out of the box.
To enable it, add something like this to your nginx configuration file:

..  code-block:: nginx

    http {
        gzip_static on;
        gzip_vary on;
    }

At the time of writing, nginx doesn't natively support brotli compression.
To get it, you'll need to compile the static brotli module as an nginx
dynamic module, or recompile nginx from scratch. When it's done you'll
add something like this to your nginx configuration file:

..  code-block:: nginx

    load_module /usr/lib/nginx/modules/ngx_http_brotli_static_module.so;

    http {
        brotli_static on;
    }

Further reading: `gzip_static`_, `gzip_vary`_, `nginx brotli module`_


Configuration
=============

There are a small number of configuration options available.
You set them in your Pelican configuration file.

*   ``PRECOMPRESS_GZIP`` (bool, default is True)

    This is always ``True`` unless you set this to ``False``.
    For example, you might turn this off during development.

*   ``PRECOMPRESS_ZOPFLI`` (bool, default is True if zopfli is installed)

    If the zopfli module is installed this will default to ``True``.
    You might set this to ``False`` during development.
    Note that if you try to enable zopfli compression but the module
    isn't installed then nothing will happen.

*   ``PRECOMPRESS_BROTLI`` (bool, default is True if brotli is installed)

    If the brotli module is installed this will default to ``True``.
    You might set this to ``False`` during development.
    Like ``PRECOMPRESS_ZOPFLI``, if you set this to ``True`` when the
    brotli module isn't installed then nothing will happen.

*   ``PRECOMPRESS_OVERWRITE`` (bool, default is False)

    When pelican_postprocess encounters an existing compressed file
    it will refuse to overwrite it. If you want the plugin to overwrite
    files you can set this to ``True``.

*   ``PRECOMPRESS_TEXT_EXTENSIONS`` (Set[str])

    This setting controls which file extensions will be pre-compressed.

    If you modify this setting in the Pelican configuration file it will
    completely replace the default extensions!

*   ``PRECOMPRESS_MIN_SIZE`` (int, default is 20)

    Small files tend to result in a larger file size when compressed, and any
    improvement is likely to be marginal. The default setting is chosen to
    avoid speculatively compressing files that are likely to result in a
    larger file size after compression.

    To try compressing every file regardless of size, set this to ``0``.


Testing
=======

**pelican_postprocess** has XXX% test coverage. If you'd like to test the
code yourself, clone the git repository and run these commands:

..  code-block:: shell

    $ python3 -m venv venv
    $ source venv/bin/activate
    (venv) $ python -m pip install tox
    (venv) $ tox

The test suite uses tox to setup multiple environments with varying
dependencies using multiple Python interpreters; pytest allows the
test suite to have parametrized tests; pyfakefs creates a fake
filesystem that the tests can run against; and coverage keeps track
of which lines of code (and which branches) have been run.

Further reading: `tox`_, `venv`_, `pytest`_, `pyfakefs`_, `coverage`_


..  Links
..  =====

..  _Pelican: https://getpelican.com/
..  _Pelican plugins: https://docs.getpelican.com/en/latest/plugins.html
..  _zopfli: https://pypi.org/project/zopfli/
..  _brotli: https://pypi.org/project/Brotli/
..  _gzip_static: https://nginx.org/en/docs/http/ngx_http_gzip_static_module.html#gzip_static
..  _gzip_vary: https://nginx.org/en/docs/http/ngx_http_gzip_module.html#gzip_vary
..  _nginx brotli module: https://github.com/google/ngx_brotli
..  _tox: https://tox.readthedocs.io/en/latest/
..  _pytest: https://docs.pytest.org/en/latest/
..  _pyfakefs: https://jmcgeheeiv.github.io/pyfakefs/release/
..  _venv: https://docs.python.org/3/library/venv.html
..  _coverage: https://coverage.readthedocs.io/en/latest/
