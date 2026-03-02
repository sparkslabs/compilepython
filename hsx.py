#!/usr/bin/python

#
# HyperText, Templating with XML Like evaluation
# Takes a directory of fragments named:
#
#      dirname/Tagname.extension
#
# Creates a custom parser based on Tagnames
# Parses a file using that file.
# Replaces <Tagname /> (and parameterised as: <Tagname key=Value key=Value .../>
#  with the contents of dirname/Tagname.extension
# If key/Value pairs are provided, these are injected into the contents first
# The injection is {args.key} gets replaced with Value
#
# If the tagname is used a block tag <Tagname> Some text contents </Tagname>
#
# Then the text "Some text contents" gets injected into the file
# "Tagname.extension" before inclusion by replacing the string {arg.__text__}
#
# This allows it to obviously be used with HTML, but it could be also used with
# css, javascript, markdown or many other content types.
#
# This is however strictly a macro processor, NOT a generic templating engine,
# since it does not have loops, conditionals, iteration over data etc.
#
# It is however, very lightweight and currently single pass
#

import os
import re
import math
from collections import defaultdict

def slurp(filename):
    with open(filename) as f:
        return f.read()

def store(filename, what, mode="w"):
    with open(filename, mode) as f:
        return f.write(what)

def files(directory):
    for entry in os.listdir(directory):
        if os.path.isfile(os.path.join(directory,entry)):
            yield directory, entry

def tag_sources(directory):
    for entry in files(directory):
        path, name = entry
        if name.endswith(TAG_EXTENSION):
            tag = name[:-len(TAG_EXTENSION)] # Remove extension
            yield path, tag, name

def mkSimpleTagPattern(tags):
    p = f'<({"|".join(tags)}) ( *[a-zA-Z_0-9]*="[^"]*")* */>'
    return p

def mkOpenTagPattern(tags):
    p = f'<({"|".join(tags)})( +[a-zA-Z_0-9]*="[^"]*")* *>'
    return p

def mkCloseTagPattern(tags):
    p = f'</({"|".join(tags)}) *>'
    return p

def parse_attrs(attr_text):
    # We know the text provided matches the following pattern:
    #    f'( *[a-zA-Z_0-9]*="[^"]*")'

    # Attr values may contain spaces and equals signs, so we have do a consume loop
    attr_p = r'^[a-zA-Z_0-9]+="[^"]*"'
    attr_re = re.compile(attr_p)
    attrs = {}
    while attr_text:
        m = attr_re.search(attr_text)
        if m:
            this_attr = attr_text[m.start():m.end()]  # Extract the first attr/value pair
            attr_text = attr_text[m.end():].strip()   # Remove it

            attr = this_attr[:this_attr.find("=")]    # Attribute name is before the equals
            value = this_attr[this_attr.find("=")+1:] # Attribute name is after the equals in quotes
            value = value[1:-1] #  Remove quotes

            attrs[attr] =  value

    return attrs

def parse_tag(raw_tag_text, block=False):
    # We know the text provided matches the following pattern if block is false:
    #    f'<({"|".join(tags)}) ( *[a-zA-Z_0-9]*="[^"]*")* */>'
    #
    # It also have this almost identical one if block is True:
    #   p = f'<({"|".join(tags)})( +[a-zA-Z_0-9]*="[^"]*")* *>'
    # So we combine the parsing here

    end_trim = -2
    if block:
        end_trim = -1
    raw_tag_text = raw_tag_text[1:end_trim]
    m = re.search(" ", raw_tag_text)
    if m:
        tag = raw_tag_text[:m.start()]
        rest = raw_tag_text[m.end():].strip()
        args = parse_attrs(rest)
    else:
        tag = raw_tag_text.strip()
        args = {}
    return tag, args

def find_file(tag, tag_defs):
    # We know that the tag must be in tag_defs because tag is derived from tag_defs
    candidates = tag_defs[tag]
    if len(candidates) == 1:
        dirname, filename = candidates[0]
        return os.path.join(dirname, filename)
    raise Exception("Broken Code")

def simple_stream_parse(tags_regexes, text):
    # "simple" : re.compile(simple_tag_pattern),
    # "open" : re.compile(open_tag_pattern),
    # "close" : re.compile(close_tag_pattern)
    tags_regex = tags_regexes["simple"]
    while text:
        simple_start = open_start = close_start = math.inf
        match = None

        # print("OK")
        # We might have any one of these next. We want to check for all three,
        # and use the earliest match
        simple_match = tags_regexes["simple"].search(text)
        open_match = tags_regexes["open"].search(text)
        # print("OPEN MATCH:", tags_regexes["open"], open_match)
        close_match = tags_regexes["close"].search(text)

        if simple_match: simple_start = simple_match.start()
        if open_match: open_start = open_match.start()
        if close_match: close_start = close_match.start()

        # To make debugging clearer/simpler
        simple_first = (simple_start < open_start) and (simple_start < close_start)
        open_first =   (open_start < simple_start) and (open_start < close_start)
        close_first =  (close_start < open_start) and (close_start < simple_start)

        if simple_match and simple_first:
            match = simple_match
            match_type = "simple"

        elif open_match and open_first:
            match = open_match
            match_type = "open"

        elif close_match and close_first:
            match = close_match
            match_type = "close"

        if match:
            pre_tag_text = text[:match.start()]
            tag_text = text[match.start():match.end()]

            yield ("text", pre_tag_text)
            yield (("tag", match_type), tag_text)

            remaining_text = text[match.end():]
            text = remaining_text

        else:
            # We're after the last tag, so just yield that
            yield ("text", text)
            text = ""

