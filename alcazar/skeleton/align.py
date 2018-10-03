#!/usr/bin/env python
# -*- coding: utf-8 -*-

#----------------------------------------------------------------------------------------------------------------------------------
# includes

# 2+3 compat
from __future__ import absolute_import, division, print_function, unicode_literals

# standards
from collections import namedtuple

#----------------------------------------------------------------------------------------------------------------------------------
# data structures

AlignmentStep = namedtuple('AlignmentStep', (
    'operation',
    'item1',
    'item2',
))

AlignmentStep.is_match = property(lambda self: self.operation == 'MATCH')

#----------------------------------------------------------------------------------------------------------------------------------

def align_skeletons(skeleton1, skeleton2):
    text1 = [item.text for item in skeleton1.body]
    text2 = [item.text for item in skeleton2.body]
    m = len(text1) + 1
    n = len(text2) + 1
    matrix = [
        [(None, None) for _ in range(n)]
        for _ in range(m)
    ]
    matrix[0][0] = (0, None)
    for j in range(1, n):
        matrix[0][j] = (
            matrix[0][j-1][0] + len(text2[j-1]),
            'INSERTION',
        )
    for i in range(1, m):
        matrix[i][0] = (
            matrix[i-1][0][0] + len(text1[i-1]),
            'DELETION',
        )
        t1 = text1[i-1]
        l1 = len(t1)
        for j in range(1, n):
            t2 = text2[j-1]
            l2 = len(t2)
            options = [
                (matrix[i-1][j][0] + l1, 'DELETION'),
                (matrix[i][j-1][0] + l2, 'INSERTION'),
            ]
            if t1 == t2:
                options.append((
                    matrix[i-1][j-1][0],
                    'MATCH',
                ))
            elif t1.startswith(t2):
                options.append((
                    matrix[i-1][j-1][0] + (len(t1) - len(t2)),
                    'MATCH_PREFIX',
                ))
            elif t2.startswith(t1):
                options.append((
                    matrix[i-1][j-1][0] + (len(t2) - len(t1)),
                    'MATCH_SUFFIX',
                ))
            matrix[i][j] = min(options)
    return _rewind_matrix(skeleton1, skeleton2, matrix)


def _rewind_matrix(skeleton1, skeleton2, matrix):
    steps = []
    i = len(matrix) - 1
    j = len(matrix[i]) - 1
    while i > 0 or j > 0:
        _score_unused, operation = matrix[i][j]
        if operation in ('MATCH', 'MATCH_PREFIX', 'MATCH_SUFFIX'):
            steps.append(AlignmentStep(operation, skeleton1.body[i-1], skeleton2.body[j-1]))
            i -= 1
            j -= 1
        elif operation == 'DELETION':
            steps.append(AlignmentStep(operation, skeleton1.body[i-1], None))
            i -= 1
        elif operation == 'INSERTION':
            steps.append(AlignmentStep(operation, None, skeleton2.body[j-1]))
            j -= 1
        else:
            raise ValueError(repr(operation))
    steps.reverse()
    return steps

#----------------------------------------------------------------------------------------------------------------------------------
