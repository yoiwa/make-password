import sys
import subprocess
import io
import re
import threading
from contextlib import ExitStack

boilerplate = """### Generated file. DO NOT EDIT.
"""

class CorpusConvert:
    @staticmethod
    def kakasi(src, fname, dest, boilerplate):
        buf = []
        pbuf = []
        for line in src:
            line = line.strip()
            if line == '': continue
            if line[0] == '#': continue
            mo = re.match(r'^([a-z\']+) +\[([^ -~]+)\]$', line)
            if mo:
                en, jp = mo.group(1, 2)
                pbuf.append("{} {}".format(len(buf), en))
                buf.append(jp)
            else:
                for w in line.split(' '):
                    mo = re.match(r'^([^ -~]+)$', w)
                    if mo:
                        pbuf.append("{} {}".format(len(buf), w))
                        buf.append(w)
                    else:
                        pass
                        #print("## {}".format(w))

        with ExitStack() as stack:
            p = stack.enter_context(
                subprocess.Popen("kakasi -iutf8 -outf8 -rh -Ja -Ha",
                                 shell=True,
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE))
            def pf():
                for a in pbuf:
                    p.stdin.write(a.encode('utf-8') + b'\n')
                p.stdin.close()

            t = threading.Thread(target=pf, daemon=True)
            t.start()

            src = io.TextIOWrapper(p.stdout, encoding='utf-8', errors='substitute')
            os = {}

            print("#format hinted\n" + boilerplate, sep="", file=dest)

            for line in src:
                line = line.strip()
                mo = re.match(r'^(\d+) ([a-z\']+)$', line)
                if not mo:
                    print("### ", line, file=dest)
                    continue
                n, ro = mo.group(1, 2)
                n = int(n)
#                ro = re.sub(r'n([m])', r'm\1', ro)  # [bpm]
                ro = re.sub(r'\'', r'', ro)
                if ro in os:
                    print("## {}\t{}\t{}".format(ro, buf[n], os[ro]), file=dest)
                else:
                    os[ro] = buf[n]
                    print("{}\t{}".format(ro, buf[n]), file=dest)
#            t.join()

    @classmethod
    def convert(self, fname, ofname):
        hdr = ""
        processor = None
        with open(fname) as src:
            with open(fname) as src2:
                while True:
                    ll = src2.readline()
                    l = ll.strip()
                    if (l == '' or l[0] != '#'): break
                    if l != src.readline().strip():
                        assert False

                    (p, s, t) = l.partition(' ')
                    if (p == '#' or p.startswith('##')):
                        hdr += ll
                    elif (p == '#processor'):
                        processor = t
                    else:
                        raise RuntimeError("Unkown header:", p)
            fun = getattr(self, processor)
            with open(ofname, 'w') as dest:
                b = boilerplate + hdr
                fun(src, fname, dest, boilerplate = b)

if __name__ == '__main__':
    CorpusConvert.convert(*sys.argv[1:])
