#!/usr/bin/env python3

import sys
import os
import json
# import time
import logging
import multiprocessing as mp
import traceback


from .misc import read_json
from cca.d3j import diffviewer, diffviewer3
from cca.d3j.siteconf import LOG_DIR, WORK_DIR, D3J_DIR
from cca.d3j.common import get_list, is_valid_java, ensure_dir
from cca.d3j.merge_engines import ENGINE_TBL, ENGINE_LIST

import cca.d3j.common as d3j_common
import cca.d3j.merge_engines as merge_engines
import cca.d3j.merge_delta as merge_delta

# logger = logging.getLogger()
logger = mp.get_logger()

LOGGING_FORMAT = ('[%(asctime)s][%(processName)s]'
                  '[%(levelname)s][%(module)s][%(funcName)s] %(message)s')
NPROCS = 2

SAMPLES_DIR = 'samples'
MERGE_DATA_PATH = 'merges-oracle-rx.json'


def get_weight(d):
    try:
        w = d['weight']
    except Exception:
        try:
            slocs = d['slocs']
            eds = d['eds']
            sims = d['sims']

            sloc = float(sum(slocs)) / 4
            diff = float(sum(eds)) / 2
            sim = sum(sims) / 2
            w = sloc * diff / sim / 1000.0
        except Exception:
            slocs = d.get('slocs', [])
            w = sum(slocs)
    return w


class Exit(Exception):
    pass


def divide(ds, n, get_weight=get_weight):
    sorted_ds = sorted(ds, key=get_weight)

    weights = [get_weight(d) for d in sorted_ds]

    bins = [[] for _ in range(n)]

    def take():
        i = len(weights) - 1
        if i < 0:
            raise Exit
        w = weights.pop()
        return [i, w]

    try:
        for b in bins:
            i_w = take()
            b.append(i_w)

        while True:
            for b in bins:
                b[-1][1] -= 1
                if b[-1][1] <= 0:
                    i_w = take()
                    b.append(i_w)
    except Exit:
        result = []
        for b in bins:
            result.append([sorted_ds[i] for i, _ in b])

        return result


def init_proc(engine, log_level, strategy):
    merge_engines.RESOLVE_STRATEGY = strategy
    pid = mp.current_process().name
    log_dir = os.path.join(LOG_DIR, engine)
    log_file = os.path.join(log_dir, f'mx.{engine}.{pid}.log')
    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setLevel(log_level)
    fmt = logging.Formatter(LOGGING_FORMAT)
    fh.setFormatter(fmt)
    logger = mp.get_logger()
    logger.addHandler(fh)
    logger.propagate = False
    d3j_common.logger = logger
    merge_engines.logger = logger
    merge_delta.logger = logger


class DummyRepo(object):
    def __init__(self, n, proj_dir=SAMPLES_DIR):
        self.name = n
        self.proj_path = os.path.join(proj_dir, n)


def merge(do_merge, merge_data, samples_dir=SAMPLES_DIR,
          no_eval=False, rough_eval=False,
          verbose=False, debug=False,
          check_patch=False, local_cache_name=None):
    # start = time.time()

    mid = merge_data['id']
    rn = merge_data['proj_id']

    (bpath, ppath1, ppath2, mpath) = merge_data['instance']

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
              'use_eval2': use_eval2
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

    if do_merge == merge_engines.do_d3j and debug:
        proj_work_dir = os.path.join(WORK_DIR, rn)
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


def analyze(args_kw):
    args, kw = args_kw
    engine, tid, ds, out_dir = args

    do_merge = ENGINE_TBL[engine]

    # proj_id -> {'id','hunk_conflict_count','effort','similarity','effort2','similarity2'} list
    tbl = {}

    pid = mp.current_process().name

    kw['local_cache_name'] = pid

    count = 0
    for d in ds:
        iid = d['id']
        proj_id = d['proj_id']
        ret = merge(do_merge, d, **kw)
        ret['id'] = iid
        get_list(tbl, proj_id).append(ret)
        count += 1

    out_path = os.path.join(out_dir, f'{pid}-{tid}.json')
    with open(out_path, 'w') as f:
        json.dump(tbl, f)

    return (pid, tid, count)


