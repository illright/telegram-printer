import subprocess

from src.cups_server import notifier
from src.main import updater


unoconv_listener = subprocess.Popen(['unoconv', '--listener'])

updater.start_polling()
updater.idle()

notifier.unsubscribe_all()
