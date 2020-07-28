# Created by Gurudev Dutt <gdutt@pitt.edu> on 3/6/20
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# this code is adapted from https://wiki.python.org/moin/PythonDecoratorLibrary#Logging_decorator_with_specified_logger_
# .28or_default.29

import functools, logging
from .utils import get_project_root

rootdir = get_project_root()
logfiledir = rootdir / 'logs/'

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
# create a file handler that logs even debug messages
fh = logging.FileHandler(logfiledir/str(__name__ + '.log'))
fh.setLevel(logging.DEBUG)
# create a console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
log.addHandler(fh)
log.addHandler(ch)

class log_with(object):
    '''Logging decorator that allows you to log with a specific logger.
    '''
    # Customize these messages
    ENTRY_MESSAGE = 'Entering {}'
    EXIT_MESSAGE = 'Exiting {}'

    def __init__(self, logger=None):
        self.logger = logger

    def __call__(self, func):
        '''Returns a wrapper that wraps func. The wrapper will log the entry and exit points of the function
        with logging.INFO level.
        '''
        # set logger if it was not set earlier
        if not self.logger:
            logging.basicConfig()
            self.logger = logging.getLogger(func.__module__)
            self.logger.setLevel(logging.DEBUG)
            # create a file handler that logs even debug messages
            fh = logging.FileHandler(logfiledir / str(__name__ + '.log')
            fh.setLevel(logging.DEBUG)
            # create a console handler with a higher log level
            ch = logging.StreamHandler()
            ch.setLevel(logging.ERROR)
            # create formatter and add it to the handlers
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            # add the handlers to the logger
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

        @functools.wraps(func)
        def wrapper(*args, **kwds):
            self.logger.info(self.ENTRY_MESSAGE.format(func.__name__))  # logging level .info(). Set to .debug() if you want to
            f_result = func(*args, **kwds)
            self.logger.info(self.EXIT_MESSAGE.format(func.__name__))   # logging level .info(). Set to .debug() if you want to
            return f_result
        return wrapper