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

from source.common.utils import log_with, get_project_root,create_logger
import logging

log = create_logger('utilslogger')

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
    log.info('i saw this foo2 and it was foobar')

@log_with()
def foo2():
    print('this is foo2')


foo()
foo2()
tlog = TestLog()
tlog.foo3()
tlog.foo4()
