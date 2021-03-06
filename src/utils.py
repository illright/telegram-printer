import subprocess
from io import BytesIO
from tempfile import NamedTemporaryFile
from typing import List, Tuple, BinaryIO

from PyPDF4 import PdfFileReader, PdfFileWriter
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from .page_selection import PageSelection


def get_inline_keyboard(layout: List[List[Tuple[str, str]]]) -> InlineKeyboardMarkup:
    '''Return an inline keyboard from a layout of buttons
       specified as a tuple of the text and callback data.'''
    if layout is None:
        return None

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
                             timeout=60,
                             check=True)
    file.seek(0)
    file.write(unoconv.stdout)
    file.truncate()

    return True


def is_portrait(reader: PdfFileReader) -> bool:
    '''Based on the existing PDF reader, determine the orientation of the document.'''
    landscape_pages = 0
    portrait_pages = 0
    for page in reader.pages:
        rotation = page.get('/Rotate')
        width = page.mediaBox.getWidth()
        height = page.mediaBox.getHeight()
        if (width > height) == (rotation in (0, 180, None)):
            landscape_pages += 1
        else:
            portrait_pages += 1

    return portrait_pages > landscape_pages


def apply_page_selection(pdf: BinaryIO, pages: PageSelection):
    '''Exclude the pages from the PDF that weren't selected.'''
    reader = PdfFileReader(pdf)
    writer = PdfFileWriter()

    for page_idx in pages:
        writer.addPage(reader.getPage(page_idx))

    output = BytesIO()
    writer.write(output)
    pdf.seek(0)
    pdf.write(output.getvalue())
    pdf.truncate()
    pdf.seek(0)
