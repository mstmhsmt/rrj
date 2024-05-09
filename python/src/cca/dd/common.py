#!/usr/bin/env python3

'''
  common.py

  Copyright 2022-2024 Chiba Institute of Technology

  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
'''

__author__ = 'Masatomo Hashimoto <m.hashimoto@stair.center>'

import re

from .conf import VAR_DIR, FACT_DIR, LOG_DIR, FB_DIR
from .conf import ONT_DIR, WORK_DIR, REFACT_DIR
from .conf import VIRTUOSO_PW, VIRTUOSO_PORT

RENAME_METHOD = 'Rename Method'
RENAME_PARAMETER = 'Rename Parameter'
RENAME_VARIABLE = 'Rename Variable'
RENAME_ATTRIBUTE = 'Rename Attribute'
CHANGE_RETURN_TYPE = 'Change Return Type'
CHANGE_PARAMETER_TYPE = 'Change Parameter Type'
CHANGE_VARIABLE_TYPE = 'Change Variable Type'
CHANGE_ATTRIBUTE_TYPE = 'Change Attribute Type'

REFACTORING_LIST = [
    RENAME_METHOD,
    RENAME_PARAMETER,
    RENAME_VARIABLE,
    RENAME_ATTRIBUTE,
    CHANGE_RETURN_TYPE,
    CHANGE_PARAMETER_TYPE,
    CHANGE_VARIABLE_TYPE,
    CHANGE_ATTRIBUTE_TYPE,
]

SIG_TBL = {
    'boolean': 'Z',
    'byte': 'B',
    'char': 'C',
    'short': 'S',
    'int': 'I',
    'long': 'J',
    'float': 'F',
    'double': 'D',
    'void': 'V',
}

ARRAY_PAT = re.compile(r'^(?P<base>[^\[]+)(?P<dims>(\[\])+)$')
TY_PARAM_PAT = re.compile(r'^(?P<base>[^<]+)(?P<tparams><.+>)(?P<dims>(\[.*\])?)$')


def erase_ty_params(s):
    level = 0
    s_ = ''
    skip_flag = False
    for c in s:
        if c == '<':
            level += 1
            skip_flag = True
        elif c == '>':
            level -= 1
            if level == 0:
                skip_flag = False
        elif not skip_flag:
            s_ += c
    return s_


def get_type_sig(ty):
    if ty is None:
        return 'V'

    dims = 0
    _ty = ty

    m = TY_PARAM_PAT.match(ty)
    if m:
        _ty = TY_PARAM_PAT.sub(r'\g<base>\g<dims>', _ty)

    m = ARRAY_PAT.match(ty)
    if m:
        _ty = ARRAY_PAT.sub(r'\g<base>', _ty)
        dims = int(len(m.group('dims')) / 2)

    prefix = ''
    if dims:
        prefix = '[' * dims
    try:
        _s = SIG_TBL[_ty]
    except KeyError:
        _ty = _ty.split('.')[-1]
        _s = f'L{_ty};'

    s = prefix + _s

    return s


def abbrev(ref):
    s = ''.join([x[0] for x in ref.split(' ')])
    return s


if __name__ == '__main__':
    print(f'VAR_DIR: {VAR_DIR}')
    print(f'fACT_DIR: {FACT_DIR}')
    print(f'LOG_DIR: {LOG_DIR}')
    print(f'FB_DIR: {FB_DIR}')
    print(f'ONT_DIR: {ONT_DIR}')
    print(f'WORK_DIR: {WORK_DIR}')
    print(f'REFACT_DIR: {REFACT_DIR}')
    print(f'VIRTUOSO_PW: {VIRTUOSO_PW}')
    print(f'VIRTUOSO_PORT: {VIRTUOSO_PORT}')
