#!/usr/bin/env python3

import sys
import os
# import time
import logging
import traceback


from .misc import read_json
from .siteconf import MERGE_SCENARIO_ROOT
from cca.d3j import diffviewer, diffviewer3
from cca.d3j.siteconf import LOG_DIR, WORK_DIR, D3J_DIR
from cca.d3j.common import is_valid_java, ensure_dir
from cca.d3j.merge_engines import ENGINE_TBL, ENGINE_LIST
import cca.d3j.merge_engines as merge_engines

logger = logging.getLogger()

LOGGING_FORMAT = ('[%(asctime)s][%(processName)s]'
                  '[%(levelname)s][%(module)s][%(funcName)s] %(message)s')

SAMPLES_DIR = 'samples'
MERGE_DATA_PATH = 'merges-oracle-rx.json'


class DummyRepo(object):
    def __init__(self, n, proj_dir=SAMPLES_DIR):
        self.name = n
        self.proj_path = os.path.join(proj_dir, n)


def merge(do_merge, merge_data, samples_dir=SAMPLES_DIR,
          no_eval=False, rough_eval=False,
          verbose=False, debug=False,
          check_patch=False, local_cache_name=None,
          suffix=''):
    # start = time.time()

    work_dir = WORK_DIR

    mid = merge_data['id']
    rn = merge_data['proj_id']
    cid = merge_data['cid']

    bpath, ppath1, ppath2, mpath = (os.path.join(MERGE_SCENARIO_ROOT, rn, cid, rp)
                                    for rp in merge_data['instance'])

    dummy_repo = DummyRepo(rn)

    logger.info(f'---------- {rn}:{mid:03} ----------')
    logger.info(f'{bpath} -> ({ppath1}, {ppath2}) -> {mpath}')

    use_eval = not no_eval
    if rough_eval:
        use_eval2 = False
    else:
        use_eval2 = use_eval

    ret = {}

    invalid_java = False
    for p in (bpath, ppath1, ppath2):
        if not is_valid_java(p):
            logger.info(f'{p} is invalid java')
            invalid_java = True
            break

    kwargs = {'use_eval': use_eval,
              'rough_eval': rough_eval,
              'use_eval2': use_eval2,
              'work_dir': work_dir,
              }

    if do_merge == merge_engines.do_d3j:
        if check_patch:
            kwargs['check_patchast'] = True
            if invalid_java:
                kwargs['keep_on_going'] = True
        if debug:
            kwargs['clean_cache'] = False

    if local_cache_name is not None:  # and do_merge == merge_engines.do_d3j:
        kwargs['local_cache_name'] = local_cache_name

    # elif do_merge == merge_engines.do_intellimerge:
    #     kwargs['path'] = merge_data.get('path', None)

    try:
        ret = do_merge((dummy_repo, mid), bpath, ppath1, ppath2, mpath, **kwargs)
    except Exception as e:
        logger.error(str(e))
        traceback.print_exc(file=sys.stdout)
        ret['failed'] = True

    if do_merge == merge_engines.do_d3j and debug:
        proj_work_dir = os.path.join(work_dir, rn)
        ensure_dir(proj_work_dir)
        root_path = os.path.realpath(D3J_DIR)
        bp = os.path.relpath(os.path.realpath(bpath), start=root_path)
        pp1 = os.path.relpath(os.path.realpath(ppath1), start=root_path)
        pp2 = os.path.relpath(os.path.realpath(ppath2), start=root_path)
        html_path = os.path.join(proj_work_dir, f'{mid:03}.html')
        if not os.path.exists(html_path):
            diffviewer3.gen_html(bp, pp1, pp2, htmlf=html_path)
        html_path0 = os.path.join(proj_work_dir, f'{mid:03}-0.html')
        if not os.path.exists(html_path0):
            diffviewer.gen_html(bp, pp1, htmlf=html_path0)
        html_path1 = os.path.join(proj_work_dir, f'{mid:03}-1.html')
        if not os.path.exists(html_path1):
            diffviewer.gen_html(bp, pp2, htmlf=html_path1)

    eff2 = ret.get('effort2', -1)

    if use_eval:
        logger.info(f'effort={ret.get("effort", -1)}')
        logger.info(f'effort2={eff2}')
        logger.info(f'similarity={ret.get("similarity", -1):.3f}')
        logger.info(f'similarity2={ret.get("similarity2", -1):.3f}')
        logger.info(f'distance={ret.get("distance", -1):.3f}')
        logger.info(f'distance2={ret.get("distance2", -1):.3f}')

        logger.info(f'effort3={ret.get("effort3", -1)}')
        logger.info(f'map_error={ret.get("map_error", -1)}')
        logger.info(f'missed_map={ret.get("missed_map", -1)}')
        logger.info(f'missed_ins={ret.get("missed_ins", -1)}')
        logger.info(f'extra_ins={ret.get("extra_ins", -1)}')

    if use_eval and eff2 < 0:
        logger.info(f'{rn} {mid}: failed to get AED')

    # t = time.time() - start
    # ret['time'] = t

    return ret


