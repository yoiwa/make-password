#!/usr/bin/python3
import sys
import time
import tkinter as tk
import tkinter.ttk as ttk
#from tkinter import ttk
from tkinter import font
from collections import OrderedDict

if '.' not in __name__:
    import password_generator
else:
    from . import password_generator

passwordtypes = OrderedDict([
    ('Custom...', None),
    ('Japanese 37k words (naist-jdic-simple)', 'j'),
    ('Japanese 130k words (naist-jdic)', 'J'),
    ('English 10k words (Gutenberg)', 'E'),
    ('English 2k words (Basic English)', 'e'),
    ('digits', 'd'),
    ('lowercase alphabets + digits', 'a'),
    ('alphabets + digits', 'A'),
    ('alphabets, digits and symbols', 's'),
    ('alphabets + digits, in 4-character block', 'A4'),
    ('digits in 4-character block', 'd4'),
    ('For iOS inputs (10 lowercases + digits)', 'l10-d'),
    ('one or more capitals, lowers, and digits', '{A1a1d1}'),
    ('one or more capitals, lowers, digits and symbols', '{A1a1d1s1}'),
])

custom_passwordtype_index = list(passwordtypes.keys()).index('Custom...')

separators = OrderedDict([
    ('default', ''),
    ('space', ' '),
    ('-', '-'),
    ('.', '.'),
    (',', ','),
    ('/', '/'),
    ('nothing', '""'),
])

complexities = OrderedDict([
    ('32 bit', ':32'),
    ('48 bit', ':48'),
    ('64 bit', ':64'),
    ('80 bit', ':80'),
    ('100 bit', ':100'),
    ('112 bit', ':112'),
    ('128 bit', ':128'),
    ('160 bit', ':160'),
    ('224 bit', ':224'),
    ('256 bit', ':256'),
    ('384 bit', ':384'),
    ('512 bit', ':512'),
    ('4 words/chars', '4'),
    ('6 words/chars', '6'),
    ('8 words/chars', '8'),
    ('10 words/chars', '10'),
    ('12 words/chars', '12'),
    ('16 words/chars', '16'),
    ('24 words/chars', '24'),
    ('32 words/chars', '32'),
])

class CopyableText(ttk.Entry):
    def __init__(self, master, *args, text="", **kwargs):
        v = tk.StringVar()
        v.set(text)
        super().__init__(master, *args, textvariable=v, state="readonly", **kwargs)
        self.var = v
        self.bind("<FocusIn>", self.callback)

    def set(self, s):
        self.var.set(s)

    def callback(self, event):
        self.selection_range(0, tk.END)

class CustomFrame(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.setup_styles()
        self.create_widgets()
        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=5)
        self.grid(row=0, column=0)

    _style_initialized = False
    @classmethod
    def setup_styles(self):
        if self._style_initialized:
            return
        self.bigfont = font.Font(size=16, weight="bold")
        self.smallfont = font.Font(size=12, weight="bold")

        self.style = style = ttk.Style()

class ComboChooser(ttk.Combobox):
    def __init__(self, *args, command=None, values=None, default=None, **kwargs):
        if isinstance(values, OrderedDict):
            v = values
            l = list(values.keys())
        elif isinstance(values, dict):
            l = sorted(list(values.keys()))
            v = OrderedDict([(k, values[k]) for k in l])
        elif isinstance(values, list):
            l = values
            v = OrderedDict([(k, k) for k in l])
        else:
            raise ValueError
        r = {v[k]: k for k in v}
        l = list(values.keys())
        super().__init__(*args, state='readonly', values=l, height=len(l), **kwargs)
        self.__values = v
        self.__revvalues = r
        self.__keys = l
        if default:
            self.current(default)
        if command:
            self.bind('<<ComboboxSelected>>', command)

    def current(self, v):
        if v in self.__keys:
            v = self.__keys.index(v)
        elif v in self.__revvalues:
            v = self.__keys.index(self.__revvalues[v])
        super().current(v)

    def get(self):
        return self.__values[super().get()]

class ListUI(CustomFrame):
    def create_widgets(self):
        t = self.stylelabel = ttk.Label(self, text="-")
        t.grid(row=0, column=0, columnspan=3, sticky=tk.W)

        widrows = []

        for i in range(10):
            ttk.Label(self, text=str(i + 1)).grid(row=i+1, column=0)
            pw = CopyableText(self, text="-", font=self.bigfont)
            pw.grid(row=i+1, column=1)
            hint = ttk.Label(self, text="-")
            hint.grid(row=i+1, column=2)
            widrows.append((pw, hint))

        self.widrows = widrows

    def update_data(self, diag_string, dat, diag):
        for i in range(10):
            self.widrows[i][0].set(dat[i][0])
            self.widrows[i][1]['text'] = dat[i][1]
        self.stylelabel['text'] = diag_string

