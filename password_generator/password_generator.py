#!/usr/bin/python3
# make-password: passphrase generator with dictionary corpus support.
# Written by Yutaka OIWA (AIST).
# (c) 2018 National Institute of Advanced Industrial Science and Technology.
# See LICENSE file copyright detials.

import sys
import re
import io
import os
from collections.abc import Sequence as abcSequence
from random import SystemRandom
from math import log2, ceil

VERSION = '1.0alpha2'

R = SystemRandom()
# SystemRandom _is_ secure from Python 3.3, despite warnings in Python documents.
# Indeed, the "secrets" module introduced in Python 3.6 is implemented upon SystemRandom.

class BadFormatError(RuntimeError):
    pass

def generate(fspec, count):
    """Generate <count> number of random passwords/passphrases.

    The passes are formated according to <fspec>.

    Returned value is (list, diagnostic_data),
    where list is a <count>-element sequence of
    pair of (password, reading hint for password).
    diagnostic_data is a dict at least containing
      key 'diag': (str) message for diagnostics,
      key 'entropy': (float) estimated entropy of generated passwords.

    Raises BadFormatError if fspec is either bad or not able to be satisfied.
    """

    diag = []
    fspec, entropy = _parse_fspec(fspec, diag=diag)
    if count < 1:
        raise BadFormatError('bad count of passwords specified')

    elements = []
    result = []
    for ncount in range(count):
        e = 0.0
        o = []

        def elem(e, f, o, h):
            return {'entropy': e, 'separator': f, 'password': o, 'hint': h }

        def proc(filling, i, sep, wl, iswords, ct):
            nonlocal e
            nonlocal o
            nonlocal o_hint

            initial = not filling and i == 0

            l1 = len(wl)
            e1 = log2(l1)

            if ct == 0:
                if entropy == None or i != len(fspec) - 1:
                    ct = 1
                elif e >= entropy:
                    ct = 0
                else:
                    ct = int(ceil((entropy - e) / e1))
                if ncount == 0 and ct > 0:
                    diag.append("Entropy computation: {0:.3f} * {2:d} = {3:.3f} bits".format(e1, e, ct, ct * e1))
                e += ct * e1
            else:
                if ncount == 0:
                    diag.append("Entropy computation: {0:.3f} * {2:d} = {3:.3f} bits".format(e1, e, ct, ct * e1))
                e += ct * e1

            if iswords:
                intersep = sep if sep != None else " "
                presep = "" if initial else sep if sep != None else " "
                for c in range(0, ct):
                    w = wl[R.randrange(l1)]
                    if type(w) is tuple:
                        w, h = w
                    else:
                        w, h = w, w
                    s = presep if c == 0 else intersep
                    sh = " " if (s == "" and c != 0) else s
                    if sh: o.append(elem(0.0, True, s, sh))
                    o.append(elem(e1, False, w, h))
            else:
                if ct != 0:
                    intersep = ""
                    presep = "" if initial else sep
                    if presep: o.append(elem(0.0, True, presep, presep))
                    ow = []
                    oh = []
                    for c in range(0, ct):
                        w = wl[R.randrange(l1)]
                        if type(w) is tuple:
                            w, h = w
                        else:
                            w, h = w, w
                        ow.append(w)
                        oh.append(h)
                    o.append(elem(ct * e1, False, "".join(ow), "".join(oh)))

        for i in fspec:
            proc(False, *i)
        while(entropy != None and e < entropy):
            proc(True, *(fspec[-1]))

        if ncount == 0:
            diag.append("Entropy computation: total generated entropy {:.3f} bits".format(e))

        o_word = "".join(x['password'] for x in o)
        o_hint = "".join(x['hint'] for x in o)

        elements.append(o)
        result.append((o_word, o_hint))

    return result, {'passwords': result, 'elements': elements, 'diag': "\n".join(diag), 'entropy': e}

def _expand_subs(s):
    o = set()
    while s != '':
        mo = re.match(r'\A(.)(?:-(.))?(.*)\Z', s)
        assert (mo != None), s
        if mo.group(2) == None:
            o.add(ord(mo.group(1)))
        else:
            for e in range(ord(mo.group(1)), ord(mo.group(2)) + 1):
                o.add(e)
        s = mo.group(3)
    r = "".join(chr(x) for x in o)
    return r

