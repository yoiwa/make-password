#!/usr/bin/python3
# make-password-sheet: passphrase memorandum generator.
# Written by Yutaka OIWA (AIST).
# (c) 2018 National Institute of Advanced Industrial Science and Technology.
# See LICENSE file copyright detials.
# [AIST program registration #H30PRO-2263]

import math
import sys
import os
import re
import json
import subprocess

if __name__ == '__main__':
    import password_generator
else:
    from . import password_generator

VERSION = password_generator.VERSION + ""
FULL_VERSION = os.path.basename(sys.argv[0]) + " " + VERSION

from reportlab.pdfgen import canvas
from reportlab.lib import pdfencrypt
from reportlab.lib.pagesizes import A4, letter, portrait
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

class BadDataError(ValueError):
    pass

# utility routine

def prepare_canvas(c_or_fname, size, pdfargs={}):
    if isinstance(c_or_fname, canvas.Canvas):
        return c_or_fname
    else:
        c = canvas.Canvas(c_or_fname, pagesize=size, **pdfargs)
        return c

# text management routines

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

# Layout

class CardLayout(namedtuple('CardLayout', '''
                description width height
                hmargin vmargin
                boxsep titlesep hintsep
                topboxheight topboxspacing
                titlesize pwdsize hintsize
                elemspacing
                qrsize align''')):

  __slots__ = ()

  def _compute_layout(self, dat, qr, title, hint, pwdelems):
      #class ComputedLayout(namedtuple('ComputedLayout', '''
      #                titlebase titleheight titleleft titlewidth
      #                pwdbase pwdheight pwdleft pwdwidth
      #                lines linesbase linesheight
      #                elemwidth elemleft hintwidth hintleft
      #                qrleft qrbottom
      #'''))

    r = SimpleNamespace()

    x_left = self.hmargin
    x_width = self.width - self.hmargin * 2

    y = self.height - self.vmargin

    # topbox
    if title:
        c1, s1, y1 = layout_lines_y(2,
                                    self.topboxheight[-1],
                                    self.titlesize, self.topboxspacing,
                                    align='center', starty=y)
        y -= self.topboxheight[-1]
        r.titleheight = r.pwdheight = s1
        r.titlebase = y1[0]
        r.pwdbase = y1[1]
    else:
        c1, s1, y1 = layout_lines_y(1,
                                    self.topboxheight[0],
                                    self.titlesize, self.topboxspacing,
                                    align='center', starty=y)
        y -= self.topboxheight[0]
        r.titleheight = r.titlebase = None
        r.pwdheight = s1
        r.pwdbase = y1[0]
    r.titleleft, r.titlewidth = x_left, x_width
    r.pwdleft, r.pwdwidth = x_left, x_width

    y -= self.titlesep

    allowed_height = y - self.vmargin
    allowed_width = x_width

    if qr:
        allowed_width -= self.qrsize + self.boxsep
        r.qrleft = x_left + allowed_width + self.boxsep
    r.lowboxleft = x_left
    r.lowboxwidth = allowed_width

    if hint or pwdelems:
        lines = r.lines = len(dat[0])

        c1, s1, y1 = layout_lines_y(lines,
                                    allowed_height,
                                    self.pwdsize,
                                    align=self.align,
                                    linespacing=self.elemspacing,
                                    starty=y)
        r.linesbase = y1
        r.linesheight = s1
        r.pwdsize = min(s1, self.pwdsize)
        r.hintsize = min(s1, self.hintsize)
        pw = hw = 0.0

        for n in range(r.lines):
            pw = max(pw, font_and_width(dat[0][n], PwdFont, r.pwdsize)[1])
            hw = max(hw, font_and_width(dat[1][n], HintFont, r.hintsize)[1])
        #print("pw={}, hw={}".format(pw, hw))
        if hint and pwdelems:
            minwidth = pw + hw + self.hintsep
            maxwidth = pw + hw + self.hintsep * 3.0
            #print("size = ({},{}), allowed_width={}".format(maxwidth, minwidth, allowed_width))
            if allowed_width >= maxwidth:
                rest = (allowed_width - maxwidth) / 2
                #print("left {}, centering".format(rest * 2))
                r.elemleft = x_left + rest
                r.elemwidth = pw
                r.hintleft = x_left + rest + pw + self.hintsep * 3.0
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

    lowboxheight = max(c1, self.qrsize)
    r.lowboxheight = lowboxheight
    r.qrbottom = r.lowboxbottom = y - lowboxheight

    y -= lowboxheight

    return r

  def draw(self, c, dat, x = 0.0, y = 0.0, qr=None, title=None, hint=False, pwdelems=True, pdfargs={}):
    """
    Draw one strip of password reminder to a canvas.
    """

    c = prepare_canvas(c, (self.width, self.height), pdfargs)

    c.setStrokeColorRGB(0.9, 0.9, 0.9)
    c.rect(x, y, self.width, self.height, fill=0)

    l2 = self._compute_layout(dat, qr=qr, title=title, hint=hint, pwdelems=pwdelems)

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
                         maxsize = self.titlesize,
                         text = title,
                         maxshrink = 0.9,
                         centered = True)
        
    draw_text_fitted(c,
                     x + l2.pwdleft,
                     y + l2.pwdbase,
                     width = l2.pwdwidth,
                     height = l2.pwdheight,
                     fonts = PwdFont,
                     maxsize = self.pwdsize,
                     text = fullpwd,
                     maxshrink = 0.8,
                     centered = True)

    if DEBUGBOX: c.rect(x + l2.lowboxleft, y + l2.lowboxbottom, l2.lowboxwidth, l2.lowboxheight, fill=0)
