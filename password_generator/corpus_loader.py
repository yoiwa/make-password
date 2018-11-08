import sys, io, os
import re
from collections.abc import Sequence as abcSequence
from contextlib import ExitStack

corpus_base_path = None
__module__ = sys.modules[__name__]

if '.' in __name__:
    from . import password_generator
else:
    import password_generator

def load_corpus(target, *, rawname=False, diag=None, errorclass=RuntimeError):
        global corpus_base_path
        if not corpus_base_path:
            from pathlib import Path
            corpus_base_path = Path(__module__.__file__).parent / 'corpus'
        fname = str(corpus_base_path / (target + ".corpus"))

        fmt = False

        with ExitStack() as stack:
            try:
                f = open(fname, 'rb')
                f = stack.enter_context(f)
                b = f.peek(128)
            except OSError as e:
                try:
                    b = __module__.__loader__.get_data(fname)
                    f = io.BytesIO(b)
                except OSError as e:
                    raise errorclass("unknown wordlist {}:\n   Cannot load file {}: {}".format(target, fname, e))

            if b.startswith(b'#'):
                if b.startswith(b'#format hinted\n'):
                    fmt = 'hinted'
                elif b.startswith(b'#format packed\n'):
                    fmt = 'packed'
                elif b.startswith(b'#format '):
                    raise errorclass('Unrecognized wordlist {} in file {}'.format(target, fname))

            if fmt == 'packed':
                wlist = load_compact_corpus(f, name=target, errorclass=errorclass)
            elif fmt == 'hinted':
                raise RuntimeError('hinted corpus is not supported anymore; convert it to compact')
            else:
                wlist = load_text_corpus(f, name=target, errorclass=errorclass)

            if diag != None:
                diag.append("loaded {} words of corpus as {}".format(wlist.len(), target))
            if (wlist.len() == 0):
                raise errorclass("empty or bad corpus:" + target)
            return wlist

### CompactCorpus

def load_compact_corpus(*args, **kwargs):
    return CompactedCorpus(*args, **kwargs)

class CompactedCorpus(password_generator.WordsCorpusBase):
    MAGIC = 0x3b9c787 # 7digits
    VERSION = 2
    HEADER = b'#format packed\n'
    HEADER2 = b'#_-_-_-\n'
    MAXSIZE = 104857600

    def __init__(self, f, load_header=True, name="", errorclass=RuntimeError):

        if isinstance(f, str):
            f = open(f, 'rb')
            load_header = True
        elif isinstance(f, io.TextIOBase):
            f = f.buffer
            f.seek(0)
            load_header = True

        try:
            size = os.fstat(f.fileno()).st_size
            if size > self.MAXSIZE:
                raise errorclass('too large corpus: safety valve triggered')
        except io.UnsupportedOperation:
            size = -1

        if load_header:
            h = f.read(len(self.HEADER))
            if h != self.HEADER:
                raise errorclass('bad corpus: header not found')
        else:
            while(f.peek(1)[0] == ord(b'\n')):
                s = f.read(1)

        try:
            s = f.read(48)
            a = s.split(b' ')
            if len(a) < 3 or a[0] != b'#!!PCK!!':
                raise errorclass('bad corpus: bad magic line {}'.format(s))

            if int(a[1], 16) != self.MAGIC:
                raise errorclass('bad corpus: bad magic {:08x}'.format(int(a[1], 16)))

            if int(a[2], 16) != self.VERSION:
                raise errorclass('bad corpus: corpus format version mismatch ({} instead of {})'.format(int(a[2], 16), self.VERSION))

            if len(a) != 6 or a[5] != b'!!\n':
                raise errorclass('bad corpus: bad magic line {}'.format(s))

            blen, l = int(a[3], 16), int(a[4], 16)
        except ValueError:
            raise errorclass('bad corpus: bad magic line {}'.format(s))

        self.l = l

        tbllen = (l * 2 + 1) * 8

        if blen:
            s = f.read(blen)

        s = f.read(len(self.HEADER2))
        if s != self.HEADER2:
            raise errorclass('bad corpus: bad magic line {}', s)

        b = f.read(size - f.tell())
        blen = len(b)
        self.dat = b
        self.tblofs = blen - tbllen
        if self._getidx(0) != self.MAGIC:
            raise errorclass('bad corpus: bad index magic {:08x}'.format(self._getidx(0)))

        self.name = name

    def len(self):
        return self.l

    def get_word(self, i):
        if (i < 0 or i >= self.l or int(i) != i):
            raise IndexError(i)
        return self._get(i * 2 + 1)

    def get_with_hint(self, i):
        if (i < 0 or i >= self.l or int(i) != i):
            raise IndexError(i)
        return password_generator.WordTuple(self._get(i * 2 + 1), self._get(i * 2 + 2))

    def _getidx(self, i):
        o = self.tblofs + i * 8
        return int(self.dat[o : o + 8], 16)
        # int accepts \n

    def _get(self, i):
        o = self._getidx(i)
        o2 = self.dat.index(b'\n', o)
        #print("NONLAZY: ({})->{}".format((o,o2), self.dat[o:o2].decode('utf-8')), file=sys.stderr)
        return self.dat[o:o2].decode('utf-8')

### Text Corpus

def load_text_corpus(f, name="", errorclass=RuntimeError):
    no_apostroph = False
    in_header = True

    wlist = set()
    for l in f:
        l = l.strip()
        if l == b'':
            in_header = False
            continue
        if l.startswith(b'#'):
            if in_header:
                if l == b"#option no-apostrophe":
                    no_apostrophe = True
            continue

        in_header = False
        for word in re.sub(br'[,;.:/!?]', b' ', l).split():
            if (word == b'' or
                word.endswith(b"'") or
                word.endswith(b"'s")):
                continue
            for char in word:
                if char not in b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'":
                    break
                if no_apostroph and char == b"'"[0]:
                    break
            else:
                wlist.add(str(word, 'ascii'))
    wlist = list(wlist)
    return password_generator.SimpleWordCorpus(wlist, name=name)

if __name__ == '__main__':
    diag = []
    d = load_corpus(sys.argv[1], diag=diag)
    print("\n".join(diag))
    for i, w in enumerate(d):
        print("{:5d}: {}".format(i+1, w))