def _remove_backslash(s):
    if s == None: return None
    return re.sub(r"\\(.)", r"\1", s)

def _parse_fspec(s, *, diag=None):
    o = []
    i = 0
    orig_s = s
    while(s != ""):
        mo = re.match(r"""\A
                          (?:
                             (?P<sep1>[\ \-/,.])
                            |"(?P<sep2>(?:[^\\\"]|\\.)*)"
                          )?
                          (?:
                             (?P<pat1>[a-zA-Z])
                            |\[:?
                              (?P<pat2>[\w\-_]+)
                                 (?:\^(?P<subs>[\w_\-]+))?
                              :?\])
                          (?P<dig>\d*)
                          (?P<rest>.*)\Z""", s, re.X)

        if not mo:
            break
        (sep1, sep2, pat1, pat2, subs, dig, s) = mo.group('sep1', 'sep2', 'pat1', 'pat2', 'subs', 'dig', 'rest')
        sep = sep1 or _remove_backslash(sep2)
        pat = pat1 or pat2

        if pat in Charlist.mapping:
            wl = Charlist.mapping[pat]
            iswords = False
        else:
            wl = Wordlist.load_wordlist(pat, diag=diag)
            iswords = True

        if subs:
            subse = _expand_subs(subs)
            wl = [w for w in wl if (w[0][0] if type(w) is tuple else w[0]) in subse]
            if len(wl) == 0:
                raise BadFormatError("no words starting with [{}] in wordset {}".format(subs, pat))
            elif len(wl) == 1:
                raise BadFormatError("only one word starting with [{}] in wordset {}".format(subs, pat))

        if len(wl) <= 1:
            raise BadFormatError("not enough candidate in wordset {}".format(subs, pat))

        o.append((i, sep, wl, iswords, (int(dig) if dig != '' else 0)))
        i += 1

    mo = re.match(r"\A(?: *:(\d+))?\Z", s)
    if not mo:
        raise BadFormatError("parse failed at " + s)

    if i == 0:
        raise BadFormatError("No format specifier found in " + s)

    entropy = mo.group(1)
    entropy = entropy and float(entropy)
    return (o, entropy)

def parse_commandline(parser):
    # preprocess arguments:
    args = sys.argv[1:]
    for i in range(len(args)):
        s = args[i]
        if (s == '--'):
            break
        if (len(s) >= 2 and s[0] == '-'):
            c = s[1]
            if (c == '[' or
                c in Charlist.mapping or
                c in Wordlist.mapping):
                args[i:i] = ('--',)
                break

    return parser.parse_args(args)

format_helpstr = """
password format specifier:
    <charset><numbers> (d8, A8, x8 etc...):
      sequences of characters from predefined sets.
        d: digits l: lowercase a: lowercase + digits, 
        A: lowercase + upper + digits, x,X: hexadecimal, 
        B: Base64, b: Base64-FSSAFE, s: ASCII printable symbols.

    <wordset><numbers> (e8, [english]8, j8):
      words selected from wordset corpuses separated by spaces.
        e: ~2k word   Basic words in English,
        E: ~10k word  English from Gutenberg project,
        j: ~37k word  Japanese romanization from NAIST-JDIC.
        J: ~132k word Japanese romanization from NAIST-JDIC.
      More word corpuses can be added from external sources.

    -e8, -j8 etc.: words separated by a hyphen as a separator
            (period, comma, space, slash are also accepted as a separator)

    d8a8, d8-a8, -e8-d8 etc.: 
      multiple specifiers can be concatenated with optional separators,

    d:128, e:128, -e:128, d8-a:128, -a5:128: 
      ":<bits>" makes the last specifier to be repeated
      until generated passwords have <n>-bit of entropy (possibility).
"""

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Generate passphrase candidates',
                                     epilog=format_helpstr,
                                     add_help=False,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-v', '--verbose', action='count', help='show some additional diagnostics', dest='verbose')
    parser.add_argument('-H', '--hint', action='store_true', help='show pronunciation hint')
    parser.add_argument('-U', '--force-unicode', action='store_true', help='enforce UTF-8 output')
    parser.add_argument('--json', action='store_true', help='output formatted in json')
    parser.add_argument('--help', action='help', help='show this help message and exit')
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
    parser.add_argument('format', help='password format')
    parser.add_argument('count', help='number of generated passwords', nargs='?', type=int, default=1)

    opts = parse_commandline(parser)

    set_stdout_encoding(opts.force_unicode)

    try:
        l, diag = generate(opts.format, opts.count)
    except BadFormatError as e:
        parser.error("Bad format: " + str(e))

    if opts.json:
        import json
        print(json.dumps(diag, sort_keys=True, indent=4))
    else:
        if opts.verbose:
            print(diag['diag'], file=sys.stderr)
        for o, hint in l:
            print(o)
            if (opts.hint):
                print("# " + hint + "\n")

    exit(0)

