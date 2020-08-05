import os

from cups import Connection
from cups_notify import Subscriber


cups = Connection()
notifier = Subscriber(cups)

printer = os.getenv('PRINTER')
