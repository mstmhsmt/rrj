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
import logging

from .ref import Ref
from .common import LOG_DIR, REFACT_DIR, WORK_DIR
from .misc import ensure_dir
from cca.ccautil.proc import system
from cca.ccautil.common import setup_logger, DEFAULT_LOGGING_LEVEL

logger = logging.getLogger()

RX_JAR_PATH = os.getenv('RX_JAR_PATH', None)
PATHTBL_FILE_NAME = 'pathtbl.csv'


def load_pathtbl(path):
    tbl = {}
    with open(path) as f:
        reader = csv.reader(f)
        for row in reader:
            tbl[row[0]] = row[1]
    return tbl


class Executor(object):
    def __init__(self, projs_path, ref_dir=REFACT_DIR):
        logger.info(f'projs_path={projs_path}')
        logger.info(f'ref_dir={ref_dir}')
        if not os.path.exists(ref_dir):
            logger.error(f'not found: "{ref_dir}"')
            raise FileNotFoundError
        self.projs_path = projs_path
        self.ref_dir = ref_dir
        self.merge_scenario_count = 0
        self.merge_scenario_list = []

    def dump_merge_scenario_list(self, path):
        if self.merge_scenario_list:
            logger.info(f'dumping into {path}...')
            with open(path, 'w') as f:
                json.dump(self.merge_scenario_list, f)
            logger.info(f'dumped {len(self.merge_scenario_list)} merge scenarios')

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
        proj_path = os.path.join(self.projs_path, proj_id, f'{cid}{suffix}')
        ensure_dir(ws_path)
        proj_name = f'{ref_id}{suffix}'
        opts = get_opts(ws_path, proj_path) + f' -Dproject.name={proj_name}'
        cmd = f'java {opts} -jar {RX_JAR_PATH}'
        logger.debug(f'cmd={cmd}')
        system(cmd)
        pathtbl_path = os.path.join(ws_path, proj_name, PATHTBL_FILE_NAME)
        pathtbl = load_pathtbl(pathtbl_path)
        src_path = os.path.join(os.path.abspath(proj_path), src_loc)
        dest_path = ws_path + pathtbl[src_path]
        return (src_path, dest_path)

    def execute_refs(self):
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
                                        pathb, path0 = self.execute_ref(proj_id, cid, ref)
                                        pathm, path1 = self.execute_ref(proj_id, cid, ref, inv=True)
                                        self.merge_scenario_count += 1
                                        d = {
                                            'id': self.merge_scenario_count,
                                            'proj_id': proj_id,
                                            'instance': [pathb, path0, path1, pathm],
                                        }
                                        self.merge_scenario_list.append(d)
                except Exception:
                    traceback.print_exc()
                    continue


def main():
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

    parser = ArgumentParser(description='Execute refactorings',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('projs_path', type=str, help='projects directory')

    parser.add_argument('-o', '--merge-scenario-list-file', type=str,
                        metavar='JSON_FILE', default='merges-rx.json',
                        help='dump merge scenarios into JSON_FILE')

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

    executor = Executor(args.projs_path)
    executor.execute_refs()
    executor.dump_merge_scenario_list(args.merge_scenario_list_file)


if __name__ == '__main__':
    pass
