import subprocess
from tempfile import NamedTemporaryFile
from typing import List, Tuple

from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def get_inline_keyboard(layout: List[List[Tuple[str, str]]]) -> InlineKeyboardMarkup:
    '''Return an inline keyboard from a layout of buttons
       specified as a tuple of the text and callback data.'''
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(name, callback_data=data) for (name, data) in row]
        for row in layout if row
    ])


# pylint: disable=invalid-name

def s(amount: int, plural_ending: str = 's', singular_ending: str = '') -> str:
    '''Return the plural or singular ending depending on the amount.'''
    if amount == 1:
        return singular_ending
    return plural_ending

# pylint: enable=invalid-name


def convert_to_pdf(file: NamedTemporaryFile, mime: str) -> bool:
    '''Convert a file to PDF if necessary.
       Return whether the conversion took place.'''
    if mime == 'application/pdf':
        return False

    unoconv = subprocess.run(['unoconv', '--stdout', '-f', 'pdf', file.name],
                             text=False,
                             capture_output=True,
                             check=True)
    file.seek(0)
    file.truncate()
    file.write(unoconv.stdout)

    return True