def run(engine, tasks, samples_dir, out_dir, nprocs=NPROCS, no_eval=False,
        rough_eval=False, verbose=False, debug=False, log_level=None,
        check_patch=False, strategy=merge_engines.RESOLVE_WITH_B):
    nmerges = 0

    for ml in tasks:
        nmerges += len(ml)

    print(f'{nmerges} merges found')
    logger.info(f'{nmerges} merges found')

    init = None
    initargs = None
    if log_level is not None:
        init = init_proc
        initargs = (engine, log_level, strategy)

    done = 0

    xl = []

    kw = {'samples_dir': samples_dir,
          'no_eval': no_eval,
          'rough_eval': rough_eval,
          'verbose': verbose,
          'debug': debug,
          'check_patch': check_patch}

    for tid, task in enumerate(tasks):
        xl.append(((engine, tid, task, out_dir), kw))

    with mp.Pool(processes=nprocs, initializer=init, initargs=initargs) as pool:
        for pid, tid, n in pool.imap_unordered(analyze, xl, chunksize=1):
            done += n
            r = float(done) * 100.0 / nmerges
            sys.stdout.write(f' processed {done:4}/{nmerges:4} ({r:2.2f}%)\r')
            sys.stdout.flush()
            logger.info(f'[{pid}] processed {n} projects in task-{tid} ({done}/{nmerges}={r:.2f}%)')

    print(f'processed {done} merges in total          ')
    logger.info(f'processed {done} merges in total')


def main():
    n_cores = NPROCS

    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

    parser = ArgumentParser(description='analyze merge scenarios (multi-process)',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    group = parser.add_mutually_exclusive_group()

    parser.add_argument('engine', choices=ENGINE_LIST, help='merge engine')

    parser.add_argument('data', help='specify merge data')

    parser.add_argument('--samples', dest='samples_dir', default=SAMPLES_DIR,
                        help='specify samples directory')

    parser.add_argument('-t', '--task-size', dest='task_size', type=int,
                        default=4,
                        help='specify task size')

    parser.add_argument('-p', '--nprocs', dest='nprocs', type=int,
                        default=n_cores,
                        help='specify number of processes')

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
    data = args.data
    samples_dir = args.samples_dir
    nprocs = args.nprocs
    no_eval = args.no_eval
    rough_eval = args.rough_eval
    verbose = args.verbose
    check_patch = args.check_patch

    task_size = args.task_size
    log_dir = os.path.join(LOG_DIR, args.engine)

    ensure_dir(log_dir)

    log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
        check_patch = True

    log_file = os.path.join(log_dir, f'mx.{args.engine}.log')
    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setLevel(log_level)
    fmt = logging.Formatter(LOGGING_FORMAT)
    fh.setFormatter(fmt)
    logging.basicConfig(level=log_level, handlers=[fh])
    logger.addHandler(fh)

    if not os.path.exists(data):
        print(f'not found: {data}')
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

    print(f'engine={engine}')
    print(f'nprocs={nprocs}')
    print(f'data={data}')
    print(f'no_eval={no_eval}')
    print(f'rough_eval={rough_eval}')
    print(f'strategy={strategy}')

    out_dir = os.path.join(WORK_DIR, 'json', engine)
    ensure_dir(out_dir)

    dl = read_json(data)
    if isinstance(dl, dict):
        dl_ = []
        for proj_id, ctbl in dl.items():
            for cid, vtbl in ctbl.items():
                for v, ktbl in vtbl.items():
                    for k, xl in ktbl.items():
                        dl_.extend(xl)
        dl = dl_

    nmerges = len(dl)

    print(f'{nmerges} merges found')
    logger.info(f'{nmerges} merges found')

    n = nprocs

    if task_size * nprocs <= nmerges:
        n = int(nmerges / task_size)
        print(f'n={n}')
        tasks = divide(dl, n)
    else:
        print(f'n={nmerges}')
        tasks = [[x] for x in dl]

    ntasks = len(tasks)

    print(f'performing {ntasks} tasks with {nprocs} processes...')
    logger.info(f'performing {ntasks} tasks with {nprocs} processes...')

    run(engine, tasks, samples_dir, out_dir, nprocs=nprocs,
        no_eval=no_eval, rough_eval=rough_eval,
        verbose=verbose, debug=args.debug,
        check_patch=check_patch, log_level=log_level, strategy=strategy)


if __name__ == '__main__':
    pass