class BulkUI(CustomFrame):
    def create_widgets(self):
        t = self.stylelabel = ttk.Label(self, text="-")
        t.grid(row=0, column=0, sticky=tk.W)

        t = tk.Button(self, text="Add more",
                      command=self.generate_more)
        t.grid(row=1, column=0, sticky=tk.W)

        t = self.bulktext = tk.Text(self)
        t.grid(row=2, column=0, sticky=tk.W)

    def update_data(self, diag_string, dat, diag):
        self.bulktext.delete('1.0', 'end')
        self.bulktext.edit_reset()

        for d in dat:
            self.bulktext.insert('end', d[0] + "\n", [])

        self.stylelabel['text'] = diag_string

    def generate_more(self, *args):
        self.master.add_more_passphrases()

class ConfigUI(CustomFrame):
    def create_widgets(self):
        ttk.Label(self, text="Passphrase type:").grid(row=0, column=0)

        t = self.passwordtype = ComboChooser(self, values=passwordtypes, width=30,
                                       default='j', command=self.passwordtypechanged)
        t.grid(row=0, column=1, sticky=('W',))

        ttk.Label(self, text="separators:").grid(row=1, column=0)

        t = self.separators = ComboChooser(self, values=separators,
                                           default='-', command=self.passwordtypechanged)
        t.grid(row=1, column=1, sticky=('W',))

        ttk.Label(self, text="password complexity:").grid(row=2, column=0)

        t = self.complexities = ComboChooser(self, values=complexities,
                                             default=':100', command=self.passwordtypechanged)
        t.grid(row=2, column=1, sticky=('W',))

        ttk.Label(self, text="custom spec:").grid(row=3, column=0)

        t = self.spec = ttk.Entry(self)
        t.grid(row=3, column=1, sticky=('W',))
        t.bind('<KeyRelease>', self.spec_inputed)

        f = tk.Frame(self)
        ib1 = tk.Button(f, text="Generate", font=self.smallfont,
                      command=self.generate_pressed)
        ib1.pack(side = 'left')

        f.grid(row=4, column=0, sticky=('W',))
        self.spec_update()

    def generate_pressed(self):
        spec = self.spec.get()
        self.master.generate_passphrases(spec)

    def compute_spec(self):
        type_value = self.passwordtype.get()
        if (type_value is None):
            return None
        sep_value = self.separators.get()
        cpx_value = self.complexities.get()
        if cpx_value[0] != ':' and type_value[-1] in "0123456789":
            spec = (sep_value + type_value) * int(cpx_value)
        else:
            spec = sep_value + type_value + cpx_value
        return spec

    def spec_update(self):
        spec = self.compute_spec()
        if spec:
            self.spec.delete(0, tk.END)
            self.spec.insert(0, spec)

    def spec_inputed(self, *event):
        self.passwordtype.current(custom_passwordtype_index)

    def passwordtypechanged(self, *event):
        self.spec_update()

class PasswordApp(ttk.Notebook):
    def __init__(self, master, name="a"):
        super().__init__(master, name=name)
        self.master = master
        self.current_spec = self.current_dat = None
        self.config_ui = ConfigUI(master=self, name="config")
        self.list_ui = ListUI(master=self, name="list")
        self.bulk_ui = BulkUI(master=self, name="bulk")
        self.add(self.config_ui, text="Configure")
        self.add(self.list_ui, text="Passphrases")
        self.add(self.bulk_ui, text="Bulk Copy")
        self.pack()

    def generate_passphrases(self, spec):
        self.current_spec = spec
        dat, diag = password_generator.generate(spec, 10)
        self.current_dat = (dat, diag)

        diag_string = self.diag_string = "Password spec = \"{}\", entropy = {:.3f} bits".format(spec, diag['entropy'])

        self.list_ui.update_data(diag_string, dat, diag)
        self.bulk_ui.update_data(diag_string, dat, diag)

        self.select(".a.list")

    def add_more_passphrases(self):
        if self.current_spec is None:
            return
        dat, diag = self.current_dat
        dat2, diag2 = password_generator.generate(self.current_spec, 10)

        dat[0] += dat2[0]
        dat[1] += dat2[1]
        diag['passwords'] += diag2['passwords']
        diag['elements'] += diag2['elements']

        self.current_dat = (dat, diag)
        self.bulk_ui.update_data(self.diag_string, dat, diag)

def main():
    root = tk.Tk()
    app = PasswordApp(master=root, name="a")
    root.mainloop()

if __name__ == '__main__':
    main()

