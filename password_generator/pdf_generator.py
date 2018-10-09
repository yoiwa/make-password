#!/usr/bin/python3
# make-password-sheet: passphrase memorandum generator.
# Written by Yutaka OIWA (AIST).
# (c) 2018 National Institute of Advanced Industrial Science and Technology.
# See LICENSE file copyright detials.

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm, mm, inch
from reportlab.pdfbase import pdfmetrics
#from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import stringWidth

import sys
import math
import re

pt = inch / 72.0

pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
#pdfmetrics.registerFont(TTFont(Font, FontFNAME))
#FontFNAME = '/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc'
#Font = 'NotoSansCJK-Medium'

PwdFont = ('Courier-Bold', 12)
HintFontJ = ('HeiseiKakuGo-W5', 9)
HintFontE = ('Times-Bold', 9)

cardheight = 55 * mm
cardwidth = 91 * mm
cinnermargin = 7 * mm

lmargin = 14 * mm
bmargin = 11 * mm

def prepare_canvas(fname, size):
    if isinstance(fname, str):
        c = canvas.Canvas(fname, pagesize=size)
        return c
    else:
        return fname

def draw_sheet10(c, dat, qr=None):
    width, height = A4
    c = prepare_canvas(c, portrait(A4))
    for xx in range(2):
        for yy in range(5):
            draw_card(c, dat, lmargin + cardwidth * xx, bmargin + cardheight * yy, qr=qr)
    return c

def draw_text_fitted(c, x, y, width, height, font, maxsize, text, *, maxshrink=1.0, centered=False):
    fsize = min(height, maxsize)
    w = stringWidth(text, font, fsize)
    scale = 1.0
    if w > width:
        scale = width / w
        if (scale < maxshrink):
            scale = maxshrink
            fsize = fsize * width / (w * scale)
    #debug print("height={}, maxsize={}, w={} -> scale={}, fsize={}".format(height, maxsize, w, scale, fsize))
    w = stringWidth(text, font, fsize)
    if centered:
        x += (width - w * scale) / 2

    to = c.beginText()
    to.setTextOrigin(x, y)
    to.setFont(font, fsize)
    to.setHorizScale(scale * 100.0)
    to.textOut(text)
    c.drawText(to)

def draw_card(c, dat, x = 0.0, y = 0.0, qr=None):
    c = prepare_canvas(c, (cardwidth, cardheight))
    c.setStrokeColorRGB(0.9, 0.9, 0.9)
    c.rect(x, y, cardwidth, cardheight, fill=0)

    pwd, pwdhints = dat
    lines = len(pwd)
    fullpwd = "".join(pwd)

    allowed_height = cardheight - cinnermargin * 2 - (0.7 * cm) # 35mm
    maxsize = allowed_height / lines / 1.4

    fontsize = min(maxsize, PwdFont[1])

    lineheight = fontsize * 1.4
    starty = y + cinnermargin + lineheight * (len(pwd) - 1)

    twidth = pwidth = cardwidth - cinnermargin * 2
    if (pwdhints):
        pwidth = twidth * 5.0 / 8.0
        hwidth = twidth * 3.0 / 8.0
    if qr:
        pwidth *= 0.7
        hwidth *= 0.7

    draw_text_fitted(c,
                     x + cinnermargin,
                     y + cinnermargin + allowed_height + 0.3 * cm,
                     width = twidth,
                     height = 0.6 * cm,
                     font = PwdFont[0],
                     maxsize = PwdFont[1],
                     text = fullpwd,
                     maxshrink = 0.8,
                     centered = True)

    for l in range(len(pwd)):
        draw_text_fitted(c,
                         x + cinnermargin,
                         starty - lineheight * l,
                         pwidth, lineheight / 1.4,
                         PwdFont[0], PwdFont[1],
                         pwd[l],
                         maxshrink = 0.85)

    hfontsize = min(maxsize, HintFontJ[1])

    if pwdhints:
        for l in range(len(pwdhints)):
            if re.match(r'\A[ -\u00FF]*\Z', pwdhints[l]):
                f = HintFontE
            else:
                f = HintFontJ
            draw_text_fitted(c,
                             x + cinnermargin + pwidth,
                             starty - lineheight * l,
                             hwidth, lineheight / 1.4,
                             f[0], f[1],
                             pwdhints[l],
                             maxshrink = 0.85)

    if qr:
        qwidth = (cardwidth - (cinnermargin * 2 + pwidth + hwidth)) * 0.95
        c.drawImage(qr,
                    x + cardwidth - cinnermargin - qwidth, y + cinnermargin,
                    width = qwidth, height = qwidth)
    return c

def main():
    if __name__ == '__main__':
        import password_generator
    else:
        from . import password_generator

    import argparse

    parser = argparse.ArgumentParser(description='Generate password candidates',
                                     epilog=password_generator.format_helpstr,
                                     add_help=False,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-H', '--hint', action='store_true', help='show pronunciation hint')
    parser.add_argument('-Q', '--qrcode', action='store_true', help='generate QR-code as well')
    parser.add_argument('-o', '--output', help='output file name', required=True)
    parser.add_argument('format', help='password format')
    parser.add_argument('count', help='number of generated passwords', nargs='?', type=int, default=1)
    parser.add_argument('--help', action='help', help='show this help message')

    opts = password_generator.parse_commandline(parser)

    while True:
        l, diag = password_generator.generate(opts.format, opts.count)
        if opts.count == 1:
            l = 1
            break

        for i in range(len(l)):
            print("{:2d}:  {}\n    ({})\n".format(i + 1, *l[i]))

        print("Which one? (1-{}, RET for another set)".format(len(l)))

        l = sys.stdin.readline().strip()

        if l != "":
            break

    n = diag['elements'][int(l) - 1]

    w = []
    h = []

    for dic in n:
        if not dic['separator']:
            w.append(dic['password'])
            h.append(dic['hint'])
        else:
            if w == []:
                w.append("")
            if h == []:
                h.append("")
            w[-1] += dic['password']
            h[-1] += dic['hint']

    if opts.hint:
        print("\nGenerated password: {}\n                   ({})".format("".join(w), "".join(h)))
        dat = (w, h)
    else:
        print("\nGenerated password: {}".format("".join(w)))
        dat = (w, None)

    if opts.qrcode:
        import qrcode
        qr = qrcode.make("".join(w))
        qr = qr.get_image()
        qr = ImageReader(qr)
    else:
        qr = None

    c = draw_sheet10(opts.output, dat, qr=qr)
    c.showPage()
    c.save()

if __name__ == '__main__':
    main()
