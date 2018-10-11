[-]: # " -*- mode: gfm; coding: utf-8 -*- "

# make-password: Passphrase generator with corpus support

(c) 2018 National Institute of Advanced Industrial Science and Technology.

See LICENSE file for the terms of use.  
[AIST program registration #H30PRO-(TBD)]

## About the program

"make-password" is a random password/passphrase generator supporting
both dictionary-based passphrases and random-character passwords.

It's functionality includes:

  * Entropy computation/adjustment: it can determine appropriate
    length of passphrases based on the computed "entropy" of generated
    passphrases (number of possible variations).

  * Corpus/Dictionary-based passphrase generation: the generator can
    create passphrases based on randomly-chosen words from given
    corpus dictionaries.  The words can be collected from various sets
    of corpus.

  * Readable "hints" for passphrases: for passphrases based on
    non-English (Japanese currently supported) words, the program will
    also emit a readable "hint" for each chosen words in the original
    languages.  Hints will also be provided for alphabetical passwords
    with confusing characters (e.g. capital I v.s. lower l).

  * Flexible formatting: users can choose several ways of formatting
    for the passphrases: you can choose word-separating characters,
    mix alphabetical words and digit-based words within single
    password, and more.

"make-password-sheet" creates a PDF for printable "cheet strip" of a
generated passphrase, which is useful for off-line sharing of
passphrases.  It can print a passphrase to either a business card
(91mm x 55mm) or an ISO-A4 sheet with 10 copies of strips, with
readable passphrase hints and an optional QR barcode.


## Usage

(Installation procedures are given in a later section)

### make-password

    usage: make-password [-v] [-H] [-U] [--json] format [count]
    
    examples:
    
    make-password -v   A:128
    make-password      x8-x8
    make-password      a10-d:112
    make-password -vH  e:112     10
    make-password -vH  -j5       10

#### Options:

 * -v (--verbose): show diagnostic messages, e.g. computed entropy of
   passphrases.
 
 * -H (--hint): show a readable hint along with generated passphrases.
 
 * -U: set character encoding of output to UTF-8, regardless of locale
   settings.  Intended for embedded use-cases.
   
 * --json: output details of generated passphrases as a JSON-encoded
   data.  Its format is described in Appendix.  Intended for embedded
   use-cases.

 * format: specify style of passphrases/passwords, as described below.
 
 * count (optional): specify number of passphrases to be generated.
   If omitted, 1 is assumed.

#### Passphrase style specifiers

Most common-case styles of random passwords are specified with
single-character mnemonics, followed by a number representing
character counts.

 * `d16`: 16 numeric digits (e.g. `1234567890123456`)
 * `l8`: 8 lower-case characters (e.g. `abcdefgh`)
 * `a8`: 8 lowercase-or-numeric characters (e.g. `a1b2c3d4`)
 * `A8`: 8 alpha-numeric characters (e.g. `a1Ab2Bc3`)
 * `s8`: 8 ASCII printable symbols (e.g. `a1A!b2?B`)
 * `x`,`X` for hexadecimal digits
 * `B`,`b` for "BASE64" characters (original, FSSAFE variant).

There are some mnemonics for word-based passphrases.

 * `E4`: 4 random words chosen from nearly 10k-word English corpus.
   (e.g. `anyone become calendar`)  
   Lower-case `e` uses words from Basic English (2k-word).

* `j3`: 3 random romanized Japanese words (nouns)
  (e.g. `angou butsuri cha` ... corresponding to 暗号 [cryptography]
  物理 [physics] 茶 [tea])

Several specifiers can be put side-by-side to generate compound
passwords/passphrases.

 * `a8d8` (e.g. `abcdefgh12345678`)
 * `E4j3` (e.g. `anyone become calendar dictionary angou butsuri cha`)

Separators can be put before or between mnemonics to separate words.

 * `-E4`: use hyphen between words (e.g. `anyone-become-calendar`)
 * `,j3`: use comma between words (e.g. `angou,butsuri,cha`)
 * `"@"E3`: use at-mark between words (e.g. `anyone@become@calendar`)
 * `""E3`: no spaces between words (e.g. `anyonebecomecalendar`)
 * `a8-d8`: put hyphen between alphabet password and digits
   (e.g. `abcdefgh-12345678`)

Allowed separators are space, hyphen, comma, underbar, period or any
double-quoted string. Please note that use of space or
double-quotation will need single-quoting for the whole format spec
on most shell environment.  
(e.g. `make-password '""E3'` or `make-password 'a8 d8'`)  
If no separator is given, dictionary-words are space-separated and
characters are not separated by default.

And, the most important feature of the format specification is an
entropy specifier: a colon followed by a decimal number at the end
means the required quality of generated passphrases in "bits". The
last element of the format is automatically repeated to meet the
required entropy.

 * `E:96`: a 96-bit passphrase from English words.  (e.g. `anyone
   become calendar dollar edit france garbage hole`: 8 words)

 * `-j:40`: a short 40-bit passphrase from Japanese words, separated
   by hyphen.  (e.g. `angou-butsuri-cha-denki`)

 * `l8-d:80`: 8 lowercase alphabets, separated by hyphen, and some
   digits to meet 80-bit quality in total.
   (e.g. `abcdefgh-1234567890123`: 13 digits after alphabets)

 * `-x4:128`: repeated set of 4 hexadecimal digits up to 128 bits.
   (e.g. `0123-4567-89ab-cdef-1234-5678-9abc-def0`)

Some more detailed specifications are also available as follows:

 * `[name]` specifies either a word-set or character-set with a name.
   For example, `[alnum]` is equivalent to `A`, `[english]` is
   equivalent to `e`.  `[base32]` gives a character set composed of
   lowercase-alphabet or digits from 2 to 7.
   (e.g. `[base32]7`: `a2b3c4d`)
 
   Locally-installed dictionaries can also be specified in this format.

 * Wordsets subset by the first characters can be specified by
   circumflex like `[english^a-ex-z]` or `[j^kst]`.  (both names and
   mnemonics are accepted before a hat).  Character-sets can also be
   subset.  It is error to create a single-element or empty set of
   words/characters (e.g. `[d^a-z]` (no alphabet in the digit set),
   `[x^f-k]` (only `f` is contained), `[english^O]` (only October
   begins with capital O)).

_Note: obviously, all of example outputs above are *intentionally* non-random at all.  Never use these as passphrases!_


### make-password-sheet

    usage: make-password-sheet [-H] [-Q] [--wifi-ssid WIFI_SSID]
                               (-o OUTPUT | -O OUTPUT_BASE)
                               [--gpg-encrypt-to email] [-L {1,10}]
                               (format [count] | --json FILENAME)

    examples:

    make-password-sheet -H -L10 -o myfilepwd.pdf -j5
    make-password-sheet -Q     -O yourfilepwd/   ,E6
    make-password-sheet -HQ --wifi-ssid=MYWIFI    a10-d:112
    make-password-sheet -L10 --json previous-data.json


#### Options:

 * -H (--hint): print a readable hint along with the generated passphrase.
 
 * -Q (--qrcode): print a QR barcode for the generated passphrase.
 
 * --wifi-ssid: Generate a special QR barcode for configuration of given WiFi SSID.
   It must be specified together with '-Q'.
   
 * -L 1 (default): print a passphrase to a 91mm x 55mm card.
 * -L 10: print a 10 copies of cards to an A4 sheet.

 * -o OUTPUT.pdf: write a generated PDF file to 'OUTPUT.pdf'.
 * -O BASE: save output data to filenames based on BASE.
   More details are described later. Either -o or -O is mandatory.
 * --gpg-encrypt-to: with an -O option, encrypt text output files
   (_except the PDF sheet_) to that email address by GnuPG.

 * format: specifies a style of passphrases, as described before.
 
 * count (optional): number of passphrases to be generated.

    * If it is 1 or omitted, single passphrase is generated and printed to the sheet.

    * If it is 2 or more, the specified number of passphrase candidates
      are generated and shown to console, and the user should choose
      one of these for printed.  In this case, the program must be
      called from an interactive terminal.
   
 * --json: reload a previously-generated passphrase from the JSON
   save-file generated by the -O option.

##### Files generated with -O option

if `-O` option is specified as an `-O base` option, any files starting
with `base.` might possibly be overwritten.  When it is specified
either like `-O dir/` or like `-O dir/base`, it will create a
directory `dir` if not existing and put all outputs inside that
directory.  For the safest usage, specify a non-existent directory.

Currently, it will output the following files.

 * `*.pdf`: The passphrase sheet, as same as those generated by `-o`.

 * `*.txt`: A bare text file containing the generated passphrase.

 * `*.json`: A detailed information on the generated passphrase.
   This file can be used as an input to `--json` option.
   (When gpg-encrypted, use this file as `gpg -d < ....json | make-password-sheet ... --json -`)



## Installation

Python 3.5 or later is required.

Packages `reportlab` and `qrcode` packages from PyPi are also required
for `make-password-sheet`.

For system-wide deployment, put the `password_generator` module
directory to Python library path.  Two top-level scripts are copied to
some executable path.

Alternatively, for single-user use, putting all archive contents to an
arbitrary directory and making a symbolic links to the scripts from an
executable path will also work.

For portable usage, the file `password_generator/password_generator.py`
can be used as a standalone script, but only the character-based
styles and the 'e' dictionary will work.

### Additional dictionaries

You can add any kinds of ASCII text files to the
`password_generator/corpus` directory with an extension `.corpus`.
The wordset can be loaded with its basename within `[]`.  For corpus
with reading hints, refer `corpus_conver.py` for details.

Authors are welcoming contribution of new wordset along with reading
hints.  However, please ensure that such data are generated from
publicly-available source with explicit permissions for redistribution
of modified derivatives (e.g. BSD-licensed or CC-BY-SA 3.0).

### Dictionary recompilation

All preset dictionaries contained in the distribution are already
processed to use.  If you really want to regenerate the dictionaries,
you will need some additional tools/files. See `Makefile.corpus` for
some details.

 * `[jwikipedia10k]` set requires `kakasi` kanji-kana conversion tool.

 * `j` and `J` sets requires the naist-jdic-utf8 package contained in
   Debian archive or elsewhere.

## Acknowledgements

English word corpus and [jwikipedia10k] corpus are extracted from data
publicly shared by Wikimedia Foundation.  10k-word English corpus is
based on the materials available in the Gutenberg Project, available
through Wikimedia.

Japanese word corpus are generated from the "NAIST Japanese
Dictionary" dataset from Nara Institute of Science and Technology.

## Author(s)

Yutaka OIWA  
Information Technology Research Institute  
Department of Information Technology and Human Factors  
National Institute of Advanced Industrial Science and Technology (AIST)

## Appendix: JSON data format

Data format for a single passphrase, used in both make-password and
make-password-sheet is like following:

``` JSON
[
    { "entropy": 41.3594000115385,
      "hint": "[zero 0][one 1]234567",
      "password": "12345678",
      "separator": false },
    { "entropy": 0.0,
      "hint": "-",
      "password": "-",
      "separator": true },
    { "entropy": 41.3594000115385,
      "hint": "abcdefgh",
      "password": "abcdefgh",
      "separator": false }
]
```

A data for single passphrase is an array of passphrase elements.

Each element is an object containing the following keys:
  * "password": a word element in passphrase.
  * "hint": a description or pronunciation hint about the above password.
  * "entropy": an entropy contained in this element, in bits.
  * "separator": a boolean whether the element is pattern-fixed or randomly-generated.
  * Other keys may appear in the future.

The `--json` option of make-password-sheet expects this format.

Data exported by the `--json` option of make-password is like following:

``` JSON
{
    "diag": "Entropy computation: 5.170 * 8 = 41.359 bits\nEntropy computation: 5.170 * 8 = 41.359 bits\nEntropy computation: total generated entropy 82.719 bits",
    "elements": [
        [
          { "entropy": 41.3594000115385,
            "hint": "[zero 0][one 1]234567",
            "password": "01234567",
            "separator": false },
          { "entropy": 0.0,
            "hint": "-",
            "password": "-",
            "separator": true },
          { "entropy": 41.3594000115385,
            "hint": "abcdefgh",
            "password": "abcdefgh",
            "separator": false }
        ],
        [
          { "entropy": 41.3594000115385,
            "hint": "[zero 0]246[eight 8]135",
            "password": "02468135",
            "separator": false },
          { "entropy": 0.0,
            "hint": "-",
            "password": "-",
            "separator": true },
          { "entropy": 41.3594000115385,
            "hint": "ijk[lower l]mnop",
            "password": "ijklmnop",
            "separator": false } ],
     ],
    "entropy": 82.718800023077,
    "passwords": [
        [ "01234567-abcdefgh",
          "[zero 0][one 1]234567-abcdefgh" ],
        [ "02468135-ijklmnop",
          "[zero 0]246[eight 8]135-ijk[lower l]mnop" ],
    ]
}
```

The data is an object containing the following keys:
  * "diag": a string containing any diagnostic messages.
  * "elements": an array of a single passphrase, whose format is described above.
  * "entropy": a total entropy contained in each passphrase, in bits.
  * "passwords": a array of (password-hint) pair of strings.
  * Other keys may appear in the future.
