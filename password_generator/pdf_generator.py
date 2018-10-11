#!/usr/bin/python3
# make-password-sheet: passphrase memorandum generator.
# Written by Yutaka OIWA (AIST).
# (c) 2018 National Institute of Advanced Industrial Science and Technology.
# See LICENSE file copyright detials.

import math
import sys
import os
import re
import json
import subprocess

from reportlab.pdfgen import canvas
from reportlab.lib import pdfencrypt
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm, mm, inch
from reportlab.pdfbase import pdfmetrics
#from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import stringWidth

pt = inch / 72.0

pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
#pdfmetrics.registerFont(TTFont(Font, FontFNAME))
#FontFNAME = '/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc'
#Font = 'NotoSansCJK-Medium'

PwdFont = ('Courier-Bold', 12)
HintFontJ = ('HeiseiKakuGo-W5', 9)
HintFontE = ('Times-Bold', 9)

DEBUGBOX = False

def draw_text_fitted(c, x, y, width, height, font, maxsize, text, *, maxshrink=1.0, efont=None, centered=False):
    c.setStrokeColorRGB(0.9, 0.9, 0.9)
    if DEBUGBOX: c.rect(x, y, width, height, fill=0)

    fsize = min(height, maxsize)
    if efont and re.match(r'\A[ -\u00FF]*\Z', text):
        font = efont

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
    to.setTextOrigin(x, y + (height - fsize) / 2.0)
    to.setFont(font, fsize)
    to.setHorizScale(scale * 100.0)
    to.textOut(text)
    c.drawText(to)

cardheight = 55 * mm
cardwidth = 91 * mm
cinnermargin = 7 * mm

lmargin = 14 * mm
bmargin = 11 * mm

def prepare_canvas(c_or_fname, size, pdfargs={}):
    if isinstance(c_or_fname, str):
        c = canvas.Canvas(c_or_fname, pagesize=size, **pdfargs)
        return c
    else:
        return c_or_fname

def draw_sheet10(c, dat, pdfargs={}, **kwargs):
    width, height = A4
    c = prepare_canvas(c, portrait(A4), pdfargs)
    for xx in range(2):
        for yy in range(5):
            draw_card(c, dat, lmargin + cardwidth * xx, bmargin + cardheight * yy, **kwargs)
    return c

def draw_card(c, dat, x = 0.0, y = 0.0, qr=None, title=None, hint=False, partpwd=True, pdfargs={}):
    """
    Draw one strip of password reminder to a canvas.
    """

    c = prepare_canvas(c, (cardwidth, cardheight), pdfargs)

    c.setStrokeColorRGB(0.9, 0.9, 0.9)
    c.rect(x, y, cardwidth, cardheight, fill=0)

    pwd, pwdhints = dat
    lines = len(pwd)
    fullpwd = "".join(pwd)

    twidth = cardwidth - cinnermargin * 2
    theight = cardheight - cinnermargin * 2

    if title:
        title_height = fullpwd_height = 0.5 * cm
    else:
        title_height = 0.0
        fullpwd_height = 0.7 * cm

    if partpwd or hint:
        allowed_height = theight - (title_height + fullpwd_height)
    else:
        allowed_height = (theight - (title_height + fullpwd_height - qrwidth)) / 2

    if qr:
        qrwidth = min(twidth * 0.4, allowed_height)
    else:
        qrwidth = 0.0
        
    maxsize = allowed_height / lines / 1.4
    fontsize = min(maxsize, PwdFont[1])

    lineheight = fontsize * 1.4
    starty = y + cinnermargin + allowed_height * 0.5 + lineheight * (len(pwd) - 2) * 0.5

    pwidth = twidth - qrwidth
    if hint:
        if partpwd: hwidth = pwidth * 3.0 / 8.0
        else:       hwidth = pwidth
    else:
        hwidth = 0.0
    pwidth -= hwidth

    if title:
        draw_text_fitted(c,
                         x + cinnermargin,
                         y + cinnermargin + allowed_height + fullpwd_height + title_height * 0.2,
                         width = twidth,
                         height = title_height,
                         font = HintFontJ[0],
                         maxsize = PwdFont[1],
                         text = title,
                         maxshrink = 0.9,
                         efont = HintFontE[0],
                         centered = True)
        
    draw_text_fitted(c,
                     x + cinnermargin,
                     y + cinnermargin + allowed_height + fullpwd_height * 0.2,
                     width = twidth,
                     height = fullpwd_height,
                     font = PwdFont[0],
                     maxsize = PwdFont[1],
                     text = fullpwd,
                     maxshrink = 0.8,
                     centered = True)

    if DEBUGBOX: c.rect(x + cinnermargin, y + cinnermargin, pwidth, allowed_height, fill=0)
    if DEBUGBOX: c.rect(x + cinnermargin, starty, -3 * mm, 0 * mm, fill=0)

    if partpwd:
        for l in range(len(pwd)):
            draw_text_fitted(c,
                             x + cinnermargin,
                             starty - lineheight * l,
                             pwidth - mm, lineheight,
                             PwdFont[0], PwdFont[1],
                             pwd[l],
                             maxshrink = 0.85)

    hfontsize = min(maxsize, HintFontJ[1])

    if hint:
        for l in range(len(pwdhints)):
            draw_text_fitted(c,
                             x + cinnermargin + pwidth,
                             starty - lineheight * l,
                             hwidth - mm, lineheight - (PwdFont[1] - HintFontJ[1]),
                             HintFontJ[0], HintFontJ[1],
                             pwdhints[l],
                             efont = HintFontE[0],
                             maxshrink = 0.85)

    if qr:
        qwidth = qrwidth - 1 * mm
        c.drawImage(qr,
                    x + cardwidth - cinnermargin - qrwidth, y + cinnermargin,
                    width = qrwidth, height = qrwidth)
        if DEBUGBOX:
            c.rect(x + cardwidth - cinnermargin - qrwidth, y + cinnermargin,
                   width = qrwidth, height = qrwidth)
    return c

