#!/usr/bin/env python3

'''
  rx.py

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
import json
import csv
import traceback
import subprocess
import logging
import sys
import multiprocessing as mp
import time

from .ref import Ref
from .common import LOG_DIR, REFACT_DIR, WORK_DIR
from .misc import ensure_dir
from .scan_oracle import scan_oracle
from . import misc
from .siteconf import MERGE_SCENARIO_ROOT
from cca.ccautil.proc import system
from cca.ccautil.sloccount import sloccount_for_lang
from cca.ccautil.common import setup_logger, DEFAULT_LOGGING_LEVEL
from cca.ccautil.java_token_diff import all_different
from cca.ccautil import sloccount

# logger = logging.getLogger()
logger = mp.get_logger()

RX_JAR_PATH = os.getenv('RX_JAR_PATH', None)
PATHTBL_FILE_NAME = 'pathtbl.csv'
DEFAULT_TARGET_REF = 'RV'
TARGET_REF_LIST = DEFAULT_TARGET_REF.split(':')


LOGGING_FORMAT = ('[%(asctime)s][%(processName)s]'
                  '[%(levelname)s][%(module)s][%(funcName)s] %(message)s')
NPROCS = 2


def set_kkkklv(tbl, k1, k2, k3, k4, v):
    try:
        t1 = tbl[k1]
    except KeyError:
        t1 = {}
        tbl[k1] = t1
    try:
        t2 = t1[k2]
    except KeyError:
        t2 = {}
        t1[k2] = t2
    try:
        t3 = t2[k3]
    except KeyError:
        t3 = {}
        t2[k3] = t3
    try:
        l4 = t3[k4]
    except KeyError:
        l4 = []
        t3[k4] = l4
    l4.append(v)


def load_pathtbl(path):
    tbl = {}
    with open(path) as f:
        reader = csv.reader(f)
        for row in reader:
            tbl[row[0]] = row[1]
    return tbl


def mangleB(i):
    i_ = f'_RxB_{i}'
    return i_


def mangleM(i):
    i_ = f'_RxM_{i}'
    return i_


def init_proc(log_level, suffix):
    pid = mp.current_process().name
    log_dir = os.path.join(LOG_DIR, 'rx')
    log_file = os.path.join(log_dir, f'rx.{pid}{suffix}.log')
    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setLevel(log_level)
    fmt = logging.Formatter(LOGGING_FORMAT)
    fh.setFormatter(fmt)
    logger = mp.get_logger()
    logger.addHandler(fh)
    logger.propagate = False
    sloccount.logger = logger
    misc.logger = logger


class IdGen(object):
    def __init__(self):
        self.count = 0

    def gen(self):
        self.count += 1
        logger.debug(f'{self.count}')
        return self.count


class Executor(object):
    def __init__(self, id_gen, samples_path, ref_dir=REFACT_DIR):
        logger.info(f'samples_path={samples_path}')
        logger.info(f'ref_dir={ref_dir}')
        if not os.path.exists(ref_dir):
            logger.error(f'not found: "{ref_dir}"')
            raise FileNotFoundError
        self.samples_path = samples_path
        self.ref_dir = ref_dir
        self.id_gen = id_gen
        self.cmd_cache = {}   # cmd -> path_tbl
        self.sloc_cache = {}  # path -> sloc

    def count_sloc(self, path, nretries=2):
        try:
            return self.sloc_cache[path]
        except KeyError:
            count = 0
            while count <= nretries:
                if os.path.exists(path):
                    break
                else:
                    logger.warning(f'not found: {path}')
                    time.sleep(2**count)
                    count += 1
                    logger.warning(f'retrying ({count})...')

            datadir = os.path.join(WORK_DIR, f'slocdata-{mp.current_process().name}')
            ensure_dir(datadir)

            sloc = sloccount_for_lang('java', path, datadir=datadir)
            self.sloc_cache[path] = sloc
            return sloc

    def execute_ref(self, proj_id, cid, ref, inv=False, swap=False, mangler=None):
        mangling = ''
        if mangler is not None:
            mangling = f'{mangler('')}'
        if inv:
            suffix = '-after'
            get_opts = ref.get_options_
            src_loc = ref.desc_.loc
        else:
            suffix = '-before'
            get_opts = ref.get_options
            src_loc = ref.desc.loc

        ref_id = ref.get_id()
        ws_path = os.path.join(WORK_DIR, proj_id, cid)
        proj_path = os.path.join(self.samples_path, proj_id, f'{cid}{suffix}')
        ensure_dir(ws_path)
        proj_name = f'{ref_id}{suffix}{mangling}'
        opts = get_opts(ws_path, proj_path, mangler, swap=swap) + f' -Dproject.name={proj_name}'
        cmd = f'java {opts} -jar {RX_JAR_PATH}'
        logger.debug(f'cmd={cmd}')

        if cmd in self.cmd_cache:
            pathtbl = self.cmd_cache[cmd]
            src_path = os.path.join(os.path.abspath(proj_path), src_loc)
            dest_path = ws_path + pathtbl[src_path]
            return (src_path, dest_path)

        if cmd not in self.cmd_cache:
            debug_flag = logger.getEffectiveLevel() == logging.DEBUG
            if debug_flag:
                try:
                    p = subprocess.run(cmd, shell=True, cwd=None, capture_output=True,
                                       encoding=None, errors=None,
                                       text=None, universal_newlines=None)
                    out = p.stdout
                    rc = p.returncode
                except subprocess.CalledProcessError as e:
                    logger.warning(f'"{cmd}":'
                                   f' terminated abnormally (exitcode={e.returncode})')
                    out = e.output
                    rc = 1
                logger.debug(out.decode('utf-8'))
            else:
                rc = system(cmd)
            if rc == 0:
                pathtbl_path = os.path.join(ws_path, proj_name, PATHTBL_FILE_NAME)
                pathtbl = load_pathtbl(pathtbl_path)
                self.cmd_cache[cmd] = pathtbl
                src_path = os.path.join(os.path.abspath(proj_path), src_loc)
                dest_path = ws_path + pathtbl[src_path]
                return (src_path, dest_path)
            else:
                logger.warning('failed to execute rx')
                return (None, None)

    def check_ref(self, proj_id, cid, ref, inv=False, swap=False, mangler=None):
        mangling = ''
        if mangler is not None:
            mangling = f'{mangler('')}'
        if inv:
            suffix = '-after'
            get_opts = ref.get_options_
        else:
            suffix = '-before'
            get_opts = ref.get_options

        ref_id = ref.get_id()
        ws_path = os.path.join(WORK_DIR, proj_id, cid)
        proj_path = os.path.join(self.samples_path, proj_id, f'{cid}{suffix}')
        ensure_dir(ws_path)
        proj_name = f'{ref_id}{suffix}{mangling}'
        opts = get_opts(ws_path, proj_path, mangler, swap=swap) + f' -Dproject.name={proj_name}'
        cmd = f'java {opts} -jar {RX_JAR_PATH}'
        return cmd

    def make_merge_scenario(self, proj_id, cid, pathb, path1, path2, pathm, add_sloc=True):
        root = os.path.join(MERGE_SCENARIO_ROOT, proj_id, cid)
        instance = [os.path.relpath(p, root) for p in [pathb, path1, path2, pathm]]
        d = {
            # 'id': self.id_gen.gen(),
            'proj_id': proj_id,
            'cid': cid,
            'instance': instance,
        }
        if add_sloc:
            def mkpath(rp):
                return os.path.join(MERGE_SCENARIO_ROOT, proj_id, cid, rp)

            slocs = [self.count_sloc(mkpath(x)) for x in instance]
            d['slocs'] = slocs
        return d

    def extract_merge_scenario(self, proj_id, cid, ref, mangle=True):
        d = None
        if mangle:
            pathb, pathb_ = self.execute_ref(proj_id, cid, ref,
                                             swap=True, mangler=mangleB)
            if pathb is None or pathb_ is None or not all_different([pathb, pathb_]):
                return
            pathb, path1 = self.execute_ref(proj_id, cid, ref,
                                            mangler=mangleM)
            if pathb is None or path1 is None or not all_different([pathb, path1]):
                return
            pathm, pathm_ = self.execute_ref(proj_id, cid, ref,
                                             inv=True, swap=True, mangler=mangleM)
            if pathm is None or pathm_ is None or not all_different([pathm, pathm_]):
                return
            pathm, path2 = self.execute_ref(proj_id, cid, ref,
                                            inv=True, mangler=mangleB)
            if pathm is None or path2 is None or not all_different([pathm, path2]):
                return
            d = self.make_merge_scenario(proj_id, cid, pathb_, path1, path2, pathm_)
            d['key'] = ref.key
        else:
            pathb, path1 = self.execute_ref(proj_id, cid, ref)
            if pathb is None or path1 is None or not all_different([pathb, path1]):
                return
            pathm, path2 = self.execute_ref(proj_id, cid, ref, inv=True)
            if pathm is None or path2 is None or not all_different([pathm, path2]):
                return
            d = self.make_merge_scenario(proj_id, cid, pathb, path1, path2, pathm)
            d['key'] = ref.key
        return d

    def check_merge(self, proj_id, cid, ref, mangle=True):
        d = None
        if mangle:
            cmd0 = self.check_ref(proj_id, cid, ref, swap=True, mangler=mangleB)
            cmd1 = self.check_ref(proj_id, cid, ref, mangler=mangleM)
            cmd2 = self.check_ref(proj_id, cid, ref, inv=True, swap=True, mangler=mangleM)
            cmd3 = self.check_ref(proj_id, cid, ref, inv=True, mangler=mangleB)
            d = [cmd0, cmd1, cmd2, cmd3]
        else:
            cmd0 = self.check_ref(proj_id, cid, ref)
            cmd1 = self.execute_ref(proj_id, cid, ref, inv=True)
            d = [cmd0, cmd1]
        return d

    def extract_merge_scenario_mp(self, tid_args):
        tid, args = tid_args
        proj_id, cid, refl, mangle, verdict, k = args
        dl = []
        for ref in refl:
            d = self.extract_merge_scenario(proj_id, cid, ref, mangle=mangle)
            dl.append(d)
        pid = mp.current_process().name
        return (pid, tid, (proj_id, cid, verdict, k, dl))

    def execute_refs(self, scenarios_path):
        merge_scenario_list = []

        for uname in os.listdir(self.ref_dir):
            for rname in os.listdir(os.path.join(self.ref_dir, uname)):
                proj_id = f'{uname}/{rname}'
                proj_dir = os.path.join(self.ref_dir, proj_id)

                if not os.path.isdir(proj_dir):
                    continue

                logger.info(f'proj_id={proj_id}')

                ref_keys_path = os.path.join(proj_dir, 'ref_keys.json')
                logger.info(f'loading "{ref_keys_path}"...')
                try:
                    with open(ref_keys_path) as f:
                        for cid, rtbl in json.load(f).items():
                            logger.info(f'cid={cid}')
                            for ra, rl in rtbl.items():
                                for r in rl:
                                    ref = Ref.from_dict(r)
                                    if ref.has_descs():
                                        logger.info(f'{ref}')
                                        d = self.extract_merge_scenario(proj_id, cid, ref)
                                        if d is not None:
                                            d['id'] = self.id_gen.gen()
                                            merge_scenario_list.append(d)
                except Exception:
                    traceback.print_exc()
                    continue

        if merge_scenario_list:
            logger.info(f'dumping into {scenarios_path}...')
            with open(scenarios_path, 'w') as f:
                json.dump(merge_scenario_list, f)
            logger.info(f'dumped {len(merge_scenario_list)} merge scenarios')

    def execute_refs_mp(self, scenarios_path, nprocs=NPROCS, log_level=None):
        tasks = []
        total_nrefs = 0

        for uname in os.listdir(self.ref_dir):
            for rname in os.listdir(os.path.join(self.ref_dir, uname)):
                proj_id = f'{uname}/{rname}'
                proj_dir = os.path.join(self.ref_dir, proj_id)

                if not os.path.isdir(proj_dir):
                    continue

                logger.info(f'proj_id={proj_id}')

                ref_keys_path = os.path.join(proj_dir, 'ref_keys.json')
                logger.info(f'loading "{ref_keys_path}"...')
                try:
                    with open(ref_keys_path) as f:
                        for cid, rtbl in json.load(f).items():
                            logger.info(f'cid={cid}')
                            for ra, rl in rtbl.items():
                                for r in rl:
                                    ref = Ref.from_dict(r)
                                    if ref.has_descs():
                                        logger.info(f'{ref}')
                                        tasks.append((proj_id, cid, [ref], True, None, None))
                                        total_nrefs += 1
                except Exception:
                    traceback.print_exc()
                    continue

        xl = []
        for tid, task in enumerate(tasks):
            xl.append((tid, task))

        init = None
        initargs = None
        if log_level is not None:
            init = init_proc
            initargs = (log_level, '.rrj')

        done = 0

        merge_scenario_list = []

        with mp.Pool(processes=nprocs, initializer=init, initargs=initargs) as pool:
            for pid, tid, result in pool.imap_unordered(self.extract_merge_scenario_mp, xl,
                                                        chunksize=1):
                _, _, _, _, dl = result
                n = 0
                for d in dl:
                    n += 1
                    if d is not None:
                        d['id'] = self.id_gen.gen()
                        merge_scenario_list.append(d)
                done += n
                r = float(done) * 100.0 / total_nrefs
                sys.stdout.write(f' processed {done:4}/{total_nrefs:4} ({r:2.2f}%)\r')
                sys.stdout.flush()
                logger.info(f'[{pid}] processed {n} in task-{tid} ({done}/{total_nrefs}={r:.2f}%)')

        if merge_scenario_list:
            logger.info(f'dumping into {scenarios_path}...')
            merge_scenario_count = len(merge_scenario_list)
            with open(scenarios_path, 'w') as f:
                json.dump(merge_scenario_list, f)
            logger.info(f'dumped {merge_scenario_count} merge scenarios')

    def get_ref_candidates(self, proj_id, _cid, key):
        cid = f'{_cid}-before'
        cid_ = f'{_cid}-after'
        key_eleml = key.split(' ')
        ra = key_eleml[0]
        candl = []
        match ra:
            case 'RV':
                proj_dir = os.path.join(self.ref_dir, proj_id)
                dtor_map_path = os.path.join(proj_dir, 'dtor_map.json')

                if not os.path.exists(dtor_map_path):
                    return candl

                vmap = key_eleml[1].split('->')
                vt = vmap[0]
                v = vt.split(':')[0]
                vt_ = vmap[1]
                v_ = vt_.split(':')[0]
                meth_ = key_eleml[2]
                cfqn_ = key_eleml[3]

                logger.info(f'vt={vt} v={v} vt_={vt_} v_={v_} meth_={meth_} cfqn_={cfqn_}')

                logger.info(f'loading "{dtor_map_path}"...')
                with open(dtor_map_path) as f:
                    dtor_map = json.load(f)
                    dl = []
                    dl_ = []
                    for x in dtor_map.get(cid, {}).get(vt, []):
                        d = {
                            'offset': x['offset'],
                            'length': x['length'],
                            'name': v_,
                            'loc': x['loc'],
                        }
                        dl.append(d)

                    for x_ in dtor_map.get(cid_, {}).get(vt_, []):
                        if x_['meth'] == meth_ and x_['class'] == cfqn_:
                            logger.info(f'x_={x_}')
                            d_ = {
                                'offset': x_['offset'],
                                'length': x_['length'],
                                'name': v,
                                'loc': x_['loc'],
                            }
                            dl_.append(d_)

                    for d_ in dl_:
                        for d in dl:
                            r = {
                                'key': key,
                                'desc': d,
                                'desc_': d_,
                            }
                            candl.append(r)
        return candl

    def execute_oracle_refs(self, oracle_path, scenarios_path, target_refs=TARGET_REF_LIST):
        if not os.path.exists(oracle_path):
            logger.error(f'not found: "{oracle_path}"')
            return

        merge_scenario_tbl = {}
        merge_scenario_count = 0

        oracle = scan_oracle(oracle_path, out_path='oracle.json')

        for proj_id, ctbl in oracle.items():
            logger.info(f'proj_id={proj_id}')

            for cid, oracle_rtbl in ctbl.items():
                logger.info(f'cid={cid}')

                for ra, oracle_vtbl in oracle_rtbl.items():
                    if ra not in target_refs:
                        continue

                    logger.info(f'ra={ra}')

                    _tp_keyl = [tuple(x) for x in oracle_vtbl.get('TP', [])]
                    _ctp_keyl = [tuple(x) for x in oracle_vtbl.get('CTP', [])]
                    _fp_keyl = [tuple(x) for x in oracle_vtbl.get('FP', [])]

                    tp_keys = set([x[0] for x in _tp_keyl])
                    ctp_keys = set([x[0] for x in _ctp_keyl])
                    fp_keys = set([x[0] for x in _fp_keyl])

                    # atp_keys = tp_keys | ctp_keys

                    logger.info(f'ntp={len(tp_keys)} nctp={len(ctp_keys)} nfp={len(fp_keys)}')

                    for verdict, keys in [('TP', tp_keys), ('CTP', ctp_keys), ('FP', fp_keys)]:
                        logger.info(f'verdict={verdict}')

                        for k in keys:
                            candl = self.get_ref_candidates(proj_id, cid, k)
                            logger.info(f'{k}: {len(candl)} candidates found')
                            for cand in candl:
                                ref = Ref.from_dict(cand)
                                logger.info(f'ref={ref}')
                                d = self.extract_merge_scenario(proj_id, cid, ref)
                                if d is not None:
                                    merge_scenario_count += 1
                                    d['id'] = self.id_gen.gen()
                                    set_kkkklv(merge_scenario_tbl, proj_id, cid, verdict, k, d)
        if merge_scenario_tbl:
            logger.info(f'dumping into {scenarios_path}...')
            with open(scenarios_path, 'w') as f:
                json.dump(merge_scenario_tbl, f)
            logger.info(f'dumped {merge_scenario_count} merge scenarios')

    def execute_oracle_refs_mp(self, oracle_path, scenarios_path, target_refs=TARGET_REF_LIST,
                               nprocs=NPROCS, log_level=None):
        if not os.path.exists(oracle_path):
            logger.error(f'not found: "{oracle_path}"')
            return

        oracle = scan_oracle(oracle_path, out_path='oracle.json')

        tasks = []
        total_nrefs = 0

        for proj_id, ctbl in oracle.items():
            logger.info(f'proj_id={proj_id}')

            for cid, oracle_rtbl in ctbl.items():
                logger.info(f'cid={cid}')

                for ra, oracle_vtbl in oracle_rtbl.items():
                    if ra not in target_refs:
                        continue

                    logger.info(f'ra={ra}')

                    _tp_keyl = [tuple(x) for x in oracle_vtbl.get('TP', [])]
                    _ctp_keyl = [tuple(x) for x in oracle_vtbl.get('CTP', [])]
                    _fp_keyl = [tuple(x) for x in oracle_vtbl.get('FP', [])]

                    tp_keys = set([x[0] for x in _tp_keyl])
                    ctp_keys = set([x[0] for x in _ctp_keyl])
                    fp_keys = set([x[0] for x in _fp_keyl])

                    # atp_keys = tp_keys | ctp_keys

                    logger.info(f'ntp={len(tp_keys)} nctp={len(ctp_keys)} nfp={len(fp_keys)}')

                    for verdict, keys in [('TP', tp_keys), ('CTP', ctp_keys), ('FP', fp_keys)]:
                        logger.info(f'verdict={verdict}')

                        for k in keys:
                            candl = self.get_ref_candidates(proj_id, cid, k)
                            logger.info(f'{k}: {len(candl)} candidates found')
                            if candl:
                                refl = []
                                for cand in candl:
                                    ref = Ref.from_dict(cand)
                                    logger.info(f'ref={ref}')
                                    refl.append(ref)
                                    total_nrefs += 1

                                tasks.append((proj_id, cid, refl, True, verdict, k))

        xl = []
        for tid, task in enumerate(tasks):
            xl.append((tid, task))

        init = None
        initargs = None
        if log_level is not None:
            init = init_proc
            initargs = (log_level, '.oracle')

        done = 0

        merge_scenario_tbl = {}
        merge_scenario_count = 0

        with mp.Pool(processes=nprocs, initializer=init, initargs=initargs) as pool:
            for pid, tid, result in pool.imap_unordered(self.extract_merge_scenario_mp, xl,
                                                        chunksize=1):
                proj_id, cid, verdict, k, dl = result
                n = 0
                for d in dl:
                    n += 1
                    if d is not None:
                        merge_scenario_count += 1
                        d['id'] = self.id_gen.gen()
                        set_kkkklv(merge_scenario_tbl, proj_id, cid, verdict, k, d)
                done += n
                r = float(done) * 100.0 / total_nrefs
                sys.stdout.write(f' processed {done:4}/{total_nrefs:4} ({r:2.2f}%)\r')
                sys.stdout.flush()
                logger.info(f'[{pid}] processed {n} in task-{tid} ({done}/{total_nrefs}={r:.2f}%)')

        if merge_scenario_tbl:
            logger.info(f'dumping into {scenarios_path}...')
            with open(scenarios_path, 'w') as f:
                json.dump(merge_scenario_tbl, f)
            logger.info(f'dumped {merge_scenario_count} merge scenarios')


def main():
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

    parser = ArgumentParser(description='Execute refactorings',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('samples_path', type=str, help='sample projects directory')

    parser.add_argument('--merge-scenario-list-file', type=str,
                        metavar='JSON_FILE', default='merges-rrj-rx.json',
                        help='dump rrj merge scenarios into JSON_FILE')

    parser.add_argument('--oracle', type=str, default='data.json',
                        help='Oracle "data.json"')

    parser.add_argument('--merge-scenario-tbl-file', type=str,
                        metavar='JSON_FILE', default='merges-oracle-rx.json',
                        help='dump oracle merge scenarios into JSON_FILE')

    parser.add_argument('-p', '--nprocs', dest='nprocs', type=int,
                        default=NPROCS,
                        help='specify number of processes')

    parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                        help='enable debug printing')

    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='enable verbose printing')

    args = parser.parse_args()

    log_level = DEFAULT_LOGGING_LEVEL  # logging.WARNING
    if args.verbose:
        log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG

    log_dir = os.path.join(LOG_DIR, 'rx')
    log_file = os.path.join(log_dir, 'rx.log')
    ensure_dir(log_dir)

    setup_logger(logger,
                 log_level,
                 log_file=log_file)

    nprocs = args.nprocs

    executor = Executor(IdGen(), args.samples_path)
    # executor.execute_refs(args.merge_scenario_list_file)
    # executor.execute_oracle_refs(args.oracle, args.merge_scenario_tbl_file)

    print('rx for rrj in progress...')
    executor.execute_refs_mp(args.merge_scenario_list_file,
                             nprocs=nprocs, log_level=log_level)
    print('\nrx for oracle in progress...')
    executor.execute_oracle_refs_mp(args.oracle, args.merge_scenario_tbl_file,
                                    nprocs=nprocs, log_level=log_level)


if __name__ == '__main__':
    pass
