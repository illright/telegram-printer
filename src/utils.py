from typing import List, Tuple

from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def get_inline_keyboard(layout: List[List[Tuple[str, str]]]):
    '''Return an inline keyboard from a layout of buttons
       specified as a tuple of the text and callback data.'''
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(name, callback_data=data) for (name, data) in row]
        for row in layout
    ])


# pylint: disable=invalid-name

def s(amount: int, plural_ending: str = 's', singular_ending: str = ''):
    '''Return the plural or singular ending depending on the amount.'''
    if amount == 1:
        return singular_ending
    return plural_ending

# pylint: enable=invalid-name
