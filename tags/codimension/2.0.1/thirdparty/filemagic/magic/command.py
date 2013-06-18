"""Command line applicatoin for filemagic.

Simple application similar to the Unix file command.
"""
from optparse import OptionParser
import json
import os
import sys

from magic.flags import MAGIC_NONE, MAGIC_MIME_TYPE, MAGIC_MIME_ENCODING
from magic.identify import Magic

try:
    from collections import OrderedDict as odict
except ImportError:
    odict = dict

SEPARATORS = (', ', ': ')


class Identifiers(object):
    "Aggregate identifier for textual, mimetype and encoding identificaiton"

    def __init__(self, path):
        "Initialise all identifiers to None"
        self.path = None if not path else path.split(':')
        self.textual = None
        self.mimetype = None
        self.encoding = None

    def __enter__(self):
        "__enter__() -> self."
        self.textual = Magic(paths=self.path, flags=MAGIC_NONE)
        self.mimetype = Magic(paths=self.path, flags=MAGIC_MIME_TYPE)
        self.encoding = Magic(paths=self.path, flags=MAGIC_MIME_ENCODING)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        "__exit__(*excinfo) -> None.  Closes libmagic resources."
        if self.textual is not None:
            self.textual.close()
        if self.mimetype is not None:
            self.mimetype.close()
        if self.encoding is not None:
            self.encoding.close()

    def id_filename(self, filename):
        identity = odict()
        identity['textual'] = self.textual.id_filename(filename)
        identity['mimetype'] = self.mimetype.id_filename(filename)
        identity['encoding'] = self.encoding.id_filename(filename)
        return identity


def parse_command_line(arguments):
    "Parse command line arguments"
    usage = "usage: python -m magic [options] file ..."
    parser = OptionParser(usage=usage)
    parser.add_option("-m", "--magic", dest="paths",
            help="A colon separated list of magic files to use")
    parser.add_option("--json", action="store_true", default=False,
            help="Format output in JSON")
    return parser.parse_args(arguments)


def print_json(filenames, results, fdesc=sys.stdout):
    "Print JSON formated results to file like object"
    json.dump(results, fdesc, indent=2, separators=SEPARATORS)
    fdesc.write(os.linesep)


def print_text(filenames, results, fdesc=sys.stdout):
    "Print human readable results to file like object"
    template = "{filename}\n\t{textual}\n\t{mimetype}\n\t{encoding}\n"
    for name in filenames:
        result = results[name]
        fdesc.write(template.format(filename=name, **result))


def run(arguments=None):
    "Main loop for file like command using filemagic"
    arguments = arguments if arguments is None else sys.argv
    options, filenames = parse_command_line(arguments)
    results = odict()
    with Identifiers(options.paths) as identify:
        for name in filenames:
            results[name] = identify.id_filename(name)
    if options.json:
        print_json(filenames, results)
    else:
        print_text(filenames, results)


if __name__ == "__main__":
    run()