def set_stdout_encoding(forced):
    import codecs
    encoding = sys.stdout.encoding
    ename = codecs.lookup(encoding).name

    if ename == 'utf-8':
        return

    if ename == 'ascii' or forced:
        new_ename = 'utf-8'
    else:
        new_ename = ename

    if hasattr(type(sys.stdout), 'reconfigure'):
        sys.stdout.reconfigure(encoding=new_ename, errors='namereplace')
    else:
        sys.stdout = type(sys.stdout)(sys.stdout.buffer, encoding=new_ename, errors='namereplace')

class Charlist:
    def _annotate(l):
        _Annotations = {
            '0': '[zero 0]',            'O': '[capital O]',
            '1': '[one 1]',             'I': '[capital I]',             'l': '[lower l]',
            '|': '[vert. bar |]',       '!': '[excl. mark !]',
            '-': '[hyphen -]',          '~': '[symbol tilde ~]',        '_': '[underbar _]',
            ',': '[comma ,]',           '.': '[period .]',
            ';': '[semicolon ;]',       ':': '[colon :]',
            '[': '[open bracket]',      ']': '[close bracket]',
            '{': '[open brace]',        '}': '[close brace]',
            '<': '[less than]',         '>': '[gtr. than]',
            '(': '[open paren]',        ')': '[close paren]',
            '"': '[dbl. quote "]',      "'": "[single quote ']",        '`': '[back quote `]',
            "\\": '[back slash \\]',    "/": '[backslash /]',
            '8': '[eight 8]',           '&': '[ampersand &]',
            '%': '[percent %]',         '@': '[at mark @]',
            '$': '[dollar $]',          '*': '[asterisk *]',            '#': '[number mark #]',
            '+': '[plus +]',            '=': '[equals =]',              '^': '[circumflex ^]',
        }

        return [(x, _Annotations.get(x, x)) for x in l]

    # raw sets
    Digits = "0123456789"
    Lower = "abcdefghojklmnopqrstuvwxyz"
    Upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    Hexadecimal = "0123456789abcdef"
    UpperHexadecimal = "0123456789ABCDEF"
    Base32 = Lower + '234567'
    Base32Upper = Upper + '234567'
    # annotated sets
    LowerAlphaNumeric = _annotate(Digits + Lower)
    AlphaNumeric = _annotate(Digits + Lower + Upper)
    Base64 = AlphaNumeric + _annotate("+/")
    Base64_FSSAFE = AlphaNumeric + _annotate("-_")
    Symbols = _annotate(chr(c) for c in range(33,127))

    mapping = {
        "d": Digits,
        "l": Lower,
        "a": LowerAlphaNumeric,
        "A": AlphaNumeric,
        "x": Hexadecimal,
        "X": UpperHexadecimal,
        "B": Base64,
        "b": Base64_FSSAFE,
        "s": Symbols,
        "alnum": AlphaNumeric,
        "digit": Digits,
        "lower": Lower,
        "upper": Upper,
        "xdigit": Hexadecimal,
        "base32": Base32,
        "base32upper": Base32Upper
    }

