#!/usr/bin/python3
# Combinatorial password generator for make-password
# Written by Yutaka OIWA (AIST).
# (c) 2018 National Institute of Advanced Industrial Science and Technology.
# See LICENSE file copyright detials.
# [AIST program registration #H30PRO-2263]

if '.' in __name__: from . import password_generator
else: import password_generator

BadFormatError = password_generator.BadFormatError

from math import log2, ceil

# n = remaining characters to generate
# N_i = [number of characters in set i]
# v_i = [required number of characters in password from set i]

# f(0, v) = 《v == 〈0〉》
# f(n, v) =
#    Σ_i (N_i * f(n - 1, roundup(v - e_i)))
#
#   where roundup(v) = 〈max(v_i, 0)〉i ,
#         e_i = 〈 《i == j》 〉j ,
#         《 》 is truth value function (delta function),
#         〈x_i〉i  is a vector composed of elements x_i

# Total number of computation steps is:
#  n * Π_i (v_i)

#def dprint(*args, **kwargs): pass
#dprint=print

class CombinatorialGenerator(password_generator.WordsCorpusBase):
    def __init__(self, wordsets, canonical=False):
        sets = []
        lens = []
        reqcounts = []

        for s, c in self.canonify(wordsets, canonical):
            sets.append(s)
            lens.append(len(s))
            reqcounts.append(c)

        self.alli = range(len(sets))
        self.sets = tuple(sets)
        self.lens = tuple(lens)
        self.reqcounts = tuple(reqcounts)
        self.wordsets = [d for d, _ in wordsets]
        self.comb_cache = {}
        self.name = "combinatrial({})".format([wl.name for wl in self.wordsets])

    def get_repeated(self, *n, **k):
        return CombinatorialWordDictionary(self, *n, **k)

    @staticmethod
    def canonify(wordsets, canonical=False, expand=False):
        do_repeat = True
        if (not canonical) and expand:
            from password_generator import _expand_subs
            prep = _expand_subs
        else:
            prep = lambda x: x
        sets = []
        for i, (d, _) in enumerate(wordsets):
            if d.is_words:
                raise BadFormatError("only character-based set can be used for combinatorial passwords")
            sets.append((0, frozenset(prep(wordsets[i][0])), i))
        outsets = []
        for round in range(len(wordsets)):
            do_repeat = False
            e1, *sets = sorted([(len(s), s, i) for l, s, i in sets])
            outsets.append(e1)
            l1, s1, i1 = e1
            o = []
            #print("in round {}: e1={}, sets={}".format(round, e1, sets))
            for e in sets:
                (l, s, i) = e
                if s.isdisjoint(s1):
                    o.append(e)
                elif s.issuperset(s1):
                    if canonical:
                        raise BadFormatError("set {} ({}) is not disjoint with set {}: {} (non-canonical input)".format
                                         (i, wordsets[i][0], i1, wordsets[i1][0]))
                    if l == l1:
                        raise BadFormatError("set {} ({}) is sum of some other sets (including set {}: {})".format
                                         (i, wordsets[i][0], i1, wordsets[i1][0]))
                    o.append((l - l1, s - s1, i))
                else:
                    raise BadFormatError("set {} ({}) has partial overwrap with set {}: {}".format
                                     (i, wordsets[i][0], i1, wordsets[i1][0]))
            sets = o
        #print("final: outsets={}".format(outsets))
        sets = sorted(outsets, key=lambda x: x[2])
        #print("final: sets={}".format(sets))
        o = []
        for ii, (l, s, i) in enumerate(sets):
            assert(i == ii)
            o.append(("".join(sorted(list(s))), wordsets[i][1]))
        #print("final: o={}".format(o))
        return o

    def entropy():
        return (-1.0/0.0)

    def len():
        return 0

    def get_with_hint(x):
        raise IndexError

    def subset():
        # until output is sorted
        raise ValueError("combinatorial corpus is not subsettable")