#    if DEBUGBOX: c.rect(x + cinnermargin, starty, -3 * mm, 0 * mm, fill=0)

    if pwdelems:
        for n in range(l2.lines):
            draw_text_fitted(c,
                             x + l2.elemleft,
                             y + l2.linesbase[n],
                             l2.elemwidth, l2.linesheight,
                             PwdFont, self.pwdsize,
                             pwd[n],
                             maxshrink = 0.85)

    if hint:
        for n in range(l2.lines):
            draw_text_fitted(c,
                             x + l2.hintleft,
                             y + l2.linesbase[n],
                             l2.hintwidth, l2.linesheight,
                             HintFont, self.hintsize,
                             pwdhints[n],
                             maxshrink = 0.85)

    if qr:
        c.drawImage(qr,
                    x + l2.qrleft, y + l2.qrbottom,
                    width = self.qrsize, height = self.qrsize)
        if DEBUGBOX:
            c.rect(x + l2.qrleft, y + l2.qrbottom,
                   width = self.qrsize, height = self.qrsize)
    return c

class MultiCardLayout(namedtuple('MultiCardLayout', '''
                description width height
                layout xcount ycount
                leftmargin xseparate
                topmargin yseparate''')):
    __slots__ = ()

    def draw(self, c, dat, x = 0.0, y = 0.0, pdfargs={}, **kwargs):
        c = prepare_canvas(c, (self.width, self.height), pdfargs)

        cw, ch = self.layout.width, self.layout.height

        if self.leftmargin == None:
            leftmargin = (self.width
                          - self.xcount * cw
                          - (self.xcount - 1) * self.xseparate) / 2
        else:
            leftmargin = self.leftmargin

        if self.topmargin == None:
            bottommargin = (self.height
                            - self.ycount * ch
                            - (self.ycount - 1) * self.yseparate) / 2
        else:
            bottommargin = (self.height
                            - self.ycount * ch
                            - (self.ycount - 1) * self.yseparate
                            - self.topmargin)

        c = prepare_canvas(c, (self.width, self.height), pdfargs)

        ww = cw + self.xseparate
        hh = ch + self.yseparate
        for xx in range(self.xcount):
            for yy in range(self.ycount):
                self.layout.draw(c, dat,
                                 x = x + leftmargin + ww * xx,
                                 y = y + bottommargin + hh * yy,
                                 **kwargs)

        return c

