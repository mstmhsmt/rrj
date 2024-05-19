#!/usr/bin/env python3

'''
  ref.py

  Copyright 2024 Chiba Institute of Technology

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

import os

from .common import REFACTORING_LIST
from .common import abbrev

BASE_OPTIONS = '-Declipse.ignoreApp=true -Dosgi.noShutdown=true'

ABBREV_TBL = dict([(abbrev(r), r.replace(' ', '')) for r in REFACTORING_LIST])


def get_ref_abbrev(key):
    a = key.split(' ')[0]
    return a


def get_ref(key):
    a = get_ref_abbrev(key)
    r = ABBREV_TBL[a]
    return r


class Desc(object):
    def __init__(self, offset, length=0, name=None, loc=None):
        self.offset = offset if isinstance(offset, int) else int(offset)
        self.length = length if isinstance(length, int) else int(length)
        self.name = name
        self.loc = loc

    def get_id(self):
        n = f'{self.offset}-{self.name}'
        return n

    def __str__(self):
        s = f'offset={self.offset} length={self.length} name={self.name} loc={self.loc}'
        return s

    def get_options(self, ws_path, proj_path, ref):
        opts = BASE_OPTIONS
        ok = False
        match ref:
            case 'RenameVariable':
                if self.name is not None:
                    opts += f' -Dosgi.instance.area={ws_path}'
                    opts += f' -Drefactoring.name={ref}'
                    opts += f' -Dexpression.offset={self.offset}'
                    opts += f' -Dvariable.name={self.name}'
                    ok = True

        if ok and self.loc is not None:
            opts += f' -Dfile.path={os.path.join(os.path.abspath(proj_path), self.loc)}'

        return opts

    def to_dict(self):
        d = {'offset': self.offset}
        if self.length > 0:
            d['length'] = self.length
        if self.name is not None:
            d['name'] = self.name
        if self.loc is not None:
            d['loc'] = self.loc
        return d

    @staticmethod
    def from_dict(d):
        o = None
        if d is not None:
            offset = int(d.get('offset', None))
            length = int(d.get('length', 0))
            name = d.get('name', None)
            loc = d.get('loc', None)
            o = Desc(offset, length, name, loc)
        return o


class Ref(object):
    def __init__(self, key, desc=None, desc_=None):
        self.key = key
        self.desc = desc
        self.desc_ = desc_

    def get_id(self):
        n = get_ref_abbrev(self.key)
        if self.desc is not None:
            n += f'-{self.desc.get_id()}-{self.desc_.get_id()}'
        return n

    def __str__(self):
        s = f'{self.key}'
        return s

    def has_descs(self):
        return self.desc is not None and self.desc_ is not None

    def get_options(self, ws_path, proj_path):
        ref = get_ref(self.key)
        opts = self.desc.get_options(ws_path, proj_path, ref)
        return opts

    def get_inv_options(self, ws_path, proj_path):
        ref = get_ref(self.key)
        opts = self.desc_.get_options(ws_path, proj_path, ref)
        return opts

    def to_dict(self):
        d = {'key': self.key}
        if self.desc is not None and self.desc_ is not None:
            d['desc'] = self.desc.to_dict()
            d['desc_'] = self.desc_.to_dict()
        return d

    @staticmethod
    def from_dict(d):
        key = d['key']
        desc = Desc.from_dict(d.get('desc', None))
        desc_ = Desc.from_dict(d.get('desc_', None))
        o = Ref(key, desc, desc_)
        return o