def evaluate_block_tag(tag, args):
    # Find the file to insert into
    replacement_file = find_file(tag, tag_defs)
    # print(f"File-- {tag} {replacement_file}")

    # Grab the file text
    t = slurp(replacement_file)

    # Insert the arguments if they exist
    for arg in args:
        t = t.replace("{args." + arg + "}", args[arg])

    t = stream_Evaluate(t, tag_regexes)

    return t

def evaluate_simple_tag(ev_value):
    # Extract the tag and arguments
    tag, args = parse_tag(ev_value)

    t = evaluate_block_tag(tag, args)
    return t

def get_tagdefs(source_dir):
    tag_defs = defaultdict(list)

    for entry in tag_sources(source_dir):
        domain, tag, tagsource = entry
        # print("domain, tag, tagsource")
        # print(f"{tag, domain, tagsource}")
        tag_defs[tag].append( (domain, tagsource) )
    return tag_defs

def makeTagParser(tag_defs):
    # Make Tag Parser
    simple_tag_pattern = mkSimpleTagPattern(tag_defs.keys())
    open_tag_pattern = mkOpenTagPattern(tag_defs.keys())
    close_tag_pattern = mkCloseTagPattern(tag_defs.keys())

    tag_regexes = {
        "simple" : re.compile(simple_tag_pattern),
        "open" : re.compile(open_tag_pattern),
        "close" : re.compile(close_tag_pattern)
    }
    return tag_regexes

def stream_Evaluate(text, tag_regexes):
    global stream_evaluate_depth
    stream_evaluate_depth += 1
    if stream_evaluate_depth > 30:
        print("Warning, deep recursion for stream_Evaluate in processing - consider refactoring")
    if stream_evaluate_depth > 50:
        raise Exception("Recursion limit for stream_Evaluate exceeded, refactor your content")
    # Basic Stream Parser
    result = []
    result_stack = []
    block_tag_stack = []
    for event in simple_stream_parse(tag_regexes, text):
        ev_type, ev_value = event
        # print(ev_type, ev_value) 
        if ev_type == ("tag", "simple"):
            replacement_text = evaluate_simple_tag(ev_value)
            result.append(replacement_text)

        elif ev_type == ("tag", "open"):
            open_tag, args = parse_tag(ev_value, block=True)
            # print(f"OPEN TAG: {open_tag} attrs: {args}")
            block_tag_stack.append( (open_tag, args, result) )
            result = []  # New local result

        elif ev_type == ("tag", "close"):
            close_tag = ev_value[2:-1].strip()  # This is guaranteed safe, or else we can't reach here
            (open_tag, args, enclosing_result) = block_tag_stack.pop()
            if open_tag != close_tag:
                raise Exception(f"Structural error. Saw {close_tag} close tag but was expecting a matching {open_tag}")
            # print("CLOSING TAG", close_tag)
            block_text = "".join(result)
            args["__text__"] = block_text # Inject the block value into args

            result = enclosing_result  # Move back to the outer layer
            replacement_text = evaluate_block_tag(close_tag, args)
            result.append(replacement_text)

        else:
            result.append(ev_value)

    stream_evaluate_depth -= 1
    return "".join(result)

if __name__ == "__main__":
    import sys

    TAG_EXTENSION = ".hsx"
    base_dir = "frags"
    source_file = "markdown.hsx"
    destfile = None

    # Fragile options handling
    if "--dir" in sys.argv:
        where = sys.argv.index("--dir")
        base_dir = sys.argv[where+1]

    if "--extension" in sys.argv:
        where = sys.argv.index("--extension")
        TAG_EXTENSION = sys.argv[where+1]

    if "--destfile" in sys.argv:
        where = sys.argv.index("--destfile")
        destfile = sys.argv[where+1]

    # TAG_EXTENSION = ".hsx"
    tag_defs = get_tagdefs(base_dir)
    tag_regexes = makeTagParser(tag_defs)

    text = slurp(source_file)
    stream_evaluate_depth = 0
    evaluated = stream_Evaluate(text, tag_regexes)
    if destfile:
        store(destfile, evaluated)
    else:
        print(evaluated)