MultiCardLayout.__new__.__defaults__ = (None, 0.0, None, 0.0)
# default parameter of namedtuple() is available after Python 3.7.

# Layout Instances

BusinessCard = CardLayout("Business card",
                          width = 91 * mm,
                          height = 55 * mm,
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
                          topboxspacing = (1.1, 1.4),
                          elemspacing = (1.4, 1.5),
                          align = 'center')

A4sheet     = CardLayout("A4 paper",
                         width = A4[0],
                         height = A4[1],
                         hmargin = 20 * mm,
                         vmargin = 20 * mm,
                         topboxheight = (20 * mm, 30 * mm),
                         topboxspacing = 2.0,
                         titlesize = 20,
                         pwdsize = 14,
                         hintsize = 11,
                         qrsize = 40 * mm,
                         boxsep = 2 * mm,
                         titlesep = 10 * mm,
                         hintsep = 2 * mm,
                         elemspacing = (1.4, 1.6),
                         align = 'top')

A5card = A4sheet._replace(description="A5 paper",
                          height = A4[1] / 2,
                          vmargin = 10 * mm,
                          topboxheight = (20 * mm, 25 * mm))

Lettercard = A4sheet._replace(description="US-Letter paper",
                          width = letter[0],
                          height = letter[1])

Sheet10 = MultiCardLayout("10 business cards on a A4 sheet",
                          width = A4[0],
                          height = A4[1],
                          layout = BusinessCard,
                          xcount = 2,
                          ycount = 5)

layouts = {
    '1': BusinessCard,
    'A4': A4sheet,
    'A5L': A5card,
    'letter': Lettercard,
    '10': Sheet10,
}

def verify_json_data(json_dat):
    try:
        for dic in json_dat:
            if (type(dic.get('separator')) is not bool or
                type(dic.get('password')) is not str or
                type(dic.get('hint')) is not str):
                raise BadDataError
    except LookupError:
        raise BadDataError

def generate_pdf(output, json_dat, qrcode=False,
                 wifi_ssid=None,
                 encrypt=False,
                 layout='1',
                 pwdelems=True,
                 hint=True,
                 title=None):
    w = []
    h = []

    try:
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
    except LookupError:
        raise BadDataError

    password = "".join(w)

    dat = (w, h)

    if wifi_ssid:
        qrcode = True
        if title == None:
            title = wifi_ssid

    if qrcode:
        import qrcode
        if wifi_ssid:
            qr_dat = 'WIFI:T:WPA;S:"{}";P:"{}";;'.format(wifi_quote(wifi_ssid), wifi_quote(password))
        else:
            qr_dat = password
        qr = qrcode.make(qr_dat)
        qr = qr.get_image()
        qr = ImageReader(qr)
    else:
        qr = None

    if encrypt:
        enc = pdfencrypt.StandardEncryption(password + "--usr", password, strength=128)
    else:
        enc = None

    layout = layouts[layout]

    c = layout.draw(output, dat, hint=hint, pwdelems=pwdelems,
                    qr=qr, title=title, pdfargs={'encrypt': enc})
    c.setCreator(FULL_VERSION)
    c.setAuthor('')
    c.setSubject('')
    c.setTitle(title or '')
    c.showPage()
    c.save()

