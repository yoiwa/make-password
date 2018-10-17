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

from collections import namedtuple
from types import SimpleNamespace
pt = inch / 72.0

pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
#pdfmetrics.registerFont(TTFont(Font, FontFNAME))
#FontFNAME = '/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc'
#Font = 'NotoSansCJK-Medium'

PwdFont = ('Courier-Bold',)
HintFont = ('HeiseiKakuGo-W5', 'Times-Bold')
TitleFont = HintFont

DEBUGBOX = False

__fsize_cache = {}
def font_and_width(s, fonts, size):
    t = (s, fonts, size)
    if t in __fsize_cache:
        return __fsize_cache[t]
    if type(fonts) is str:
        font = fonts
    elif re.match(r'\A[ -\u00FF]*\Z', s):
        font = fonts[-1]
    else:
        font = fonts[0]
    r = (font, stringWidth(s, font, size))
    __fsize_cache[t] = r
    return r

def draw_text_fitted(c, x, y, width, height, fonts, maxsize, text, *, maxshrink=1.0, centered=False):
    c.setStrokeColorRGB(0.9, 0.9, 0.9)
    if DEBUGBOX: c.rect(x, y, width, height, fill=0)

    fsize = min(height, maxsize)

    font, w = font_and_width(text, fonts, fsize)

    scale = 1.0
    if w > width:
        scale = width / w
        if (scale < maxshrink):
            scale = maxshrink
            fsize = fsize * width / (w * scale)
    #debug print("height={}, maxsize={}, w={} -> scale={}, fsize={}".format(height, maxsize, w, scale, fsize))

    font, w = font_and_width(text, fonts, fsize)
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

class CardLayout(namedtuple('CardLayout', '''
                cardwidth cardheight
                hmargin vmargin
                boxsep titlesep hintsep
                topboxheight titlesize pwdsize hintsize
                qrsize align''')):
    pass

#class CardLayout2(namedtuple('CardLayout2', '''
#                titlebase titleheight titleleft titlewidth
#                pwdbase pwdheight pwdleft pwdwidth
#                lines linesbase linesheight
#                elemwidth elemleft hintwidth hintleft
#                qrleft qrbottom
#'''))

def _erange(x):
    if type(x) is tuple: return x
    else: return (x, x)

def layout_lines_y(lines, boxheight, lineheight, linespacing, align='top', starty = 0):
    #print("lines={}, boxheight={}, lineheight={}, linespacing={}, align={}, starty={}".format(lines, boxheight, lineheight, linespacing, align, starty))

    lineskip_min, lineskip_max = _erange(linespacing)
    lineskip_min *= lineheight
    lineskip_max *= lineheight
    vmin0 = lineskip_min * (lines - 1) + lineheight
    vmax0 = lineskip_max * (lines - 1) + lineheight
    content_height = boxheight
    lineheight_r = lineheight
    topmargin = 0.0

    #print(" => v0=({},{}), boxheight={}".format(vmin0, vmax0, boxheight))

    if vmax0 <= boxheight:
        lineskip = lineskip_max
        topmargin = (boxheight - vmax0)
        if align == 'top':
            content_height = vmax0
            topmargin = 0
        elif align == 'center':
            topmargin /= 2
        elif align == 'bottom':
            pass
    elif vmin0 <= boxheight:
        assert (lines >= 2)
        lineskip = (boxheight - lineheight) / (lines - 1)
    else:
        scale = vmin0 / boxheight
        lineheight_r = lineheight / scale
        lineskip = lineskip_min / scale
    lines_y = [starty - topmargin - lineheight_r - lineskip * y
               for y in range(0, lines)]
    #print(" => content_height={}, lineheight={}, topmargin={}, lineskip={}, y={!r}".format(content_height, lineheight_r, topmargin, lineskip, lines_y))
    return (content_height, lineheight_r, lines_y)

