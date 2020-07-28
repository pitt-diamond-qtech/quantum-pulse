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

from source.common.utils import log_with, get_project_root
import logging

rootdir = get_project_root()
logfiledir = rootdir / 'logs/'
if not logfiledir.exists():
    os.mkdir(logfiledir)
    print('Creating directory for logging at:'.format(logfiledir.resolve()))

log = logging.getLogger('utilslogger')
log.setLevel(logging.DEBUG)
# create a file handler that logs even debug messages
fh = logging.FileHandler((logfiledir/str('utilslogger'+ '.log')).resolve())
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

@log_with(log)
class TestLog:
    def __init__(self):
        print('creating test log class')
        self.logger = logging.getLogger('utilslogger.testlogcls')

    def foo3(self):
        print('this is foo3')
        self.logger.info('this is foo3')


    def foo4(self):
        print('this is foo4')
#
@log_with(log)
def foo():
    print('this is foo')

@log_with()
def foo2():
    print('this is foo2')


foo()
foo2()
tlog = TestLog()
tlog.foo3()
tlog.foo4()