# Other outputs and data formats

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
    import argparse

    layout_helpstr = ("\nlayouts:\n" +
                      "\n".join("    {:<7s} : {:<15s} ({:3.0f} mm x {:3.0f} mm)"
                                .format(k, v.description, v.width / mm, v.height / mm)
                                for k, v in sorted(layouts.items())))

    parser = argparse.ArgumentParser(description='Generate password candidates',
                                     epilog=password_generator.format_helpstr +layout_helpstr,
                                     add_help=False,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-H', '--hint', action='store_true', help='show pronunciation hints')
    parser.add_argument('-Q', '--qrcode', action='store_true', help='show QR code')
    parser.add_argument('--wifi-ssid', help='generate QR code for WiFi WPA configuration')

    outgroup = parser.add_mutually_exclusive_group(required=True)
    outgroup.add_argument('-o', '--output', help='output file name')
    outgroup.add_argument('-O', '--output-base', help='output related data to specified basename or directory')

    parser.add_argument('--gpg-encrypt-to', help='encrypt plaintext output by gpg', metavar='EMAIL')
    parser.add_argument('--encrypt', action='store_true',
                        help=argparse.SUPPRESS #'encrypt PDF output by generated password itself'
    ) # ReportLab bug: encryption with CID font generates buggy PDF.

    parser.add_argument('-L', '--layout', help='choose output layout', choices=layouts.keys(), metavar='LAYOUT', default='1')
    parser.add_argument('--title', help='put title line')
    parser.add_argument('--no-partial-passwords', action='store_false', dest='pwdelems', help=argparse.SUPPRESS)
    parser.add_argument('--json', action='store_true',help='reuse previous passphrase data in JSON format')
    parser.add_argument('format', help='password format (or JSON filename with --json)')
    parser.add_argument('count', help='number of generated passwords', nargs='?', type=int, default=None)
    parser.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
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

        # format check
        if isinstance(json_dat, list) and 'password' in json_dat[0]:
            if opts.count != None:
                parser.error("given JSON contains single passphrase")
        elif 'elements' in json_dat:
            json_dat = json_dat['elements']
            if not isinstance(json_dat, list):
                parser.error("bad JSON input")
            if opts.count == None:
                parser.error("parameter count must be given to choose a single passphrase")
            if not 1 <= opts.count <= len(json_dat):
                parser.error("bad count given (must be in 1 -- {})".format(len(json_dat)))
            json_dat = json_dat[opts.count - 1]
        else:
            parser.error("bad JSON input")
    else:
        while True:
            try:
                l, diag = password_generator.generate(opts.format, opts.count if opts.count != None else 1)
            except password_generator.BadFormatError as e:
                parser.error(e.args[0])

            if opts.count == None:
                l = 1
                break

            for i in range(len(l)):
                print("{:2d}:  {}\n    ({})\n".format(i + 1, *l[i]), file=sys.stderr)

            print("Which one? (1-{}, RET for another set): ".format(len(l)), end="", file=sys.stderr)
            sys.stderr.flush()

            l = sys.stdin.readline().strip()

            if l != "":
                break
        try:
            json_dat = diag['elements'][int(l) - 1]
        except ValueError:
            print("Unrecognized input.  aborting.", file=sys.stderr)
            exit(2)

    try:
        verify_json_data(json_dat)
    except BadDataError:
        print("Bad data.  aborting.", file=sys.stderr)
        exit(2)

    password = "".join(e['password'] for e in json_dat)
    hintstr = "".join(e['hint'] for e in json_dat)

    if opts.hint:
        print("\nGenerated password: {}\n                   ({})".format(password, hintstr))
    else:
        print("\nGenerated password: {}".format(password))

    os.umask(os.umask(0o077) | 0o077)

    if opts.output_base:
        base, sep, out = opts.output_base.rpartition('/')
        if sep:
            os.makedirs(base, mode=0o700, exist_ok=True)
        output_base = opts.output_base if out != '' else opts.output_base + "password"
        output = output_base + ".pdf"
    else:
        output_base = None
        output = opts.output

    generate_pdf(output, json_dat, qrcode=opts.qrcode,
                 wifi_ssid=opts.wifi_ssid,
                 encrypt=opts.encrypt,
                 layout=opts.layout,
                 hint=opts.hint,
                 pwdelems=opts.pwdelems,
                 title=opts.title)

    if output_base:
        generate_textfile(output_base + ".txt", password,
                          encrypt_to=opts.gpg_encrypt_to)
        generate_textfile(output_base + ".json",
                          json.dumps(json_dat, sort_keys=True, indent=4),
                          encrypt_to=opts.gpg_encrypt_to)

if __name__ == '__main__':
    main()