def compute_layout(layout, dat, qr, title, hint, partpwd):
    r = SimpleNamespace()

    x_left = layout.hmargin
    x_width = layout.cardwidth - layout.hmargin * 2

    y = layout.cardheight - layout.vmargin

    # topbox
    if title:
        c1, s1, y1 = layout_lines_y(2,
                                    layout.topboxheight[-1],
                                    layout.titlesize, (1.1, 1.4),
                                    align='center', starty=y)
        y -= layout.topboxheight[-1]
        r.titleheight = r.pwdheight = s1
        r.titlebase = y1[0]
        r.pwdbase = y1[1]
    else:
        c1, s1, y1 = layout_lines_y(1,
                                    layout.topboxheight[0],
                                    layout.titlesize, (1.1, 1.4),
                                    align='center', starty=y)
        y -= layout.topboxheight[0]
        r.titleheight = r.titlebase = None
        r.pwdheight = s1
        r.pwdbase = y1[0]
    r.titleleft, r.titlewidth = x_left, x_width
    r.pwdleft, r.pwdwidth = x_left, x_width

    y -= layout.titlesep

    allowed_height = y - layout.vmargin
    allowed_width = x_width

    if qr:
        allowed_width -= layout.qrsize + layout.boxsep
        r.qrleft = x_left + allowed_width + layout.boxsep
    r.lowboxleft = x_left
    r.lowboxwidth = allowed_width

    if hint or partpwd:
        lines = r.lines = len(dat[0])

        c1, s1, y1 = layout_lines_y(lines,
                                    allowed_height,
                                    layout.pwdsize,
                                    align=layout.align,
                                    linespacing=1.4,
                                    starty=y)
        r.linesbase = y1
        r.linesheight = s1
        r.pwdsize = min(s1, layout.pwdsize)
        r.hintsize = min(s1, layout.hintsize)
        pw = hw = 0.0

        for n in range(r.lines):
            pw = max(pw, font_and_width(dat[0][n], PwdFont, r.pwdsize)[1])
            hw = max(hw, font_and_width(dat[1][n], HintFont, r.hintsize)[1])
        #print("pw={}, hw={}".format(pw, hw))
        if hint and partpwd:
            minwidth = pw + hw + layout.hintsep
            maxwidth = pw + hw + layout.hintsep * 3.0
            #print("size = ({},{}), allowed_width={}".format(maxwidth, minwidth, allowed_width))
            if allowed_width >= maxwidth:
                rest = (allowed_width - maxwidth) / 2
                #print("left {}, centering".format(rest * 2))
                r.elemleft = x_left + rest
                r.elemwidth = pw
                r.hintleft = x_left + rest + pw + layout.hintsep * 3.0
                r.hintwidth = hw
            elif allowed_width >= minwidth:
                #print("between, flushing to both side")
                r.elemleft = x_left
                r.elemwidth = pw
                r.hintleft = x_left + (allowed_width - hw)
                r.hintwidth = hw
            else:
                scale = allowed_width / minwidth
                #print("not enough, scaling by {}".format(scale))
                r.elemleft = x_left
                r.elemwidth = pw * scale
                r.hintleft = x_left + (allowed_width - hw * scale)
                r.hintwidth = hw * scale
        else:
            ww = hw if hint else pw
            if ww > allowed_width:
                r.elemleft = r.hintleft = x_left
                r.elemwidth = r.hintwidth = allowed_width
            else:
                r.elemleft = r.hintleft = x_left + (allowed_width - ww) / 2
                r.elemwidth = r.hintwidth = ww
    else: # qr only
        c1 = 0

    lowboxheight = max(c1, layout.qrsize)
    r.lowboxheight = lowboxheight
    r.qrbottom = r.lowboxbottom = y - lowboxheight

    y -= lowboxheight

    return r

def draw_strip(c, dat, layout, x = 0.0, y = 0.0, qr=None, title=None, hint=False, partpwd=True, pdfargs={}):
    """
    Draw one strip of password reminder to a canvas.
    """

    c = prepare_canvas(c, (layout.cardwidth, layout.cardheight), pdfargs)

    c.setStrokeColorRGB(0.9, 0.9, 0.9)
    c.rect(x, y, layout.cardwidth, layout.cardheight, fill=0)

    l2 = compute_layout(layout, dat, qr=qr, title=title, hint=hint, partpwd=partpwd)

    pwd, pwdhints = dat
    lines = len(pwd)
    fullpwd = "".join(pwd)

    if title:
        draw_text_fitted(c,
                         x + l2.titleleft,
                         y + l2.titlebase,
                         width = l2.titlewidth,
                         height = l2.titleheight,
                         fonts = TitleFont,
                         maxsize = layout.titlesize,
                         text = title,
                         maxshrink = 0.9,
                         centered = True)
        
    draw_text_fitted(c,
                     x + l2.pwdleft,
                     y + l2.pwdbase,
                     width = l2.pwdwidth,
                     height = l2.pwdheight,
                     fonts = PwdFont,
                     maxsize = layout.pwdsize,
                     text = fullpwd,
                     maxshrink = 0.8,
                     centered = True)

    if DEBUGBOX: c.rect(x + l2.lowboxleft, y + l2.lowboxbottom, l2.lowboxwidth, l2.lowboxheight, fill=0)
