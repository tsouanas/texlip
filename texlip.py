#!/usr/bin/env python
"""
texlitout

Version: 0.92
Author: Thanos Tsouanas <thanos@tsouanas.org>
"""

import sys, os
import re
import time
from optparse import OptionParser

# Parse the options
optparser = OptionParser()
optparser.add_option('-v', '--verbose',
                     help="verbose mode",
                     action="store_true",
                     dest="verbose",
                     default=False)
optparser.add_option('-t', '--tag',
                     help='do not write a "tag" comment as the first line',
                     action="store_true",
                     dest="tag",
                     default=False)
optparser.add_option('-d', '--basedir',
                     help='directory to output files to',
                     type="string",
                     dest="basedir",
                     default=".")
optparser.add_option('-l', '--lang-hier',
                     help="put the files to different directories, according to each file's language",
                     action="store_true",
                     dest="lang_hier",
                     default=False)
optparser.add_option('-T', '--timetag',
                     help='write the date & time tag as the last line',
                     action="store_true",
                     dest="timetag",
                     default=False)
optparser.add_option('-q', '--quiet',
                     help='do not show statistics',
                     action="store_false",
                     dest="stats",
                     default=True)
optparser.add_option('-V', '--version',
                     help="display the version",
                     action="store_true",
                     dest="version",
                     default=False)
(options, args) = optparser.parse_args()

# Initial values
outputs = {}        # holds all output objects
languages = {}      # holds all language objects
output = None
COMMENT_FMT = '''# COMMENT'''
TIME_FMT = "[%T] %a, %d %b %Y"
BASEDIR = options.basedir
rightnow = lambda: time.strftime(TIME_FMT)

# Helper general-purpose functions
def log(s, level=1):
    if options.verbose or level == 0:
        sys.stdout.write(s)
        sys.stdout.flush()

def plural(n):
    if n == 1:
        return ""
    else:
        return "s"

# Version mode
if options.version:
    print "%s, version %s.\nBy %s." % (NAME, VERSION, AUTHOR)
    sys.exit(0)

class Language():
    def __init__(self, name, comment_fmt=COMMENT_FMT):
        self.name = name
        self.comment_fmt = comment_fmt
        # dirs
        if options.lang_hier:
            try:
                os.makedirs('%s/%s' % (BASEDIR, self.name))
            except OSError:
                log("%s/%s already exists; continuing...\n" % (BASEDIR, self.name))
            self.prefix = '%s/' % self.name
        else:
            self.prefix = ''
        # for stats
        self.total_lines = 0
        self.total_files = 0
    def __str__(self):
        return self.name
    def comment(self, comment):
        return self.comment_fmt.replace('COMMENT', 'texlitout: ' + comment)

class Output():
    def __init__(self, name, language):
        self.name = name
        self.lineno = 0
        self.comment_fmt = comment_fmt
        self.language = languages[language]
        self.language.total_files += 1
        self.fullpath = os.path.normpath("%s/%s/%s" % (BASEDIR, self.language.prefix, self.name))
        try:
            os.makedirs(os.path.split(self.fullpath)[0])
        except OSError:
            log("%s/%s already exists; continuing...\n" % (BASEDIR, self.name))
        self.fp = open(self.fullpath, 'w')
    def __str__(self):
        return self.name
    def close(self):
        self.fp.close()
    def writecomment(self, comment):
        self.fp.write("%s\n" % self.language.comment(comment))
    def writetag(self):
        self.writecomment("%s -> %s" % (input, self.name))
    def writedate(self):
        self.writecomment("%s" % rightnow())
    def writeline(self, line):
        if self.lineno == 0 and options.tag:
            self.writetag()
        self.fp.write("%s" % line)
        self.lineno += 1
        self.language.total_lines += 1

try:
    input = args[0]
except IndexError:
    print "Usage: python texlip.py INPUT.TEX"
    sys.exit(1)

tex_fp = file(input)
tex_lines = tex_fp.readlines()
tex_fp.close()

# Main loop:
log("""Running texlip on "%s":\n""" % input, 0)

# create the BASEDIR
try:
    os.makedirs(BASEDIR)
except OSError:
    log("%s already exists; continuing...\n" % BASEDIR)

# process the input, line by line
for line in tex_lines:

    # command?
    command_match = re.match(r'%texlip: (\+|-|\#)(.*)', line)
    if command_match:
        command, arg = command_match.groups()
        if command == '+' and arg not in languages:
            log('Adding language "%s"... ' % arg)
            languages[arg] = Language(arg)
            log('Done!\n')
        elif command == '-' and arg in languages:
            log('Removing language "%s"... ' % arg)
            languages.remove(arg)
            log('Done!\n')
        elif command == '#':
            language, comment_fmt = arg.split('#')
            log('Setting comment format to "%s" for language "%s"... ' % (comment_fmt, language))
            languages[language].comment_fmt = comment_fmt
            log('Done!\n')
        continue

    # end?
    end_match = re.match(r'\\end{(' + '|'.join([re.escape(langname) for langname in languages]) + ')}', line)
    if end_match and output:
        output.writeline('\n')
        output = None
        log("\n")
        continue

    # begin?
    begin_match = re.match(r'\\begin\[(.*)\]{(' + '|'.join([re.escape(langname) for langname in languages]) + ')}', line)
    if begin_match:
        output_name, language = begin_match.groups()
        if output_name not in outputs:
            outputs[output_name] = Output(output_name, language)
        # set the current output to this output object
        output = outputs[output_name]
        log("""[%s, line %d] """ % (output, output.lineno))
    elif output:
        output.writeline(line)
        log(""".""")

# Close fp's.
for output in outputs.values():
    if output.lineno and options.timetag:
        output.writedate()
    output.close()

# Display stats.
if options.stats:
    total_files = 0
    total_lines = 0
    for language in languages.values():
        lang_files = language.total_files
        lang_lines = language.total_lines
        print "%d file%s and %d line%s in %s." % (
            lang_files, plural(lang_files), lang_lines, plural(lang_lines), language
        )
        total_files += lang_files
        total_lines += lang_lines
    print "%d file%s and %d line%s in total." % (
        total_files, plural(total_files), total_lines, plural(total_lines)
    )
