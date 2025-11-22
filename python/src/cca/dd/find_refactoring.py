#!/usr/bin/env python3

'''
  find_refactoring.py

  Copyright 2018-2022 Chiba Institute of Technology

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

import os.path
# import logging

from .conf import CCA_HOME
from cca.ccautil import find_change_patterns
from cca.ccautil.find_change_patterns import Predicates
from cca.ccautil.ns import REF_NS, JREF_NS, CREF_NS

from cca.factutil.rdf import Predicate

# logger = logging.getLogger()

QUERY_DIR = os.path.join(CCA_HOME, 'queries', 'refactoring')


class FactExtractor(find_change_patterns.FactExtractor):

    def get_other_info(self, ver0, ver1):
        return self.get_git_commit_info(ver0, ver1)


JAVA_PREDICATES = Predicates()
JAVA_PREDICATES.chgpat_ns = JREF_NS
JAVA_PREDICATES.p_filepair = Predicate(REF_NS, 'filePair')
JAVA_PREDICATES.p_chgpat = Predicate(REF_NS, 'refactoring')

C_PREDICATES = Predicates()
C_PREDICATES.chgpat_ns = CREF_NS
C_PREDICATES.p_filepair = Predicate(REF_NS, 'filePair')
C_PREDICATES.p_chgpat = Predicate(REF_NS, 'refactoring')


PREDICATE_TBL = {'java': JAVA_PREDICATES, 'c': C_PREDICATES}


def get_queries(weak=False):
    # rename_method = 'rename_method.rq'
    # move_method = 'move_method.rq'

    # if weak:
    #     rename_method    = 'weak_'+rename_method
    #     move_method      = 'weak_'+move_method

    queries = {'java':  # (FILE,
                        #  ENT_VAR0, ENT_VAR1,
                        #  EXTRA_ENT_VAR_PAIRS,
                        #  EXTRA_VAR_LIST,
                        #  ESSENTIAL_VARS(RM,AD,MP),
                        #  INST_KEY, INST_KEY_IS_ONE_TO_ONE,
                        #  PER_VER, MIN_EXTRA_PAIRS)
               [
                   ('local_variable_rename.rq', 'originalDtor', 'modifiedDtor',
                    [('originalVariable', 'modifiedVariable')],
                    ['originalVariableName', 'modifiedVariableName',
                     'originalMethod', 'modifiedMethod'],
                    ([], [], [('dtor', 'dtor_'), ('v', 'v_')]), None,
                    None, False, 0),

                   ('rename_parameter.rq',
                    'originalParameter', 'modifiedParameter',
                    [('originalVariable', 'modifiedVariable')],
                    ['originalParameterName', 'modifiedParameterName',
                     'methodName', 'className',
                     'originalMethod', 'modifiedMethod', 'originalClass'],
                    ([], [], [('param', 'param_'), ('v', 'v_')]), None,
                    None, False, 0),

                   ('rename_field.rq', 'originalField', 'modifiedField', [],
                    ['originalFieldName', 'modifiedFieldName',
                     'originalClass', 'modifiedClass'],
                    ([], [], [('vdtor', 'vdtor_')]), None, None, False, 0),

                   ('rename_method.rq', 'originalMethod', 'modifiedMethod', [],
                    ['originalMethodName', 'modifiedMethodName'],
                    ([], [], [('meth', 'meth_')]), None, None, False, 0),

                   ('change_parameter_type.rq', 'originalType', 'modifiedType',
                    [('originalVariable', 'modifiedVariable')],
                    ['originalParameterName', 'modifiedParameterName',
                     'originalTypeName', 'modifiedTypeName',
                     'originalTypeDims', 'modifiedTypeDims',
                     'methodName', 'className',
                     'originalParameter', 'modifiedParameter',
                     'originalMethod', 'modifiedMethod',
                     'originalClass', 'modifiedClass'],
                    ([], [], [('ty', 'ty_'), ('v', 'v_')]), None,
                    None, False, 0),

                   ('change_variable_type.rq', 'originalType', 'modifiedType',
                    [('originalVariable', 'modifiedVariable')],
                    ['originalTypeName', 'modifiedTypeName',
                     'originalTypeDims', 'modifiedTypeDims',
                     'originalVariableName', 'modifiedVariableName',
                     'originalMethod', 'modifiedMethod'],
                    ([], [], [('ty', 'ty_'), ('v', 'v_')]), None,
                    None, False, 0),

                   ('change_field_type.rq', 'originalType', 'modifiedType', [],
                    ['originalFieldName', 'modifiedFieldName',
                     'originalTypeName', 'modifiedTypeName',
                     'originalTypeDims', 'modifiedTypeDims',
                     'originalClass', 'modifiedClass'],
                    ([], [], [('ty', 'ty_')]), None, None, False, 0),

                   ('change_return_type.rq', 'originalType', 'modifiedType',
                    [],
                    ['originalTypeName', 'modifiedTypeName',
                     'originalTypeDims', 'modifiedTypeDims',
                     'methodName', 'className',
                     'originalMethod', 'modifiedMethod',
                     'originalClass', 'modifiedClass'],
                    ([], [], [('ty', 'ty_')]), None, None, False, 0),

                   # ('extract_variable.rq', 'originalExpr', 'movedExpr',
                   #  [('originalContext', 'modifiedContext'),
                   #   ('originalExpr', 'extractedVariable')],
                   #  ['extractedVariableName', 'originalMethodName',
                   #   'extractedDtor',
                   #   'modifiedMethodName', 'originalMethod', 'modifiedMethod'],
                   #  ([], ['vdtor_', 'v_'], [('f', 'f_'), ('a', 'rhs_')]), None,
                   #  None, False, 0),

                   # ('inline_variable.rq', 'originalExpr', 'movedExpr',
                   #  [('originalContext', 'modifiedContext'),
                   #   ('eliminatedVariable', 'movedExpr')],
                   #  ['eliminatedVariableName', 'originalMethodName',
                   #   'eliminatedDtor',
                   #   'modifiedMethodName', 'originalMethod', 'modifiedMethod'],
                   #  (['vdtor', 'v'], [], [('f', 'f_'), ('rhs', 'a_')]), None,
                   #  None, False, 0),
                ],
               'c':
               [
               ]
               }
    return queries


QUERIES = get_queries(weak=False)


def find(base_dir, proj_id, foutdir, outdir, pw, port,
         limit=None, lang=None, method='odbc', change_enumeration=False,
         per_ver=False,
         query_prec=False, conf=None, url_base_path='..'):

    find_change_patterns.find(QUERY_DIR, QUERIES, PREDICATE_TBL, FactExtractor,
                              base_dir, proj_id, foutdir, outdir, pw, port,
                              limit, lang, method, change_enumeration, per_ver,
                              query_prec, conf=conf,
                              url_base_path=url_base_path)


def main():
    find_change_patterns.main(QUERY_DIR,
                              QUERIES,
                              'find refactorings',
                              predicate_tbl=PREDICATE_TBL,
                              extra_fact_extractor=FactExtractor)


if __name__ == '__main__':
    main()
