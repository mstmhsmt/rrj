#!/usr/bin/env python3

'''
  rrj.py

  Copyright 2020-2024 Chiba Institute of Technology

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
import csv
import logging

from .common import VAR_DIR, FACT_DIR, LOG_DIR, FB_DIR
from .common import VIRTUOSO_PW, VIRTUOSO_PORT
from .misc import ensure_dir
from .setup_factbase import FB

from . import misc
from . import setup_factbase

from cca.ccautil.cca_config import Config, VKIND_VARIANT
from cca.ccautil.factextractor import Enc, HashAlgo
from cca.ccautil.srcdiff import diffast, diff_dirs
from cca.ccautil.common import setup_logger, DEFAULT_LOGGING_LEVEL
from cca.ccautil import srcdiff, virtuoso, materialize_fact, find_change_patterns

#

logger = logging.getLogger()

FACT_SIZE_THRESH = 100000
FILE_SIM_THRESH = 0.5

DIFF_CACHE_DIR = os.path.join(VAR_DIR, 'cache', 'diffast')
STAT_FILE = os.path.join(VAR_DIR, 'status')

URL_BASE_PATH = '../../..'

#


def set_status(mes):
    logger.log(DEFAULT_LOGGING_LEVEL, mes)
    print(mes)
    try:
        with open(STAT_FILE, 'w') as f:
            f.write(mes)
    except Exception as e:
        logger.warning(str(e))


def shutdown_virtuoso(proj_id, port, pw=VIRTUOSO_PW):
    if misc.is_virtuoso_running(port):
        logger.info(f'shutting down virtuoso for {proj_id}...')
        fb_dir = os.path.join(FB_DIR, proj_id)
        v = virtuoso.base(dbdir=fb_dir, pw=pw, port=port)
        v.shutdown_server()
        logger.info('done.')


def main():
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

    parser = ArgumentParser(description='Reconstruct refactorings on Java programs',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('proj_dir', type=str, help='project directory')
    parser.add_argument('commit_id', metavar='CID', type=str, nargs='+',
                        help='commit id')

    parser.add_argument('--proj-id', type=str, metavar='PROJ_ID', default=None,
                        help='specify project id (dirname of PROJ_DIR is used by default)')

    parser.add_argument('--include', type=str, metavar='DIR', action='append',
                        default=[],
                        help='analyze only sub-directories (relative paths)')

    parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                        help='enable debug printing')

    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='enable verbose printing')

    parser.add_argument('--use-cache', dest='usecache', action='store_true',
                        help='use cached diffast results')

    parser.add_argument('--analyze-unmodified', dest='analyze_unmodified',
                        action='store_true',
                        help='analyze unmodified files as well')

    parser.add_argument('--no-rename-rectification', dest='no_rename_rectification',
                        action='store_true', help='disable rename rectification')

    parser.add_argument('--no-move-rectification', dest='no_move_rectification',
                        action='store_true', help='disable move rectification')

    parser.add_argument('--exit-on-failure', dest='keep_going',
                        action='store_false',
                        help='exits on failures')

    parser.add_argument('--port', dest='port', default=VIRTUOSO_PORT,
                        metavar='PORT', type=int, help='set port number')

    parser.add_argument('--pw', dest='pw', metavar='PASSWORD',
                        default=VIRTUOSO_PW,
                        help='set password to access FB')

    parser.add_argument('-m', '--mem', dest='mem', metavar='GB', type=int,
                        choices=[2, 4, 8, 16, 32, 48, 64], default=8,
                        help='set available memory (GB)')

    args = parser.parse_args()

    log_level = DEFAULT_LOGGING_LEVEL  # logging.WARNING
    if args.verbose:
        log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG

    if args.proj_id is None:
        proj_id = os.path.basename(args.proj_dir)
    else:
        proj_id = args.proj_id

    keep_going = args.keep_going

    ignore_unmodified = not args.analyze_unmodified

    ensure_dir(LOG_DIR)

    log_proj_dir = os.path.join(LOG_DIR, f'{proj_id}')

    ensure_dir(log_proj_dir)

    log_file = os.path.join(LOG_DIR, log_proj_dir, 'rrj.log')

    setup_logger(logger,
                 log_level,
                 log_file=log_file)

    setup_factbase.logger = logger
    misc.logger = logger
    srcdiff.logger = logger
    virtuoso.logger = logger
    materialize_fact.logger = logger
    find_change_patterns.logger = logger

    ###

    # setup config
    conf = Config()
    conf.proj_id = proj_id
    conf.lang = 'java'
    conf.proj_path = args.proj_dir
    conf.vkind = VKIND_VARIANT
    conf.include = args.include
    conf.vpairs = [(f'{cid}-before', f'{cid}-after') for cid in args.commit_id]
    conf.vers = [x for vpl in conf.vpairs for x in vpl]
    conf.get_long_name = lambda x: x
    conf.finalize()
    logger.info('\n{}'.format(conf))

    for v_before, v_after in conf.vpairs:

        # diff dirs
        ensure_dir(DIFF_CACHE_DIR)
        set_status(f'comparing "{v_before}" with "{v_after}"...')
        dir_before = os.path.join(args.proj_dir, v_before)
        dir_after = os.path.join(args.proj_dir, v_after)
        r = diff_dirs(diffast, dir_before, dir_after,
                      usecache=args.usecache,
                      include=args.include,
                      cache_dir_base=DIFF_CACHE_DIR,
                      load_fact=True,
                      fact_versions=[conf.mkver_for_fact_by_name(v)
                                     for v in [v_before, v_after]],
                      fact_proj=proj_id,
                      fact_proj_roots=[dir_before, dir_after],
                      ignore_unmodified=ignore_unmodified,
                      fact_for_changes=True,
                      fact_for_mapping=True,
                      fact_for_ast=True,
                      fact_into_directory=os.path.join(FACT_DIR, proj_id),
                      fact_size_thresh=FACT_SIZE_THRESH,
                      fact_for_cfg=False,
                      fact_encoding=Enc.FDLCO,
                      fact_hash_algo=HashAlgo.MD5,
                      fact_no_compress=True,
                      aggressive=args.no_move_rectification,
                      no_rename_rectification=args.no_rename_rectification,
                      dump_delta=False,
                      fact_for_delta=False,
                      keep_going=keep_going,
                      use_sim=True,
                      sim_thresh=FILE_SIM_THRESH,
                      quiet=(log_level != logging.DEBUG),
                      no_node_count=True,
                      )
        cost = r['cost']
        nmappings = r['nmappings']
        nrelabels = r['nrelabels']
        try:
            nnodes1 = r['nnodes1']
            nnodes2 = r['nnodes2']
            nnodes = r['nnodes']
        except KeyError:
            logger.warning('failed to get total number of nodes')
            nnodes1 = srcdiff.count_nodes([dir_before])
            nnodes2 = srcdiff.count_nodes([dir_after])
            nnodes = nnodes1 + nnodes2
        dist = 0
        sim = 0
        if nmappings > 0:
            dist = float(cost) / float(nmappings)
        if nnodes > 0:
            sim = float(2 * (nmappings - nrelabels) + nrelabels) / float(nnodes)
        logger.info(f'nodes: {nnodes1} -> {nnodes2}')
        logger.info(f'edit distance: {cost}')
        logger.info(f'similarity: {sim}')
        logger.info(f'evolutionary distance: {dist}')

        renamed_file_pairs = []
        for f1, f2 in r['modified']:
            _f1 = os.path.relpath(f1, dir_before)
            _f2 = os.path.relpath(f2, dir_after)
            if _f1 != _f2:
                renamed_file_pairs.append((_f1, _f2))

        renamed_file_pairs_path = os.path.join(dir_before, 'renamed_file_pairs.csv')
        if not os.path.exists(renamed_file_pairs_path) and renamed_file_pairs:
            with open(renamed_file_pairs_path, 'w', newline='') as f:
                w = csv.writer(f)
                for row in renamed_file_pairs:
                    w.writerow(row)

    # setup FB
    set_status('building factbase...')
    fb = FB(proj_id, mem=args.mem, pw=args.pw, port=args.port,
            build_only=False, conf=conf,
            url_base_path=URL_BASE_PATH, logdir=log_proj_dir)
    fb.setup()

    if not args.debug:
        set_status(f'shutting down virtuoso (port={args.port})...')
        shutdown_virtuoso(proj_id, args.port, pw=args.pw)

    set_status('finished.')


if __name__ == '__main__':
    main()