def generate_textfile(fname, dat, encrypt_to):
    with open(fname, 'w', encoding='utf-8', errors='replace') as f:
        if encrypt_to:
            subprocess.run(['gpg', '-ae', '-r', encrypt_to, '-'],
                           input=dat.encode('utf-8', errors='replace'),
                           stdout=f,
                           check=True)
        else:
            print(dat, end="", file=f)

def wifi_quote(s):
    return re.sub(r'([\\",;:])', r'\\\1', s)

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
    parser.add_argument('--wifi-ssid', help='generate WiFi WPA QRcode')

    outgroup = parser.add_mutually_exclusive_group(required=True)
    outgroup.add_argument('-o', '--output', help='output file name')
    outgroup.add_argument('-O', '--output-base', help='output related data to specified basename or directory')

    parser.add_argument('--gpg-encrypt-to', help='encrypt plaintext output by gpg', metavar='EMAIL')
    parser.add_argument('--encrypt', action='store_true',
                        help=argparse.SUPPRESS #'encrypt PDF output by generated password itself'
    ) # ReportLab bug: encryption with CID font generates buggy PDF.

    parser.add_argument('-L', '--layout', help='card layout (1 or 10)', choices=('1', '10'), default='1')
    parser.add_argument('--title', help='put title line')
    parser.add_argument('--no-partial-passwords', action='store_false', dest='partpwd', help=argparse.SUPPRESS)
    parser.add_argument('--json', action='store_true',help='reuse previous passphrase data in JSON format')
    parser.add_argument('format', help='password format (or JSON filename with --json)')
    parser.add_argument('count', help='number of generated passwords', nargs='?', type=int, default=1)
    parser.add_argument('--help', action='help', help='show this help message')

    opts = password_generator.parse_commandline(parser)

    if opts.json:
        if opts.format == '-':
            json_dat = json.load(sys.stdin)
        else:
            with open(opts.format, 'r', encoding='utf-8') as rf:
                json_dat = json.load(rf)

    else:
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

        json_dat = diag['elements'][int(l) - 1]

    w = []
    h = []

    for dic in json_dat:
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

    password = "".join(w)

    if opts.output_base:
        base, sep, out = opts.output_base.rpartition('/')
        if sep:
            os.makedirs(base, mode=0o700, exist_ok=True)
        output_base = opts.output_base if out != '' else opts.output_base + "password"
        output = output_base + ".pdf"
    else:
        output_base = None
        output = opts.output

    dat = (w, h)
    if opts.hint:
        print("\nGenerated password: {}\n                   ({})".format(password, "".join(h)))
    else:
        print("\nGenerated password: {}".format(password))

    if opts.wifi_ssid and opts.title == None:
        opts.title = opts.wifi_ssid
        
    if opts.qrcode:
        import qrcode
        if opts.wifi_ssid:
            qr_dat = 'WIFI:T:WPA;S:"{}";P:"{}";;'.format(wifi_quote(opts.wifi_ssid), wifi_quote(password))
        else:
            qr_dat = password
        qr = qrcode.make(qr_dat)
        qr = qr.get_image()
        qr = ImageReader(qr)
    else:
        qr = None

    os.umask(os.umask(0o077) | 0o077)

    if opts.encrypt:
        enc = pdfencrypt.StandardEncryption(password + "--usr", password, strength=128)
    else:
        enc = None
    if opts.layout == '10':
        draw = draw_sheet10
    else:
        draw = draw_card
    c = draw(output, dat, hint=opts.hint, partpwd=opts.partpwd, qr=qr, title=opts.title, pdfargs={'encrypt': enc})
    c.showPage()
    c.save()

    if output_base:
        generate_textfile(output_base + ".txt", password, encrypt_to=opts.gpg_encrypt_to)
        generate_textfile(output_base + ".json", json.dumps(json_dat, sort_keys=True, indent=4), encrypt_to=opts.gpg_encrypt_to)

if __name__ == '__main__':
    main()