def main():
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

    parser = ArgumentParser(description='analyze a merge scenario',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    group = parser.add_mutually_exclusive_group()

    parser.add_argument('engine', choices=ENGINE_LIST, help='merge engine')

    parser.add_argument('merges_data_json', help='specify merges data')

    parser.add_argument('proj_id', help='project id')

    parser.add_argument('mid', type=int, help='merge scenario id')

    parser.add_argument('--samples', dest='samples_dir', default=SAMPLES_DIR,
                        help='specify samples directory')

    parser.add_argument('--suffix', dest='suffix', default='',
                        help='specify suffix of log file and intermediate JSONs')

    parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                        help='enable debug printing')

    parser.add_argument('--check-patch', dest='check_patch',
                        action='store_true',
                        help='enable patch check')

    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='enable verbose printing')

    parser.add_argument('--no-eval', dest='no_eval', action='store_true',
                        help='do not evaluate merge results')

    parser.add_argument('--rough-eval', dest='rough_eval', action='store_true',
                        help='make merge result evaluation rough')

    group.add_argument('--base', dest='base', action='store_true',
                       help='resolve conflicts favoring base')

    group.add_argument('--ours', dest='ours', action='store_true',
                       help='resolve conflicts favoring our side')

    group.add_argument('--yours', dest='yours', action='store_true',
                       help='resolve conflicts favoring your side')

    args = parser.parse_args()

    engine = args.engine
    merges_data_json = args.merges_data_json
    samples_dir = args.samples_dir
    no_eval = args.no_eval
    rough_eval = args.rough_eval
    check_patch = args.check_patch

    # log_dir = os.path.join(LOG_DIR, args.engine)
    log_dir = LOG_DIR

    ensure_dir(log_dir)

    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
        check_patch = True

    log_file = os.path.join(log_dir,
                            f'mx1.{args.engine}.{args.mid}{args.suffix}.log')
    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setLevel(log_level)
    fmt = logging.Formatter(LOGGING_FORMAT)
    fh.setFormatter(fmt)
    logging.basicConfig(level=log_level, handlers=[fh])
    logger.addHandler(fh)

    if not os.path.exists(merges_data_json):
        print(f'not found: {merges_data_json}')
        exit(1)

    if not os.path.exists(samples_dir):
        print(f'not found: {samples_dir}')
        exit(1)

    strategy = merge_engines.RESOLVE_WITH_0
    if args.base:
        strategy = merge_engines.RESOLVE_WITH_B
    elif args.ours:
        strategy = merge_engines.RESOLVE_WITH_0
    elif args.yours:
        strategy = merge_engines.RESOLVE_WITH_1

    spec = f'[engine:{engine}][merges_data_json:{merges_data_json}]'
    if no_eval:
        spec += '[no_eval]'
    if rough_eval:
        spec += '[rough_eval]'
    spec += f'[strategy:{strategy}]'

    print(spec)
    print(f'proj_id={args.proj_id} mid={args.mid}')

    merges_data = read_json(merges_data_json)

    merge_data = None

    for proj_id, ctbl in merges_data.items():
        for cid, vtbl in ctbl.items():
            for v, ktbl in vtbl.items():
                for k, xl in ktbl.items():
                    for x in xl:
                        if args.mid == x['id'] and args.proj_id == x['proj_id']:
                            merge_data = x
                            break
                    if merge_data is not None:
                        break
                if merge_data is not None:
                    break
            if merge_data is not None:
                break
        if merge_data is not None:
            break

    if merge_data:
        print(f'FOUND: {merge_data}')

        do_merge = ENGINE_TBL[engine]

        res = merge(do_merge, merge_data, samples_dir=samples_dir,
                    no_eval=no_eval, rough_eval=rough_eval,
                    verbose=args.verbose, debug=args.debug,
                    check_patch=check_patch, local_cache_name=None,
                    suffix=args.suffix)
        print(f'RESULT: {res}')

    else:
        print(f'not found: mid={args.mid}')


if __name__ == '__main__':
    pass