class Wordlist:
    # Builtin Corpuses

    # From https://simple.wikipedia.org/wiki/Wikipedia:Basic_English_ordered_wordlist
    BasicEnglish ="""
    I a able about account acid across act addition adjustment
    advertisement after again against agreement air all almost among
    amount amusement and angle angry animal answer ant any apparatus
    apple approval arch argument arm army art as at attack attempt
    attention attraction authority automatic awake baby back bad bag
    balance ball band base basin basket bath be beautiful because bed
    bee before behaviour belief bell bent berry between bird birth bit
    bite bitter black blade blood blow blue board boat body boiling
    bone book boot bottle box boy brain brake branch brass bread
    breath brick bridge bright broken brother brown brush bucket
    building bulb burn burst business but butter button by cake camera
    canvas card care carriage cart cat cause certain chain chalk
    chance change cheap cheese chemical chest chief chin church circle
    clean clear clock cloth cloud coal coat cold collar colour comb
    come comfort committee common company comparison competition
    complete complex condition connection conscious control cook
    copper copy cord cork cotton cough country cover cow crack credit
    crime cruel crush cry cup current curtain curve cushion cut damage
    danger dark daughter day dead dear death debt decision deep degree
    delicate dependent design desire destruction detail development
    different digestion direction dirty discovery discussion disease
    disgust distance distribution division do dog door doubt down
    drain drawer dress drink driving drop dry dust ear early earth
    east edge education effect egg elastic electric end engine enough
    equal error even event ever every example exchange existence
    expansion experience expert eye face fact fall false family far
    farm fat father fear feather feeble feeling female fertile fiction
    field fight finger fire first fish fixed flag flame flat flight
    floor flower fly fold food foolish foot for force fork form
    forward fowl frame free frequent friend from front fruit full
    future garden general get girl give glass glove go goat gold good
    government grain grass great green grey grip group growth guide
    gun hair hammer hand hanging happy harbour hard harmony hat hate
    have he head healthy hearing heart heat help here high history
    hole hollow hook hope horn horse hospital hour house how humour
    ice idea if ill important impulse in increase industry ink insect
    instrument insurance interest invention iron island jelly jewel
    join journey judge jump keep kettle key kick kind kiss knee knife
    knot knowledge land language last late laugh law lead leaf
    learning leather left leg let letter level library lift light like
    limit line linen lip liquid list little living lock long look
    loose loss loud love low machine make male man manager map mark
    market married mass match material may meal measure meat medical
    meeting memory metal middle military milk mind mine minute mist
    mixed money monkey month moon morning mother motion mountain mouth
    move much muscle music nail name narrow nation natural near
    necessary neck need needle nerve net new news night no noise
    normal north nose not note now number nut observation of off offer
    office oil old on only open operation opinion opposite or orange
    order organization ornament other out oven over owner page pain
    paint paper parallel parcel part past paste payment peace pen
    pencil person physical picture pig pin pipe place plane plant
    plate play please pleasure plough pocket point poison polish
    political poor porter position possible pot potato powder power
    present price print prison private probable process produce profit
    property prose protest public pull pump punishment purpose push
    put quality question quick quiet quite rail rain range rat rate
    ray reaction reading ready reason receipt record red regret
    regular relation religion representative request respect
    responsible rest reward rhythm rice right ring river road rod roll
    roof room root rough round rub rule run sad safe sail salt same
    sand say scale school science scissors screw sea seat second
    secret secretary see seed seem selection self send sense separate
    serious servant sex shade shake shame sharp sheep shelf ship shirt
    shock shoe short shut side sign silk silver simple sister size
    skin skirt sky sleep slip slope slow small smash smell smile smoke
    smooth snake sneeze snow so soap society sock soft solid some son
    song sort sound soup south space spade special sponge spoon spring
    square stage stamp star start statement station steam steel stem
    step stick sticky stiff still stitch stocking stomach stone stop
    store story straight strange street stretch strong structure
    substance such sudden sugar suggestion summer sun support surprise
    sweet swim system table tail take talk tall taste tax teaching
    tendency test than that the then theory there thick thin thing
    this though thought thread throat through thumb thunder ticket
    tight till time tin tired to toe together tomorrow tongue tooth
    top touch town trade train transport tray tree trick trouble
    trousers true turn twist umbrella under unit up use value verse
    very vessel view violent voice waiting walk wall war warm wash
    waste watch water wave wax way weather week weight well west wet
    wheel when where while whip whistle white who why wide will wind
    window wine wing winter wire wise with woman wood wool word work
    worm wound writing wrong year yellow yes yesterday you young
    """.split()

    # from https://simple.wikipedia.org/wiki/Wikipedia:Basic_English_combined_wordlist
    MoreBasicEnglish = """
    April August December Dominion Embassy Empire February Friday
    Geography Geology Geometry I Imperial January July June March May
    Monday November October Physics Physiology President Prince
    Princess Psychology Purr Royal Saturday September Sunday Thursday
    Tuesday Wednesday a able about absence absorption acceleration
    acceptance accessory accident account acid across act acting
    active actor addition address adjacent adjustment adventure
    advertisement advice after afterthought again against age agency
    agent ago agreement air airplane alcohol algebra all allowance
    almost along also alternative aluminium always ambition ammonia
    among amount amplitude amusement anchor and anesthetic angle angry
    animal ankle another answer ant any anybody anyhow anyone anything
    anywhere apparatus appendage apple application approval
    approximation arbitrary arbitration arc arch area argument
    arithmetic arm army arrangement art as asbestos ash asset
    assistant at attack attempt attention attraction authority autobus
    automatic automobile average awake awkward axis baby back backbone
    backwoods bad bag balance balcony bale ball ballet band bang bank
    bankrupt bar bark barrel base based basin basing basket bath be
    beak beaker beard beat beautiful because become bed bedroom bee
    beef beer beeswax before behavior behind belief bell belt bent
    berry bet between bill biology bird birefringence birth birthday
    birthright bit bite bitter black blackberry blackbird blackboard
    blade blame blanket blood bloodvessel blow blue bluebell board
    boat body boiling bomb bone book bookkeeper boot both bottle
    bottom box boy brain brake branch brass brave bread break
    breakfast breast breath brick bridge bright broken broker brother
    brown brush brushwood bubble bucket bud budget builder building
    bulb bunch buoyancy burial burn burned burner burning burst
    business busy but butter buttercup button by cafe cake calculation
    calendar call camera canvas capacity capital card cardboard care
    carefree caretaker carpet carriage cart carter cartilage case cast
    cat catarrh cause cave cavity cell centi ceremony certain
    certificate chain chair chalk champagne chance change character
    charge chauffeur cheap check cheese chemical chemist chemistry
    chest chief child chimney chin china chocolate choice chorus
    church cigarette circle circuit circulation circumference circus
    citron civilization claim claw clay clean clear cleavage clever
    client climber clip clock clockwork cloth clothier clothing cloud
    club coal coat cocktail code coffee cognac coil cold collar
    collection college collision colony color column comb combination
    combine come comfort committee common commonsense communications
    company comparison competition complaint complete complex
    component compound concept concrete condition conductor congruent
    connection conscious conservation consignment constant consumer
    continuous contour control convenient conversion cook cooked
    cooker cooking cool copper copy copyright cord cork corner
    correlation corrosion cost cotton cough country court cover cow
    crack credit creeper crime crop cross cruel crush cry crying
    cunning cup cupboard current curtain curve cushion cusp customs
    cut damage damping dance dancer dancing danger dark date daughter
    day daylight dead dear death debit debt deci decision deck
    decrease deep defect deficiency deflation degenerate degree
    delicate delivery demand denominator density department dependent
    deposit desert design designer desire destruction detail
    determining development dew diameter difference different
    difficulty digestion dike dilution dinner dip direct direction
    dirty disappearance discharge discount discovery discussion
    disease disgrace disgust dislike dissipation distance distribution
    disturbance ditch dive division divisor divorce do dog doll
    domesticating door doubt down downfall drain drawer dreadful dream
    dress dressing drift drink driver driving drop dropped dropper dry
    duct dull dust duster duty dynamite each ear early earring earth
    earthwork east easy economy edge education effect efficiency
    effort egg eight either elastic electric electricity eleven
    elimination employer empty encyclopedia end enemy engine engineer
    enough envelope environment envy equal equation erosion error
    eruption evaporation even evening event ever evergreen every
    everybody everyday everyone everything everywhere exact example
    exchange excitement exercise existence expansion experience
    experiment expert explanation explosion export expression
    extinction eye eyeball eyebrow eyelash face fact factor failure
    fair fall false family famous fan far farm farmer fastening fat
    father fatherland fault fear feather feeble feeling female ferment
    fertile fertilizing fever fiber fiction field fifteen fifth fifty
    fight figure fin financial finger fingerprint fire firearm fired
    firefly fireman fireplace firework firing first fish fisher
    fisherman five fixed flag flame flash flask flat flesh flight
    flint flood floor flour flow flower fly focus fold folder
    foliation food foolish foot football footlights footman footnote
    footprint footstep for force forecast forehead foreign forgiveness
    fork form forty forward four fourteen fourth fowl fraction
    fracture frame free frequent fresh friction friend from front
    frost frozen fruit full fume funnel funny fur furnace furniture
    fusion future garden gardener gas gasworks gate general generation
    germ germinating get gill girl give glacier gland glass glove
    glycerin go goat god gold goldfish good goodlooking goodnight
    government grain gram grand grass grateful grating gravel gray
    grease great green grey grief grip grocery groove gross ground
    group growth guarantee guard guess guide gum gun gunboat gunmetal
    gunpowder habit hair half hammer hand handbook handkerchief handle
    handwriting hanger hanging happy harbor hard harmony hat hate have
    he head headdress headland headstone headway healthy hearing heart
    heat heated heater heating heavy hedge help here hereafter
    herewith high highlands highway hill himself hinge hire hiss
    history hold hole holiday hollow home honest honey hoof hook hope
    horn horse horseplay horsepower hospital host hotel hour hourglass
    house houseboat housekeeper how however human humor hundred hunt
    hurry hurt husband hyena hygiene hysteria ice idea if igneous ill
    image imagination import important impulse impurity in inasmuch
    inclusion income increase index individual indoors industry
    inferno infinity inflation influenza inheritance ink inland inlet
    inner innocent input insect inside instep institution instrument
    insulator insurance integer intelligent intercept interest
    international interpretation intersection into intrusion invention
    inverse investigation investment invitation iron island itself jam
    jaw jazz jealous jelly jerk jewel jeweler join joiner joint
    journey judge jug juice jump jury justice keep keeper kennel
    kettle key kick kidney kilo kind king kiss kitchen knee knife
    knock knot knowledge lace lag lake lame lamp land landmark
    landslip language large last late latitude laugh laughing lava law
    lawyer layer lazy lead leaf learner learning least leather lecture
    left leg legal length lens less lesson let letter level lever
    liability library license lid life lift light lighthouse like lime
    limestone limit line linen link lip liqueur liquid list liter
    little liver living load loan local lock locker locking locus long
    longitude look loose loss loud love low luck lump lunch lung
    macaroni machine madam magic magnetic magnitude make malaria male
    man manager manhole mania manner many map marble margin mark
    marked market marriage married mass mast match material
    mathematics mattress mature may meal mean meaning measure meat
    medical medicine medium meeting melt member memory meow mess
    message metabolism metal meter micro microscope middle military
    milk mill milli million mind mine miner mineral minute mist mixed
    mixture model modern modest momentum money monkey monopoly month
    mood moon moral more morning most mother motion mountain moustache
    mouth move much mud multiple multiplication murder muscle museum
    music myself nail name narrow nasty nation natural nature navy
    near nearer neat necessary neck need needle neglect neighbor nerve
    nest net network neutron new news newspaper next nice nickel
    nicotine night nine no nobody node noise normal north nose nostril
    not note noted nothing now nowhere nucleus number numerator nurse
    nut obedient observation of off offer office officer offspring oil
    old olive omelet on once oncoming one oneself onlooker only onto
    open opera operation opinion opium opposite or orange orchestra
    order ore organ organism organization origin ornament other out
    outburst outcome outcrop outcry outdoor outer outgoing outhouse
    outlaw outlet outlier outline outlook output outside outskirts
    outstretched oval oven over overacting overall overbalancing
    overbearing overcoat overcome overdo overdressed overfull
    overhanging overhead overland overlap overleaf overloud overseas
    overseer overshoe overstatement overtake overtaxed overtime
    overturned overuse overvalued overweight overworking own owner
    oxidation packing pad page pain paint painter painting pair
    pajamas pan paper paradise paraffin paragraph parallel parcel
    parent park part particle parting partner party passage passport
    past paste patent path patience payment peace pedal pen pencil
    pendulum penguin pension people perfect person petal petroleum
    phonograph physical piano picture pig pin pincushion pipe piston
    place plain plan plane plant plaster plate platinum play played
    playing plaything please pleased pleasure plough plow plug pocket
    poetry point pointer pointing poison police policeman polish
    political pollen pool poor population porcelain porter position
    possible post postman postmark postmaster postoffice pot potash
    potato potter powder power practice praise prayer present pressure
    price prick priest prime print printer prison prisoner private
    probability probable process produce producer product profit
    program progress projectile projection promise proof propaganda
    property prose protest proud public pull pulley pump punishment
    pupil purchase pure purpose push put pyramid quack quality
    quantity quarter queen question quick quiet quinine quite quotient
    race radiation radio radium rail rain raining range rat rate ratio
    ray reaction reader reading ready reagent real reason receipt
    receiver reciprocal record rectangle recurring red reference
    referendum reflux regret regular reinforcement relation relative
    religion remark remedy rent repair representative reproduction
    repulsion request residue resistance resolution respect
    responsible rest restaurant result retail revenge reversible
    reward rheumatism rhythm rice rich right rigidity ring rise rival
    river road rock rod roll roller roof room root rot rotation rough
    round rub rubber rude rule ruler rum run runaway rust sac sad safe
    sail sailor salad sale salt same sample sand sardine satisfaction
    saturated saucer saving say scale scarp schist school science
    scissors scratch screen screw sea seal seaman search seat second
    secondhand secret secretary secretion section security sedimentary
    see seed seem selection self selfish send sense sensitivity
    sentence sepal separate serious serum servant service set seven
    sex shade shadow shake shale shame share sharp shave shear sheep
    sheet shelf shell ship shirt shock shocked shocking shoe shore
    short shorthand shoulder show shut side sideboard sidewalk sight
    sign silk sill silver similarity simple since sir sister six
    sixteen size skin skirt skull sky slate sleep sleeve slide slip
    slope slow small smash smell smile smoke smooth snake sneeze snow
    snowing so soap social society sock soft soil soldier solid
    solution solvent some somebody someday somehow someone something
    sometime somewhat somewhere son song sorry sort sound soup south
    space spade spark special specialization specimen speculation
    spirit spit splash sponge spoon sport spot spring square stable
    stage stain stair stalk stamen stamp star start statement station
    statistics steady steam steamer steel stem step stick sticky stiff
    still stimulus stitch stocking stomach stone stop stopper stopping
    store storm story straight strain strange straw stream street
    strength stress stretch stretcher strike string strong structure
    study subject substance substitution subtraction success
    successive such suchlike sucker sudden sugar suggestion sum summer
    sun sunburn sunlight sunshade supply support surface surgeon
    surprise suspension suspicious sweet sweetheart swelling swim
    swing switch sympathetic system table tail tailor take talk
    talking tall tame tap tapioca taste tax taxi tea teacher teaching
    tear telegram telephone ten tendency tent term terrace test
    texture than that the theater then theory there thermometer thick
    thickness thief thimble thin thing third thirteen thirty this
    thorax though thought thousand thread threat three throat through
    thrust thumb thunder ticket tide tie tight till time tin tired
    tissue to toast tobacco today toe together tomorrow tongs tongue
    tonight too tooth top torpedo total touch touching towel tower
    town trade trader tradesman traffic tragedy train trainer training
    transmission transparent transport trap travel tray treatment tree
    triangle trick trouble troubled troubling trousers truck true tube
    tune tunnel turbine turn turning twelve twenty twice twin twist
    two typist ugly umbrella unconformity under underclothing
    undercooked undergo undergrowth undermined undersigned undersized
    understanding understatement undertake undervalued undo unit
    universe university unknown up upkeep uplift upon upright uptake
    use used valency valley value valve vanilla vapor variable
    vascular vegetable velocity verse very vessel vestigial victim
    victory view viewpoint violent violin visa vitamin vodka voice
    volt volume vortex vote waiter waiting walk wall war warm wash
    waste wasted watch water waterfall wave wax way weak weather wedge
    week weekend weight welcome well west wet what whatever wheel when
    whenever where whereas whereby wherever whether which whichever
    while whip whisky whistle white whitewash who whoever wholesale
    why wide widow wife wild will wind window windpipe wine wing
    winter wire wise with within without woman wood woodwork wool word
    work worker workhouse working world worm wound wreck wrist writer
    writing wrong yawn year yearbook yellow yes yesterday you young
    yourself zebra zinc zookeeper zoology""".split()

    mapping = {
        "e": 'english',
        "E": 'gutenberg10k',
        "j": 'naist-jdic-simple',
        "J": 'naist-jdic',
    }

    corpus = {
        "english": MoreBasicEnglish,
        "basicenglish": BasicEnglish
    }

    base_path = None
    @classmethod
    def load_wordlist(self, target, *, diag=None):
        if target in self.mapping:
            target = self.mapping[target]
        if target in self.corpus:
            return self.corpus[target]

        if not self.base_path:
            from pathlib import Path
            self.base_path = Path(sys.modules[self.__module__].__file__).parent / 'corpus'
        fname = str(self.base_path / (target + ".corpus"))

        no_apostroph = False
        fmt = False
        in_header = True
        try:
            with open(fname, 'rb') as f:
                b = f.peek(128)
                if b.startswith(b'#'):
                    if b.startswith(b'#format hinted\n'):
                        fmt = 'hinted'
                    elif b.startswith(b'#format packed\n'):
                        fmt = 'packed'
                    elif b.startswith(b'#format '):
                        raise BadFormatError('Unrecognized wordlist {} in file {}'.format(target, fname))

                if fmt == 'packed':
                    wlist = load_compact_corpus(f)
                else:
                    wlist = set()
                    for l in f:
                        l = l.strip()
                        if l == b'':
                            in_header = False
                            continue
                        if l.startswith(b'#'):
                            if in_header:
                                if l == b"#option no-apostroph":
                                    no_apostroph = True
                            continue

                        in_header = False
                        if fmt:
                            w = l.split(b'\t')
                            if len(w) != 2:
                                raise BadFormatError("invalid line in corpus: " + l)
                            wlist.add((w[0].decode('utf-8'), w[1].decode('utf-8')))
                        else:
                            for word in l.split():
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
            if diag != None:
                diag.append("loaded {} words of corpus as {}".format(len(wlist), target))
            if (len(wlist) == 0):
                raise BadFormatError("empty or bad corpus:" + target)
            self.corpus[target] = wlist
            return wlist
        except OSError as e:
            raise BadFormatError("unknown wordlist {}:\n   Cannot load file {}: {}".format(target, fname, e))

