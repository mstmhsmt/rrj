#!/usr/bin/env python3

import os
import sys
import json
import logging

from pathlib import PurePath
from shutil import copytree

from cca.ccautil.java_token_diff import compare_files
from cca.d3j.common import set_list, ensure_dir
from .misc import read_json


logger = logging.getLogger()

LOGGING_FORMAT = ('[%(asctime)s][%(processName)s]'
                  '[%(levelname)s][%(module)s][%(funcName)s] %(message)s')

SAMPLES_DIR = 'samples'
MERGE_DATA_PATH = 'merges-oracle-rx.json'
VAR_WORK_PATH = 'var/work'


def get_orig(proj_id, cid, head):
    tbl_path = os.path.join(VAR_WORK_PATH, proj_id, cid, head, 'pathtbl.csv')
    orig = None
    with open(tbl_path) as f:
        for _line in f.readlines():
            line = _line.strip()
            orig = line.split(',')[0]
    return orig


def get_path(proj_id, cid, rp):
    head = PurePath(rp).parts[0]
    orig = get_orig(proj_id, cid, head)
    logger.debug(f'{rp} -> {orig}')
    return orig


def get_sim(proj_id, cid, rp1, rp2):
    p1 = get_path(proj_id, cid, rp1)
    p2 = get_path(proj_id, cid, rp2)
    r = compare_files(p1, p2)
    s = r['sim']
    logger.debug(f'{rp1} vs {rp2} --> {s}')
    return s


def filter_merges(proj_id, cid, k, merges):
    logger.debug(f'* {proj_id} {cid} {k}')
    merges_ = []
    max_sim = 0.0
    tbl = {}
    for merge in merges:
        inst = merge['instance']
        b = inst[0]
        m = inst[3]
        s = get_sim(proj_id, cid, b, m)
        set_list(tbl, s, merge)
        if s > max_sim:
            max_sim = s
    logger.debug(f'max_sim={max_sim}')
    merges_.extend(tbl[max_sim])
    return merges_


def get_heads(merges):
    heads = set()
    for merge in merges:
        proj_id = merge['proj_id']
        cid = merge['cid']
        inst = merge['instance']
        for rp in inst:
            head = PurePath(rp).parts[0]
            heads.add((proj_id, cid, head))
    return heads


def main():
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

    parser = ArgumentParser(description='filter merge scenarios',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                        help='enable debug printing')

    parser.add_argument('--data', help='specify merges data', default=MERGE_DATA_PATH)

    parser.add_argument('--samples', dest='samples_dir', default=SAMPLES_DIR,
                        help='specify samples directory')

    parser.add_argument('-o', '--out-json', dest='out_json', default='a.json',
                        help='filtered JSON')

    parser.add_argument('--out-dir', dest='out_dir', default=None,
                        help='reduced var/work')

    args = parser.parse_args()

    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG

    log_file = os.path.join('.', 'filt_merges.log')
    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setLevel(log_level)
    fmt = logging.Formatter(LOGGING_FORMAT)
    fh.setFormatter(fmt)
    logging.basicConfig(level=log_level, handlers=[fh])
    logger.addHandler(fh)

    data = read_json(args.data)

    nprojs = len(data)
    done = 0

    used_heads = set()

    for proj_id, ctbl in data.items():
        for cid, vtbl in ctbl.items():
            vs_to_be_removed = []
            for v, ktbl in vtbl.items():
                if v != 'TP':
                    vs_to_be_removed.append(v)
                    continue
                for k, xl in ktbl.items():
                    xl_ = filter_merges(proj_id, cid, k, xl)
                    ktbl[k] = xl_
                    used_heads |= get_heads(xl_)
            for v in vs_to_be_removed:
                del vtbl[v]
        done += 1
        r = float(done) * 100.0 / nprojs
        sys.stdout.write(f' processed {done:4}/{nprojs:4} ({r:2.2f}%)\r')
        sys.stdout.flush()

    with open(args.out_json, 'w') as f:
        json.dump(data, f)
        print(f'dumped into "{args.out_json}"')

    if args.out_dir is not None:
        print(f'dumping reduced var/work into "{args.out_dir}"...')
        ensure_dir(args.out_dir)
        for proj_id, cid, head in used_heads:
            src = os.path.join(VAR_WORK_PATH, proj_id, cid, head)
            dst = os.path.join(args.out_dir, proj_id, cid, head)
            copytree(src, dst)
