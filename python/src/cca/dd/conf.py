#!/usr/bin/env python3

import os

CCA_HOME = os.getenv('CCA_HOME', '/opt/cca')
VAR_DIR = os.getenv('CCA_VAR_DIR', '/var/lib/cca')
LOG_DIR = os.getenv('CCA_LOG_DIR', '/var/log/cca')

VIRTUOSO_PW = 'rrj'
VIRTUOSO_PORT = 1111

#

ONT_DIR = os.path.join(CCA_HOME, 'ontologies')

FB_DIR = os.path.join(VAR_DIR, 'db')
FACT_DIR = os.path.join(VAR_DIR, 'fact')
WORK_DIR = os.path.join(VAR_DIR, 'work')

REFACT_DIR = os.path.join(VAR_DIR, 'refactoring')

PARSER_CMD = '/opt/cca/bin/parsesrc.opt'
