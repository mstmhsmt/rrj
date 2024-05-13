#!/usr/bin/env python3

'''
  ref_keys.py

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
import json
import logging

from cca.ccautil.ns import FB_NS, NS_TBL
from cca.ccautil import sparql
from cca.ccautil.sparql import get_localname
from .common import VIRTUOSO_PW, VIRTUOSO_PORT, abbrev, SIG_TBL
from .common import RENAME_METHOD, RENAME_PARAMETER, RENAME_VARIABLE, RENAME_ATTRIBUTE
from .common import CHANGE_RETURN_TYPE
from .common import CHANGE_PARAMETER_TYPE, CHANGE_VARIABLE_TYPE, CHANGE_ATTRIBUTE_TYPE
from .common import get_type_sig as _get_type_sig
from .ref_key_queries import QUERY_TBL, DTOR_QUERY
from .ref import Ref, Desc

logger = logging.getLogger()


VER_PAT = re.compile(r'^(?P<cid>[0-9a-f]+)-before$')
MSIG_PAT = re.compile(r'^\((?P<ptys>(.+)?)\)(?P<rty>.+)$')
TYSIG_PAT = re.compile(r'^L(?P<ty>.+);$')

BASIC_TYSIGS = set(SIG_TBL.values())
REV_SIG_TBL = {}
for k, v in SIG_TBL.items():
    REV_SIG_TBL[v] = k

MAX_VARS = 4


def get_cid(ver):
    cid = VER_PAT.sub(r'\g<cid>', get_localname(ver))
    return cid


def get_uqn(fqn):
    uqn = fqn
    if fqn:
        uqn = fqn.split('.')[-1]
    return uqn


def get_type_sig(ty):
    return _get_type_sig(get_uqn(ty.replace('$', '.')))


def ty_of_tysig(tysig):
    _tysig = tysig.lstrip('[')
    dims = len(tysig) - len(_tysig)
    ty = _tysig
    m = TYSIG_PAT.match(_tysig)
    if m:
        ty = m.group('ty')
    else:
        ty = REV_SIG_TBL[_tysig]
    ty += '[]' * dims
    return ty


def pad(x):
    res = x
    xlen = len(x)
    if xlen < MAX_VARS + 1:
        res = list(x) + ([''] * (MAX_VARS + 1 - xlen))
    return res


def setup_mname(mname, cfqn):
    mname_ = mname
    if mname_ == '<init>':
        mname_ = get_uqn(cfqn)
    return mname_


def split_tysig_seq(tysig_seq):
    if not tysig_seq:
        return []
    tysig_list = []
    tysig = ''
    entry_flag = False
    for c in tysig_seq:
        if c == 'L':
            tysig += c
            entry_flag = True
        elif c == ';':
            tysig += c
            tysig_list.append(tysig)
            tysig = ''
            entry_flag = False
        elif entry_flag or c == '[':
            tysig += c
        elif c in BASIC_TYSIGS:
            tysig_list.append(tysig+c)
            tysig = ''
        else:
            logger.warning(f'malformed tysig_seq: {tysig_seq}')
            break
    return tysig_list


def reduce_msig(msig):
    msig_ = msig
    m = MSIG_PAT.match(msig)
    if m:
        pty_list = split_tysig_seq(m.group('ptys'))
        ptys = ''.join([get_type_sig(ty_of_tysig(pty)) for pty in pty_list])
        rty = get_type_sig(ty_of_tysig(m.group('rty').replace('$', '.')))
        msig_ = f'({ptys}){rty}'
    return msig_


def get_dims(row):
    x = 0
    try:
        x = int(row['dims'])
    except Exception:
        pass
    return x


def get_dims_(row):
    x = 0
    try:
        x = int(row['dims_'])
    except Exception:
        pass
    return x


def proc_DTOR(row):
    vname = row['vname']
    dims = get_dims(row)
    vty = '[' * dims + get_type_sig(row['vtyname'])
    cfqn = row['cfqn'].replace('$', '.')
    mname = setup_mname(row['mname'], cfqn)
    msig = reduce_msig(row['msig'])
    ver = row['ver']
    cid = get_localname(ver)
    key = f'{vname}:{vty}'
    meth = f'{mname}{msig}'
    loc = row.get('loc', None)
    offset = row.get('offset', None)
    length = row.get('length', None)

    d = {
        'meth': meth,
        'class': cfqn,
        'loc': loc,
        'offset': offset,
        'length': length,
    }

    return cid, key, d


def proc_RM(row):
    cfqn = row['cfqn'].replace('$', '.')
    abst = ''
    # if row['abst'] == 'true':
    #     abst = 'abstract '
    mname = setup_mname(row['mname'], cfqn)
    msig = reduce_msig(row['msig'])
    cfqn_ = row['cfqn_'].replace('$', '.')
    abst_ = ''
    # if row['abst_'] == 'true':
    #     abst_ = 'abstract '
    mname_ = setup_mname(row['mname_'], cfqn_)
    msig_ = reduce_msig(row['msig_'])
    ver = row['ver']
    key = f'RM {abst}{mname}{msig}->{abst_}{mname_}{msig_} {cfqn_}'
    cid = get_cid(ver)
    return cid, Ref(key)


def proc_RP(row):
    pname = row['pname']
    dims = get_dims(row)
    pty = '[' * dims + get_type_sig(row['ptyname'])
    pname_ = row['pname_']
    dims_ = get_dims_(row)
    pty_ = '[' * dims_ + get_type_sig(row['ptyname_'])
    cfqn_ = row['cfqn_'].replace('$', '.')
    abst_ = ''
    # if row['abst_'] == 'true':
    #     abst_ = 'abstract '
    mname_ = setup_mname(row['mname_'], cfqn_)
    msig_ = reduce_msig(row['msig_'])
    ver = row['ver']
    key = f'RP {pname}:{pty}->{pname_}:{pty_} {abst_}{mname_}{msig_} {cfqn_}'
    cid = get_cid(ver)
    return cid, Ref(key)


def proc_RV(row):
    vname = row['vname']
    dims = get_dims(row)
    vty = '[' * dims + get_type_sig(row['vtyname'])
    vname_ = row['vname_']
    dims_ = get_dims_(row)
    vty_ = '[' * dims_ + get_type_sig(row['vtyname_'])
    cfqn_ = row['cfqn_'].replace('$', '.')
    mname_ = setup_mname(row['mname_'], cfqn_)
    msig_ = reduce_msig(row['msig_'])
    ver = row['ver']
    key = f'RV {vname}:{vty}->{vname_}:{vty_} {mname_}{msig_} {cfqn_}'
    cid = get_cid(ver)

    desc = None
    desc_ = None
    offset = row.get('offset', None)
    offset_ = row.get('offset_', None)
    length = row.get('length', None)
    length_ = row.get('length_', None)
    loc = row.get('loc', None)
    loc_ = row.get('loc_', None)
    if all([x is not None for x in [offset, length, loc, offset_, length_, loc_]]):
        desc = Desc(offset, length, vname_, loc)
        desc_ = Desc(offset_, length_, vname, loc_)

    return cid, Ref(key, desc, desc_)


def proc_RA(row):
    vname = row['vname']
    dims = get_dims(row)
    vty = '[' * dims + get_type_sig(row['vtyname'])
    vname_ = row['vname_']
    dims_ = get_dims_(row)
    vty_ = '[' * dims_ + get_type_sig(row['vtyname_'])
    cfqn_ = row['cfqn_'].replace('$', '.')
    ver = row['ver']
    key = f'RA {vname}:{vty}->{vname_}:{vty_} {cfqn_}'
    cid = get_cid(ver)
    return cid, Ref(key)


def proc_CRT(row):
    dims = get_dims(row)
    rty = '[' * dims + get_type_sig(row['rtyname'])
    dims_ = get_dims_(row)
    rty_ = '[' * dims_ + get_type_sig(row['rtyname_'])
    cfqn_ = row['cfqn_'].replace('$', '.')
    abst_ = ''
    # if row['abst_'] == 'true':
    #     abst_ = 'abstract '
    mname_ = setup_mname(row['mname_'], cfqn_)
    msig_ = reduce_msig(row['msig_'])
    ver = row['ver']
    key = f'CRT {rty}->{rty_} {abst_}{mname_}{msig_} {cfqn_}'
    cid = get_cid(ver)
    return cid, Ref(key)


def proc_CPT(row):
    pname = row['pname']
    dims = get_dims(row)
    pty = '[' * dims + get_type_sig(row['ptyname'])
    pname_ = row['pname_']
    dims_ = get_dims_(row)
    pty_ = '[' * dims_ + get_type_sig(row['ptyname_'])
    cfqn_ = row['cfqn_'].replace('$', '.')
    abst_ = ''
    # if row['abst_'] == 'true':
    #     abst_ = 'abstract '
    mname_ = setup_mname(row['mname_'], cfqn_)
    msig_ = reduce_msig(row['msig_'])
    ver = row['ver']
    key = f'CPT {pname}:{pty}->{pname_}:{pty_} {abst_}{mname_}{msig_} {cfqn_}'
    cid = get_cid(ver)
    return cid, Ref(key)


def proc_CVT(row):
    vname = row['vname']
    dims = get_dims(row)
    vty = '[' * dims + get_type_sig(row['vtyname'])
    vname_ = row['vname_']
    dims_ = get_dims_(row)
    vty_ = '[' * dims_ + get_type_sig(row['vtyname_'])
    cfqn_ = row['cfqn_'].replace('$', '.')
    mname_ = setup_mname(row['mname_'], cfqn_)
    msig_ = reduce_msig(row['msig_'])
    ver = row['ver']
    key = f'CVT {vname}:{vty}->{vname_}:{vty_} {mname_}{msig_} {cfqn_}'
    cid = get_cid(ver)
    return cid, Ref(key)


def proc_CAT(row):
    vname = row['vname']
    dims = get_dims(row)
    vty = '[' * dims + get_type_sig(row['vtyname'])
    vname_ = row['vname_']
    dims_ = get_dims_(row)
    vty_ = '[' * dims_ + get_type_sig(row['vtyname_'])
    cfqn_ = row['cfqn_'].replace('$', '.')
    ver = row['ver']
    key = f'CAT {vname}:{vty}->{vname_}:{vty_} {cfqn_}'
    cid = get_cid(ver)
    return cid, Ref(key)


PROC_TBL = {
    RENAME_METHOD: proc_RM,
    RENAME_PARAMETER: proc_RP,
    RENAME_VARIABLE: proc_RV,
    RENAME_ATTRIBUTE: proc_RA,
    CHANGE_RETURN_TYPE: proc_CRT,
    CHANGE_PARAMETER_TYPE: proc_CPT,
    CHANGE_VARIABLE_TYPE: proc_CVT,
    CHANGE_ATTRIBUTE_TYPE: proc_CAT,
}


def dump(proj_id, out_file,
         method='odbc', pw=VIRTUOSO_PW, port=VIRTUOSO_PORT):

    driver = sparql.get_driver(method, pw=pw, port=port)

    graph_uri = FB_NS + proj_id

    qtbl = NS_TBL.copy()
    qtbl['graph_uri'] = graph_uri

    tbl = {}  # cid -> refty -> key list

    for ref, _query in QUERY_TBL.items():
        logger.info(f'processing "{ref}"')

        refty = abbrev(ref)

        query = _query % qtbl
        proc = PROC_TBL[ref]

        # print(f'***** {ref} *****')
        # print(query)

        for _, row in driver.query(query):
            cid, r = proc(row)
            key = r.key
            logger.debug(f'key="{key}" cid={cid}')
            try:
                rtbl = tbl[cid]
            except KeyError:
                rtbl = {}
                tbl[cid] = rtbl
            try:
                rl = rtbl[refty]
            except KeyError:
                rl = []
                rtbl[refty] = rl
            rd = r.to_dict()
            if rd not in rl:
                rl.append(rd)

    logger.info(f'dumping into "{out_file}"...')
    with open(out_file, 'w') as f:
        json.dump(tbl, f)


def dump_dtor_map(proj_id, out_file,
                  method='odbc', pw=VIRTUOSO_PW, port=VIRTUOSO_PORT):

    driver = sparql.get_driver(method, pw=pw, port=port)

    graph_uri = FB_NS + proj_id

    qtbl = NS_TBL.copy()
    qtbl['graph_uri'] = graph_uri

    tbl = {}  # cid -> key -> (loc * offset * length) list

    query = DTOR_QUERY % qtbl

    for _, row in driver.query(query):
        cid, key, r = proc_DTOR(row)
        logger.debug(f'{cid} {key} {r}')
        try:
            ktbl = tbl[cid]
        except KeyError:
            ktbl = {}
            tbl[cid] = ktbl
        try:
            rl = ktbl[key]
        except KeyError:
            rl = []
            ktbl[key] = rl
        if r not in rl:
            rl.append(r)

    logger.info(f'dumping into "{out_file}"...')
    with open(out_file, 'w') as f:
        json.dump(tbl, f)
