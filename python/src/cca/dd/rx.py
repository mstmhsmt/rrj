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

from .ref import Ref
from .common import LOG_DIR, REFACT_DIR, WORK_DIR
from .misc import ensure_dir
from .scan_oracle import scan_oracle
from cca.ccautil.proc import system
from cca.ccautil.sloccount import sloccount_for_lang
from cca.ccautil.common import setup_logger, DEFAULT_LOGGING_LEVEL

logger = logging.getLogger()

RX_JAR_PATH = os.getenv('RX_JAR_PATH', None)
PATHTBL_FILE_NAME = 'pathtbl.csv'
DEFAULT_TARGET_REF = 'RV'
TARGET_REF_LIST = DEFAULT_TARGET_REF.split(':')


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


class Executor(object):
    def __init__(self, samples_path, ref_dir=REFACT_DIR):
        logger.info(f'samples_path={samples_path}')
        logger.info(f'ref_dir={ref_dir}')
        if not os.path.exists(ref_dir):
            logger.error(f'not found: "{ref_dir}"')
            raise FileNotFoundError
        self.samples_path = samples_path
        self.ref_dir = ref_dir
        self.merge_scenario_count = 0

    def execute_ref(self, proj_id, cid, ref, inv=False):
        if inv:
            suffix = '-after'
            get_opts = ref.get_inv_options
            src_loc = ref.desc_.loc
        else:
            suffix = '-before'
            get_opts = ref.get_options
            src_loc = ref.desc.loc

        ref_id = ref.get_id()
        ws_path = os.path.join(WORK_DIR, proj_id, cid)
        proj_path = os.path.join(self.samples_path, proj_id, f'{cid}{suffix}')
        ensure_dir(ws_path)
        proj_name = f'{ref_id}{suffix}'
        opts = get_opts(ws_path, proj_path) + f' -Dproject.name={proj_name}'
        cmd = f'java {opts} -jar {RX_JAR_PATH}'
        logger.debug(f'cmd={cmd}')
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
            src_path = os.path.join(os.path.abspath(proj_path), src_loc)
            dest_path = ws_path + pathtbl[src_path]
            return (src_path, dest_path)
        else:
            logger.warning('failed to execute rx')
            return (None, None)

    def make_merge_scenario(self, proj_id, cid, pathb, path1, path2, pathm):
        self.merge_scenario_count += 1
        instance = [pathb, path1, path2, pathm]
        slocs = [sloccount_for_lang('java', p) for p in instance]
        d = {
            'id': self.merge_scenario_count,
            'proj_id': proj_id,
            'cid': cid,
            'instance': instance,
            'slocs': slocs,
        }
        return d

    def extract_merge_scenario(self, proj_id, cid, ref):
        d = None
        pathb, path1 = self.execute_ref(proj_id, cid, ref)
        if pathb is not None and path1 is not None:
            pathm, path2 = self.execute_ref(proj_id, cid, ref, inv=True)
            if pathm is not None and path2 is not None:
                d = self.make_merge_scenario(proj_id, cid, pathb, path1, path2, pathm)
                d['key'] = ref.key
        return d

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
                                            merge_scenario_list.append(d)
                except Exception:
                    traceback.print_exc()
                    continue

        if merge_scenario_list:
            logger.info(f'dumping into {scenarios_path}...')
            with open(scenarios_path, 'w') as f:
                json.dump(merge_scenario_list, f)
            logger.info(f'dumped {self.merge_scenario_count} merge scenarios')

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
                        logger.info(f'x_={x_}')
                        if x_['meth'] == meth_ and x_['class'] == cfqn_:
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
                                    set_kkkklv(merge_scenario_tbl, proj_id, cid, verdict, k, d)
        if merge_scenario_tbl:
            logger.info(f'dumping into {scenarios_path}...')
            with open(scenarios_path, 'w') as f:
                json.dump(merge_scenario_tbl, f)
            logger.info(f'dumped {self.merge_scenario_count} merge scenarios')


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

    log_file = os.path.join(LOG_DIR, 'rx.log')

    setup_logger(logger,
                 log_level,
                 log_file=log_file)

    executor = Executor(args.samples_path)
    executor.execute_refs(args.merge_scenario_list_file)
    executor.execute_oracle_refs(args.oracle, args.merge_scenario_tbl_file)


if __name__ == '__main__':
    pass
