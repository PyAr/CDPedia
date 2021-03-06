#!/usr/bin/env python3

# Copyright 2006-2020 CDPedistas (see AUTHORS.txt)
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For further info, check  https://github.com/PyAr/CDPedia/

import optparse
import os
import platform
import sys
import threading
import traceback
import webbrowser
import logging


# set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s  %(name)-20s %(levelname)-8s %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


# change execution path, so we can access all cdpedia internals (code and libraries); note this
# is needed for when CDPedia is executed from a different location (e.g.: double click from GUI)
cdpedia_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(cdpedia_path)

# fix path to be able to access the "included external libraries"
sys.path.append(os.path.join(cdpedia_path, "extlib"))

# imports after path was fixed
import config  # NOQA
from src.armado import to3dirs  # NOQA
from src.utiles import WatchDog, find_open_port, set_locale  # NOQA
from src.web.web_app import create_app  # NOQA
from werkzeug.serving import ThreadedWSGIServer  # NOQA


# We log stdout and stderr if it is the Windows platform,
# except it is a debug build to compile the .exe file.
if platform.system() == 'Windows' and not os.path.exists('debug'):
    log_filename = os.path.join(os.path.expanduser('~'), 'cdpedia.log')
    try:
        log = open(log_filename, 'wt', encoding='utf8', errors='replace')
        sys.stdout = log
        sys.stderr = log
    except Exception:     # If we can't log or show the error because we
        pass    # don't have a terminal we can't do anything.


def handle_crash(type, value, tb):
    """Handle any exception that is not addressed explicitly."""
    if issubclass(type, KeyboardInterrupt):
        # We leave!
        logger.info("Closed by user request.")
        cd_wd_timer.cancel()
        sys.exit(0)
    else:
        exception = traceback.format_exception(type, value, tb)
        exception = "".join(exception)
        logger.info(exception)


def close():
    """Shutdown the server."""
    logger.info("Exiting by watchdog timer")
    server.shutdown()
    sys.exit(0)


def cd_watch_dog():
    """Check that the CD is inserted."""
    global cd_wd_timer

    try:
        files = os.listdir('.')
    except OSError:
        # The CD is not available.
        close()

    if 'cdpedia.py' not in files:
        # The CD is not CDPedia.
        close()

    # It's working, let's try later.
    cd_wd_timer = threading.Timer(CD_WD_SECONDS, cd_watch_dog)
    cd_wd_timer.daemon = True
    cd_wd_timer.start()


def sleep_and_browse():
    server_up.wait()
    if config.EDICION_ESPECIAL is None:
        index = "http://%s:%d/" % (config.HOSTNAME, config.PORT)
    else:
        index = "http://%s:%d/%s/%s" % (config.HOSTNAME, config.PORT,
                                        config.EDICION_ESPECIAL, config.INDEX)
    if not webbrowser.open(index):
        logger.info("You need a browser installed in your system to access the CDPedia content.")
        server.shutdown()
        sys.exit(-1)


if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-v", "--verbose", action="store_true", default=False,
                      dest="verbose", help="shows information about what is done")
    parser.add_option("-d", "--daemon", action="store_true", default=False,
                      dest="daemon", help="daemonize server")
    parser.add_option("-p", "--port", type="int", dest="port",
                      default=config.PORT)
    parser.add_option("-m", "--host", type="str", dest="hostname",
                      default=config.HOSTNAME)
    (options, args) = parser.parse_args()

    set_locale()

    sys.excepthook = handle_crash

    if options.daemon:
        port = options.port
    else:
        port = find_open_port(starting_from=options.port, host=options.hostname)

    # init some config vars and other internal structures
    config.PORT, config.HOSTNAME = port, options.hostname
    to3dirs.namespaces.load(config.NAMESPACES_PREFIXES_DIR)

    if not options.daemon:
        server_up = threading.Event()

        # CD WatchDog timer
        cd_wd_timer = None

        # Time between calls to cd_watch_dog in seconds.
        CD_WD_SECONDS = 10

        cd_wd_timer = threading.Timer(CD_WD_SECONDS, cd_watch_dog)
        cd_wd_timer.daemon = True
        cd_wd_timer.start()

        threading.Thread(target=sleep_and_browse).start()

        browser_watchdog = None
        if config.BROWSER_WD_SECONDS:
            browser_watchdog = WatchDog(callback=close, sleep=config.BROWSER_WD_SECONDS)
            # We start the watchdog even if the browser is not yet up since
            # the watchdog time is much longer than the time it takes to raise
            # the server and the browser.
            browser_watchdog.start()

        if options.verbose:
            logger.info("Raising the server...")

        app = create_app(browser_watchdog, verbose=options.verbose)

        server = ThreadedWSGIServer(config.HOSTNAME, config.PORT, app, handler=None,
                                    passthrough_errors=False)
        server_up.set()
        server.serve_forever()

        if options.verbose:
            logger.info("Finished.")
        cd_wd_timer.cancel()

    else:
        app = create_app(watchdog=None, verbose=options.verbose)
        server = ThreadedWSGIServer(config.HOSTNAME, port, app, handler=None,
                                    passthrough_errors=False)
        server.serve_forever()
