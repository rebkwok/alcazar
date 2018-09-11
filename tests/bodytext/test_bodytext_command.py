#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from itertools import chain
from os import path
import re
import subprocess
from tempfile import NamedTemporaryFile
import unittest

# alcazar
from alcazar.utils.compatibility import native_string

#----------------------------------------------------------------------------------------------------------------------------------

_root_path = path.join(path.dirname(__file__))

def compile_test_method(input_encoding, use_stdin, output_encoding, use_stdout, long_form):
    input_file_path = path.join(_root_path, 'mars.%s.html' % (input_encoding or 'UTF-8'))

    def _compose_command_line(output_file):
        yield 'bodytext',
        if not use_stdin:
            yield '--input-file' if long_form else '-i', input_file_path
        if input_encoding:
            yield '--input-encoding', input_encoding
        if not use_stdout:
            yield '--output-file' if long_form else '-o', output_file.name
        if output_encoding:
            yield '--output-encoding', output_encoding       

    def _output_text(output_file):
        output_file.seek(0)
        output_bytes = output_file.read()
        return output_bytes.decode(output_encoding)

    def test_method(self):
        output_file = NamedTemporaryFile()
        child_stdin = open(input_file_path, 'rb') if use_stdin else None
        try:
            subprocess.check_call(
                list(chain.from_iterable(_compose_command_line(output_file))),
                stdin=child_stdin,
                stdout=output_file if use_stdout else None,
            )
            output_text = _output_text(output_file)
        finally:
            output_file.close()
            if child_stdin:
                child_stdin.close()
        self.assertGreater(
            # Should be at least 90% Russian text
            sum(map(len, re.findall(r'[\u0400-\u045F0-9\s\.,]+', output_text))),
            0.9 * len(output_text),
        )

    test_method.__name__ = _method_name(input_encoding, use_stdin, output_encoding, use_stdout, long_form)
    return test_method


def _method_name(input_encoding, use_stdin, output_encoding, use_stdout, long_form):
    return native_string(
        'test_bodytext_from_%s_%s_to_%s_%s%s' % (
            input_encoding or 'default_encoding',
            'stdin' if use_stdin else 'file',
            output_encoding or 'default_encoding',
            'stout' if use_stdout else 'file',
            '_longform_args' if long_form else '',
        ),
    )

#----------------------------------------------------------------------------------------------------------------------------------

BodyTextCommandTests = type(
    native_string('BodyTextCommandTests'),
    (unittest.TestCase,),
    {
        _method_name(input_encoding, use_stdin, output_encoding, use_stdout, long_form):
            compile_test_method(input_encoding, use_stdin, output_encoding, use_stdout, long_form)
        for input_encoding in ('UTF-8', 'Windows-1251')
        for use_stdin in (True, False)
        for output_encoding in ('UTF-8', 'Windows-1251')
        for use_stdout in (True, False)
        for long_form in ([True, False] if use_stdin or use_stdout else [None])
    },
)

#----------------------------------------------------------------------------------------------------------------------------------