#    if DEBUGBOX: c.rect(x + cinnermargin, starty, -3 * mm, 0 * mm, fill=0)

    if partpwd:
        for n in range(l2.lines):
            draw_text_fitted(c,
                             x + l2.elemleft,
                             y + l2.linesbase[n],
                             l2.elemwidth, l2.linesheight,
                             PwdFont, layout.pwdsize,
                             pwd[n],
                             maxshrink = 0.85)

    if hint:
        for n in range(l2.lines):
            draw_text_fitted(c,
                             x + l2.hintleft,
                             y + l2.linesbase[n],
                             l2.hintwidth, l2.linesheight,
                             HintFont, layout.hintsize,
                             pwdhints[n],
                             maxshrink = 0.85)

    if qr:
        c.drawImage(qr,
                    x + l2.qrleft, y + l2.qrbottom,
                    width = layout.qrsize, height = layout.qrsize)
        if DEBUGBOX:
            c.rect(x + l2.qrleft, y + l2.qrbottom,
                   width = layout.qrsize, height = layout.qrsize)
    return c

BusinessCard = CardLayout(cardwidth = 91 * mm,
                          cardheight = 55 * mm,
                          hmargin = 5 * mm,
                          vmargin = 5 * mm,
                          topboxheight = (7 * mm, 10 * mm),
                          titlesize = 12,
                          pwdsize = 12,
                          hintsize = 9,
                          qrsize = 32 * mm,
                          boxsep = 1 * mm,
                          titlesep = 1 * mm,
                          hintsep = 1 * mm,
                          align = 'center')

def draw_sheet10(c, dat, pdfargs={}, **kwargs):
    width, height = A4
    c = prepare_canvas(c, portrait(A4), pdfargs)
    for xx in range(2):
        for yy in range(5):
            draw_strip(c, dat, BusinessCard, lmargin + BusinessCard.cardwidth * xx, bmargin + BusinessCard.cardheight * yy, **kwargs)
    return c

def draw_card(c, dat, pdfargs={}, **kwargs):
    c = draw_strip(c, dat, BusinessCard, pdfargs=pdfargs, **kwargs)
    return c

def draw_A4sheet(c, dat, pdfargs={}, **kwargs):
    A4sheet = CardLayout(cardwidth = A4[0],
                         cardheight = A4[1],
                         hmargin = 20 * mm,
                         vmargin = 20 * mm,
                         topboxheight = (20 * mm, 30 * mm),
                         titlesize = 16,
                         pwdsize = 14,
                         hintsize = 11,
                         qrsize = 40 * mm,
                         boxsep = 2 * mm,
                         titlesep = 10 * mm,
                         hintsep = 2 * mm,
                         align = 'top')
    c = prepare_canvas(c, portrait(A4), pdfargs)
    draw_strip(c, dat, A4sheet, **kwargs)
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

    parser.add_argument('-L', '--layout', help='card layout (1 or 10)', choices=('1', '10', 'A4'), default='1')
    parser.add_argument('--title', help='put title line')
    parser.add_argument('--no-partial-passwords', action='store_false', dest='partpwd', help=argparse.SUPPRESS)
    parser.add_argument('--json', action='store_true',help='reuse previous passphrase data in JSON format')
    parser.add_argument('format', help='password format (or JSON filename with --json)')
    parser.add_argument('count', help='number of generated passwords', nargs='?', type=int, default=1)
    parser.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--help', action='help', help='show this help message')

    opts = password_generator.parse_commandline(parser)
    global DEBUGBOX
    if opts.debug:
        DEBUGBOX = True

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
    elif opts.layout == 'A4':
        draw = draw_A4sheet
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
