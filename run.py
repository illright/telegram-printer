import subprocess

from src.main import updater


unoconv_listener = subprocess.Popen(['unoconv', '--listener'])

updater.start_polling()
updater.idle()
