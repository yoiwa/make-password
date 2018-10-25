#!/usr/bin/python3
from setuptools import setup, find_packages
import re

def extract_description(fname, pats):
    f = False
    r = ""
    o = []
    for l in open(fname):
        if f:
            if re.search(r, l):
                #print(repr((False,r,l)))
                f = False
                continue
            else:
                o.append(l)
        else:
            for p in pats:
                if re.search(p[0], l):
                    f = True
                    #                    print(repr((True,p[0],l)))
                    r = p[1]
                    if len(p) >= 3 and p[2]:
                        o.append(l)
                    continue
    return "".join(o)

setup(
    name = "make-password",
    version = "1.0",
    author = "Yutaka OIWA",
    author_email = "y.oiwa@aist.go.jp",
    description = "Passphrase generator with corpus support",
    long_description = extract_description("README.md", [(r'^\"', r"## Install", 1)]),
    long_description_content_type = "text/markdown",
    url = "https://github.com/yoiwa/make-password",

    packages = find_packages(),
    license = "Apache Software License",
    keywords = "password passphrase security",
    platforms = ["OS Independent"],
    project_urls = {
        "Source Code": "https://github.com/yoiwa/make-password",
    },

    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Security",
        "Topic :: Utilities",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        ],

    python_requires = ">=3.5",

    include_package_data = True,
    package_data = {
        "*": ["*.corpus"],
    },
    extras_require = {
        "PDF": ["reportlab>=3.5", "qrcode"],
    },

    zip_safe = True,

    #scripts = ["make-password", "make-password-sheet"],
    entry_points = {
        "console_scripts": [
            "make-password = password_generator.password_generator:main",
            "make-password-sheet = password_generator.pdf_generator:main [PDF]",
        ]
    },

)