class CombinatorialWordDictionary(password_generator.WordsCorpusBase):
    def __init__(self, combi, *a, entropy=None):
        self.__dict__.update(combi.__dict__)
        self.combs = None
        if len(a) == 1 and entropy == None:
            self.n = a[0]
        elif len(a) == 0 and entropy != None:
            self.n = self.__guess_n(entropy)
        else:
            raise TypeError("either and only one of n or entropy must be given {}".format((a, entropy)))

    def password_elements(self):
        return self.n

    def __guess_n(self, entropy):
        nc = sum(self.lens)
        if (nc < 2):
            raise BadFormatError("impossible to generate combinatorial corpus")
        n = max(int(ceil(entropy / log2(nc))), sum(self.reqcounts))
        # initial guess:
        #   Number of combinations is always less than those without charset restrictions.
        #   Thus, floor(entropy/log2(nc)) characters is below the solution,
        #   and ceil(entropy/log2(nc)) is smaller or equal to the minimal integer solution.
        #   Also, sum(reqcounts) characters is required to meet charset restrictions.

        while True:
            combs = self.combinations(n, self.lens, self.reqcounts, cache=self.comb_cache)
            if combs > 0 and log2(combs) >= entropy:
                break
            #if combs: print("trying {:2d} characters: entropy = {:7.3f} <  {:7.3f}".format(n, log2(combs), entropy))
            #else: print("trying {:2d} characters: entropy = -Inf    <  {:7.3f}".format(n, entropy))
            n += 1
        #print(    "got    {:2d} characters: entropy = {:7.3f} >= {:7.3f}".format(n, log2(combs), entropy))
        return n

    def len(self):
        if self.combs == None:
            combs = self.combinations(self.n, self.lens, self.reqcounts, cache=self.comb_cache)
            if combs == 0:
                raise BadFormatError("impossible to generate combinatorial corpus")
            self.combs = combs
        return self.combs

    def entropy(self):
        # not use len(self) to avoid integer overflow
        return log2(self.len())

    def get_with_hint(self, x):
        alli = self.alli

        if self.combs == None:
            self.entropy()

        def sub(x, n, v, lo, hi):
            if n == 0:
                assert(hi - lo == 1)
                assert(x == lo)
                return []

            assert(hi - lo == self.comb_cache[(n, v)])
            assert(lo <= x < hi)
            #dprint("SUB: x={} lo,hi={},{}, n={}, v={}".format(x, lo, hi, n, v))
            # to decide which sets to generate
            rfix = sum(v)
            if rfix > n:
                assert false
            elif rfix == n:
                f = tuple(v[i] > 0 for i in alli)
            else:
                f = tuple(1 for i in alli)
            top = []
            s = lo
            for i in alli:
                if f[i]:
                    charn = self.comb_cache[(n-1, self._v_decr(v,i))]
                    setn = charn * self.lens[i]
                    top.append((s, s + setn, i, charn))
                    s += setn
            #dprint("  borders: {}".format(top))
            assert(s == hi)
            k = None
            for elo, ehi, i, charn in top:
                if elo <= x < ehi:
                    k = (x - elo) // charn
                    break
            else:
                assert False
            #dprint("  chosen set = {} (range {}, {}), item={}".format(i, elo, ehi, k))
            c = self.sets[i][k]
            n_lo = elo + k * charn
            n_hi = n_lo + charn
            return [c] + sub(x, n - 1, self._v_decr(v,i), n_lo, n_hi)

        s = sub(x, self.n, self.reqcounts, 0, self.combs)

        return password_generator.WordTuple("".join(s), self.get_hint_by_word(s))

    @staticmethod
    def _v_decr(v, i, alli=None):
        if not alli:
            alli = range(len(v))
        return tuple(v[j] - int(i == j and v[j] > 0) for j in alli)

    @classmethod
    def combinations(self, n, N, v, cache=None):
        if cache == None:
            cache = {}

        alli = range(len(N))
        def sub(n, v):
            if n == 0:
                return 1 if all(v[i] <= 0 for i in alli) else 0
            if sum(v[i] for i in alli) > n:
                return False
            return sum((N[i] * rec(n-1, self._v_decr(v, i, alli=alli))
                        for i in alli))

        def rec(n, v):
            if (n, v) in cache:
                x = cache[(n,v)]
                #dprint("cache reused: {}, {} -> {}".format(n, v, x))
            else:
                #dprint("cache mishit: {}, {}".format(n, v))
                x = cache[(n,v)] = sub(n, v)
                #dprint("cache stored: {}, {} -> {}".format(n, v, x))
            return x

        return rec(n, v)

    def subset(self, set):
        # until output is sorted
        raise ValueError("combinatorial corpus is not subsettable")

    def index(self, w):
        # until output is sorted
        raise ValueError("combinatorial corpus is not subsettable")

    def __contains__(self, w):
        raise NotImplementedError

    def get_hint_by_word(self, w):
        # expand hint based on most-comprehensive base corpus:
        o = []
        for i in w:
            r = None
            for d in self.wordsets:
                k = d.get_hint_by_word(i)
                if k != None and len(k) > len(r or ""):
                    r = k
            if r == None:
                return None
            o.append(r)

        return "".join(o)
        
def main():
    from random import SystemRandom
    R = SystemRandom()
    import sys
    n, *args = sys.argv[1:]
    n = int(n)
    l = []
    i = len(args) // 2
    for i in range(i):
        sets = args[i * 2]
        reqcount = int(args[i * 2 + 1])
        l.append((sets, reqcount))
    print("requests={}, n={}".format(l, n))

    g = CombinatorialGenerator(l)
    print("canonified requests={}".format(list(zip(g.sets, g.reqcounts))))

    x = g.get_dict_by_length(n)

    print("entropy = {:.3f} bits".format(x.entropy()))

    if x.combs > 50:
        for i in range(10):
            k = R.randrange(x.combs)
            print("{}: {} ({})".format(i, x.get(k), k))
    else:
        for i in range(x.combs):
            print("{}: {}".format(i, x.get(i)))

if __name__ == '__main__':
    main()