class load_compact_corpus(abcSequence):
    MAGIC = 0x3b9c787 # 7digits
    VERSION = 1
    HEADER = b'#format packed\n'
    HEADER2 = b'#_-_-_-\n'
    MAXSIZE = 104857600

    def __init__(self, f, load_header=True):

        if isinstance(f, str):
            f = open(f, 'rb')
            load_header = True
        elif isinstance(f, io.TextIOBase):
            f = f.buffer
            f.seek(0)
            load_header = True

        size = os.fstat(f.fileno()).st_size
        if size > self.MAXSIZE:
            raise RuntimeError('too large corpus: safety valve triggered')

        if load_header:
            h = f.read(len(self.HEADER))
            if h != self.HEADER:
                raise RuntimeError('bad corpus: header not found')
        else:
            while(f.peek(1)[0] == ord(b'\n')):
                s = f.read(1)

        try:
            s = f.read(48)
            a = s.split(b' ')
            if len(a) < 3 or a[0] != b'#!!PCK!!':
                raise RuntimeError('bad corpus: bad magic line {}'.format(s))

            if int(a[1], 16) != self.MAGIC:
                raise RuntimeError('bad corpus: bad magic {:08x}'.format(int(a[1], 16)))

            if int(a[2], 16) != self.VERSION:
                raise RuntimeError('bad corpus: corpus format version mismatch ({} instead of {})'.format(int(a[2], 16), self.VERSION))

            if len(a) != 6 or a[5] != b'!!\n':
                raise RuntimeError('bad corpus: bad magic line {}'.format(s))

            blen, l = int(a[3], 16), int(a[4], 16)
        except ValueError:
            raise RuntimeError('bad corpus: bad magic line {}'.format(s))

        self.len = l

        tbllen = (l * 2 + 1) * 8

        if blen:
            s = f.read(blen)

        s = f.read(len(self.HEADER2))
        if s != self.HEADER2:
            raise RuntimeError('bad corpus: bad magic line {}', s)

        b = f.read(size - f.tell())
        blen = len(b)
        self.dat = b
        self.tblofs = blen - tbllen
        if self._getidx(0) != self.MAGIC:
            raise RuntimeError('bad corpus: bad index magic {:08x}'.format(self._getidx(0)))

    def __len__(self):
        return self.len

    def __getitem__(self, i):
        return (self._get(i * 2 + 1), self._get(i * 2 + 2))

    def _getidx(self, i):
        o = self.tblofs + i * 8
        return int(self.dat[o : o + 8], 16)
        # int accepts \n

    def _get(self, i):
        o = self._getidx(i)
        o2 = self.dat.index(b'\n', o)
        return self.dat[o:o2].decode('utf-8')

if __name__ == '__main__':
    main()
