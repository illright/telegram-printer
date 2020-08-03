import os

from cups import Connection


cups = Connection()
printer = os.getenv('PRINTER')
