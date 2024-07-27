#!/usr/bin/env python3

'''
  ref_key_queries.py

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

from .common import RENAME_METHOD, RENAME_PARAMETER, RENAME_VARIABLE, RENAME_ATTRIBUTE
from .common import CHANGE_RETURN_TYPE
from .common import CHANGE_PARAMETER_TYPE, CHANGE_VARIABLE_TYPE, CHANGE_ATTRIBUTE_TYPE
from .common import EXTRACT_VARIABLE, INLINE_VARIABLE

DTOR_QUERY = '''DEFINE input:inference "ont.cpi"
PREFIX ver:  <%(ver_ns)s>
PREFIX java: <%(java_ns)s>
PREFIX src:  <%(src_ns)s>

SELECT DISTINCT ?ver ?loc ?cfqn ?mname ?msig ?vname ?vtyname ?dims ?offset ?length
WHERE {
GRAPH <%(graph_uri)s> {
  {
    SELECT DISTINCT ?dtor ?vtyname ?dims
    WHERE {
      {
        ?dtor a java:ForHeader ;
              src:child1 ?vty .
      }
      UNION
      {
        ?dtor src:parent ?decl .
        ?decl src:child1 ?vty .
      }
      UNION
      {
        ?dtor a java:CatchParameter ;
              src:child1 ?vty .
      }
      ?vty a java:Type ;
           a ?cat OPTION (INFERENCE NONE) .
      {
        GRAPH <http://codinuum.com/ont/cpi> {
          ?cat rdfs:label ?vtyname0 .
        }
        BIND (STR(?vtyname0) AS ?vtyname)
      }
      UNION
      {
        ?vty java:name ?vtyname .
      }
      OPTIONAL {
        ?vty java:dimensions ?dims .
      }
    }  GROUP BY ?dtor ?vtyname ?dims
  }
  ?dtor java:name ?vname ;
        java:identOffset ?offset ;
        java:identLength ?length ;
        java:inMethodOrConstructor ?meth .
  {
    SELECT DISTINCT ?meth ?mname ?msig ?cfqn ?loc ?ver
    WHERE {
      ?meth a java:MethodOrConstructor ;
            java:inTypeDeclaration ?tdecl ;
            java:name ?mname ;
            java:fullyQualifiedName ?mfqn ;
            java:signature ?msig .

      ?tdecl a java:TypeDeclaration ;
             java:fullyQualifiedName ?cfqn ;
             src:inFile/src:location ?loc ;
             ver:version ?ver .

    } GROUP BY ?meth ?mname ?msig ?cfqn ?loc ?ver
  }
}
}
'''

RM_QUERY = '''DEFINE input:inference "ont.cpi"
PREFIX ver:  <%(ver_ns)s>
PREFIX jref: <%(jref_ns)s>
PREFIX java: <%(java_ns)s>

SELECT DISTINCT ?mname ?msig ?cfqn ?abst ?mname_ ?msig_ ?abst_ ?cfqn_ ?ver ?ver_
WHERE {
GRAPH <%(graph_uri)s> {
[] a jref:RenameMethod ;
   a ?ref ;
   jref:originalMethod ?meth ;
   jref:modifiedMethod ?meth_ .
  {
    SELECT DISTINCT ?meth ?mname ?msig ?cfqn ?ver ?abst
    WHERE {
      ?meth a java:MethodOrConstructor ;
            java:inTypeDeclaration ?tdecl ;
            java:name ?mname ;
            java:fullyQualifiedName ?mfqn ;
            java:signature ?msig .

      ?tdecl a java:TypeDeclaration ;
             java:fullyQualifiedName ?cfqn ;
             ver:version ?ver .

      OPTIONAL {
        ?meth java:isAbstract ?abst .
      }

    } GROUP BY ?meth ?mname ?msig ?cfqn ?ver ?abst
  }
  {
    SELECT DISTINCT ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?abst_
    WHERE {
      ?meth_ a java:MethodOrConstructor ;
             java:inTypeDeclaration ?tdecl_ ;
             java:name ?mname_ ;
             java:fullyQualifiedName ?mfqn_ ;
             java:signature ?msig_ .

      ?tdecl_ a java:TypeDeclaration ;
              java:fullyQualifiedName ?cfqn_ ;
              ver:version ?ver_ .

      OPTIONAL {
        ?meth_ java:isAbstract ?abst_ .
      }

    } GROUP BY ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?abst_
  }
  ?ver ver:next ?ver_ .
}
}
'''

RP_QUERY = '''DEFINE input:inference "ont.cpi"
PREFIX ver:  <%(ver_ns)s>
PREFIX jref: <%(jref_ns)s>
PREFIX java: <%(java_ns)s>
PREFIX src:  <%(src_ns)s>

SELECT DISTINCT ?pname ?ptyname ?pname_ ?ptyname_ ?dims ?dims_
                ?mname ?msig ?cfqn ?mname_ ?msig_ ?abst_ ?cfqn_ ?ver ?ver_
WHERE {
GRAPH <%(graph_uri)s> {
[] a jref:RenameParameter ;
   a ?ref ;
   jref:originalParameter ?param;
   jref:modifiedParameter ?param_;
   jref:originalParameterName ?pname ;
   jref:modifiedParameterName ?pname_ ;
   jref:originalMethod ?meth ;
   jref:modifiedMethod ?meth_ .
  {
    SELECT DISTINCT ?param ?ptyname ?dims
    WHERE {
      ?param src:child1 ?pty .
      ?pty a java:Type ;
           a ?cat OPTION (INFERENCE NONE) .
      {
        GRAPH <http://codinuum.com/ont/cpi> {
          ?cat rdfs:label ?ptyname0 .
        }
        BIND (STR(?ptyname0) AS ?ptyname)
      }
      UNION
      {
        ?pty java:name ?ptyname .
      }
      OPTIONAL {
        ?pty java:dimensions ?dims .
      }
    }  GROUP BY ?param ?ptyname ?dims
  }
  {
    SELECT DISTINCT ?param_ ?ptyname_ ?dims_
    WHERE {
      ?param_ src:child1 ?pty_ .

      ?pty_ a java:Type ;
            a ?cat_ OPTION (INFERENCE NONE) .
      {
        GRAPH <http://codinuum.com/ont/cpi> {
          ?cat_ rdfs:label ?ptyname0_ .
        }
        BIND (STR(?ptyname0_) AS ?ptyname_)
      }
      UNION
      {
        ?pty_ java:name ?ptyname_ .
      }
      OPTIONAL {
        ?pty_ java:dimensions ?dims_ .
      }
    }  GROUP BY ?param_ ?ptyname_ ?dims_
  }
  {
    SELECT DISTINCT ?meth ?mname ?msig ?cfqn ?ver
    WHERE {
      ?meth a java:MethodOrConstructor ;
            java:inTypeDeclaration ?tdecl ;
            java:name ?mname ;
            java:fullyQualifiedName ?mfqn ;
            java:signature ?msig .

      ?tdecl a java:TypeDeclaration ;
             java:fullyQualifiedName ?cfqn ;
             ver:version ?ver .

    } GROUP BY ?meth ?mname ?msig ?cfqn ?ver
  }
  {
    SELECT DISTINCT ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?abst_
    WHERE {
      ?meth_ a java:MethodOrConstructor ;
             java:inTypeDeclaration ?tdecl_ ;
             java:name ?mname_ ;
             java:fullyQualifiedName ?mfqn_ ;
             java:signature ?msig_ .

      ?tdecl_ a java:TypeDeclaration ;
              java:fullyQualifiedName ?cfqn_ ;
              ver:version ?ver_ .

      OPTIONAL {
        ?meth_ java:isAbstract ?abst_ .
      }

    } GROUP BY ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?abst_
  }
  ?ver ver:next ?ver_ .
}
}
'''

RV_QUERY = '''DEFINE input:inference "ont.cpi"
PREFIX ver:  <%(ver_ns)s>
PREFIX jref: <%(jref_ns)s>
PREFIX java: <%(java_ns)s>
PREFIX src:  <%(src_ns)s>

SELECT DISTINCT ?vname ?vtyname ?vname_ ?vtyname_ ?dims ?dims_
                ?mname ?msig ?cfqn ?mname_ ?msig_ ?cfqn_ ?ver ?ver_
                ?offset ?length ?offset_ ?length_ ?loc ?loc_
WHERE {
GRAPH <%(graph_uri)s> {
[] a jref:LocalVariableRename ;
   a ?ref ;
   jref:originalDtor ?dtor;
   jref:modifiedDtor ?dtor_;
   jref:originalVariableName ?vname ;
   jref:modifiedVariableName ?vname_ ;
   jref:originalMethod ?meth ;
   jref:modifiedMethod ?meth_ .
  {
    SELECT DISTINCT ?dtor ?vtyname ?dims
    WHERE {
      {
        ?dtor a java:ForHeader ;
              src:child1 ?vty .
      }
      UNION
      {
        ?dtor src:parent ?decl .
        ?decl src:child1 ?vty .
      }
      # UNION
      # {
      #   ?dtor a java:Resource ;
      #         src:child1 ?vty .
      # }
      UNION
      {
        ?dtor a java:CatchParameter ;
              src:child1 ?vty .
      }
      ?vty a java:Type ;
           a ?cat OPTION (INFERENCE NONE) .
      {
        GRAPH <http://codinuum.com/ont/cpi> {
          ?cat rdfs:label ?vtyname0 .
        }
        BIND (STR(?vtyname0) AS ?vtyname)
      }
      UNION
      {
        ?vty java:name ?vtyname .
      }
      OPTIONAL {
        ?vty java:dimensions ?dims .
      }
    }  GROUP BY ?dtor ?vtyname ?dims
  }
  {
    SELECT DISTINCT ?dtor_ ?vtyname_ ?dims_
    WHERE {
      {
        ?dtor_ a java:ForHeader ;
               src:child1 ?vty_ .
      }
      UNION
      {
        ?dtor_ src:parent ?decl_ .
        ?decl_ src:child1 ?vty_ .
      }
      # UNION
      # {
      #   ?dtor_ a java:Resource ;
      #          src:child1 ?vty_ .
      # }
      UNION
      {
        ?dtor_ a java:CatchParameter ;
               src:child1 ?vty_ .
      }
      ?vty_ a java:Type ;
            a ?cat_ OPTION (INFERENCE NONE) .
      {
        GRAPH <http://codinuum.com/ont/cpi> {
          ?cat_ rdfs:label ?vtyname0_ .
        }
        BIND (STR(?vtyname0_) AS ?vtyname_)
      }
      UNION
      {
        ?vty_ java:name ?vtyname_ .
      }
      OPTIONAL {
        ?vty_ java:dimensions ?dims_ .
      }
    }  GROUP BY ?dtor_ ?vtyname_ ?dims_
  }
  {
    SELECT DISTINCT ?meth ?mname ?msig ?cfqn ?ver ?loc
    WHERE {
      ?meth a java:MethodOrConstructor ;
            java:inTypeDeclaration ?tdecl ;
            java:name ?mname ;
            java:fullyQualifiedName ?mfqn ;
            java:signature ?msig .

      ?tdecl a java:TypeDeclaration ;
             java:fullyQualifiedName ?cfqn ;
             src:inFile/src:location ?loc ;
             ver:version ?ver .

    } GROUP BY ?meth ?mname ?msig ?cfqn ?ver ?loc
  }
  {
    SELECT DISTINCT ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?loc_
    WHERE {
      ?meth_ a java:MethodOrConstructor ;
             java:inTypeDeclaration ?tdecl_ ;
             java:name ?mname_ ;
             java:fullyQualifiedName ?mfqn_ ;
             java:signature ?msig_ .

      ?tdecl_ a java:TypeDeclaration ;
              java:fullyQualifiedName ?cfqn_ ;
              src:inFile/src:location ?loc_ ;
              ver:version ?ver_ .

    } GROUP BY ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?loc_
  }
  ?ver ver:next ?ver_ .
  OPTIONAL {
    ?dtor java:identOffset ?offset ;
          java:identLength ?length .
    ?dtor_ java:identOffset ?offset_ ;
           java:identLength ?length_ .
  }
}
}
'''

RA_QUERY = '''DEFINE input:inference "ont.cpi"
PREFIX ver:  <%(ver_ns)s>
PREFIX jref: <%(jref_ns)s>
PREFIX java: <%(java_ns)s>
PREFIX src:  <%(src_ns)s>

SELECT DISTINCT ?vname ?vtyname ?vname_ ?vtyname_ ?dims ?dims_
                ?cfqn ?cfqn_ ?ver ?ver_
WHERE {
GRAPH <%(graph_uri)s> {
[] a jref:RenameField ;
   a ?ref ;
   jref:originalField ?dtor;
   jref:modifiedField ?dtor_;
   jref:originalFieldName ?vname ;
   jref:modifiedFieldName ?vname_ ;
   jref:originalClass ?tdecl ;
   jref:modifiedClass ?tdecl_ .
  {
    SELECT DISTINCT ?dtor ?vtyname ?dims
    WHERE {
      ?dtor src:parent ?decl .
      ?decl src:child1 ?vty .

      ?vty a java:Type ;
           a ?cat OPTION (INFERENCE NONE) .
      {
        GRAPH <http://codinuum.com/ont/cpi> {
          ?cat rdfs:label ?vtyname0 .
        }
        BIND (STR(?vtyname0) AS ?vtyname)
      }
      UNION
      {
        ?vty java:name ?vtyname .
      }
      OPTIONAL {
        ?vty java:dimensions ?dims .
      }
    }  GROUP BY ?dtor ?vtyname ?dims
  }
  {
    SELECT DISTINCT ?dtor_ ?vtyname_ ?dims_
    WHERE {
      ?dtor_ src:parent ?decl_ .
      ?decl_ src:child1 ?vty_ .

      ?vty_ a java:Type ;
            a ?cat_ OPTION (INFERENCE NONE) .
      {
        GRAPH <http://codinuum.com/ont/cpi> {
          ?cat_ rdfs:label ?vtyname0_ .
        }
        BIND (STR(?vtyname0_) AS ?vtyname_)
      }
      UNION
      {
        ?vty_ java:name ?vtyname_ .
      }
      OPTIONAL {
        ?vty_ java:dimensions ?dims_ .
      }
    }  GROUP BY ?dtor_ ?vtyname_ ?dims_
  }
  {
    SELECT DISTINCT ?tdecl ?cfqn ?ver
    WHERE {
      ?tdecl a java:TypeDeclaration ;
             java:fullyQualifiedName ?cfqn ;
             ver:version ?ver .

    } GROUP BY ?tdecl ?cfqn ?ver
  }
  {
    SELECT DISTINCT ?tdecl_ ?cfqn_ ?ver_
    WHERE {
      ?tdecl_ a java:TypeDeclaration ;
              java:fullyQualifiedName ?cfqn_ ;
              ver:version ?ver_ .

    } GROUP BY ?tdecl_ ?cfqn_ ?ver_
  }
  ?ver ver:next ?ver_ .
}
}
'''

CRT_QUERY = '''DEFINE input:inference "ont.cpi"
PREFIX ver:  <%(ver_ns)s>
PREFIX jref: <%(jref_ns)s>
PREFIX java: <%(java_ns)s>

SELECT DISTINCT ?rtyname ?rtyname_ ?dims ?dims_
                ?mname ?msig ?cfqn ?mname_ ?msig_ ?abst_ ?cfqn_ ?ver ?ver_
WHERE {
GRAPH <%(graph_uri)s> {
[] a jref:ChangeReturnType ;
   a ?ref ;
   jref:originalType ?rty ;
   jref:modifiedType ?rty_ ;
   jref:originalMethod ?meth ;
   jref:modifiedMethod ?meth_ .
  {
    SELECT DISTINCT ?rty ?rtyname ?dims
    WHERE {
      ?rty a java:Type ;
           a ?cat OPTION (INFERENCE NONE) .
      {
        GRAPH <http://codinuum.com/ont/cpi> {
          ?cat rdfs:label ?rtyname0 .
        }
        BIND (STR(?rtyname0) AS ?rtyname)
      }
      UNION
      {
        ?rty java:name ?rtyname .
      }
      OPTIONAL {
        ?rty java:dimensions ?dims .
      }
    }  GROUP BY ?rty ?rtyname ?dims
  }
  {
    SELECT DISTINCT ?rty_ ?rtyname_ ?dims_
    WHERE {
      ?rty_ a java:Type ;
            a ?cat_ OPTION (INFERENCE NONE) .
      {
        GRAPH <http://codinuum.com/ont/cpi> {
          ?cat_ rdfs:label ?rtyname0_ .
        }
        BIND (STR(?rtyname0_) AS ?rtyname_)
      }
      UNION
      {
        ?rty_ java:name ?rtyname_ .
      }
      OPTIONAL {
        ?rty_ java:dimensions ?dims_ .
      }
    }  GROUP BY ?rty_ ?rtyname_ ?dims_
  }
  {
    SELECT DISTINCT ?meth ?mname ?msig ?cfqn ?ver
    WHERE {
      ?meth a java:MethodOrConstructor ;
            java:inTypeDeclaration ?tdecl ;
            java:name ?mname ;
            java:fullyQualifiedName ?mfqn ;
            java:signature ?msig .

      ?tdecl a java:TypeDeclaration ;
             java:fullyQualifiedName ?cfqn ;
             ver:version ?ver .

    } GROUP BY ?meth ?mname ?msig ?cfqn ?ver
  }
  {
    SELECT DISTINCT ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?abst_
    WHERE {
      ?meth_ a java:MethodOrConstructor ;
             java:inTypeDeclaration ?tdecl_ ;
             java:name ?mname_ ;
             java:fullyQualifiedName ?mfqn_ ;
             java:signature ?msig_ .

      ?tdecl_ a java:TypeDeclaration ;
              java:fullyQualifiedName ?cfqn_ ;
              ver:version ?ver_ .

      OPTIONAL {
        ?meth_ java:isAbstract ?abst_ .
      }

    } GROUP BY ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?abst_
  }
  ?ver ver:next ?ver_ .
}
}
'''

CPT_QUERY = '''DEFINE input:inference "ont.cpi"
PREFIX ver:  <%(ver_ns)s>
PREFIX jref: <%(jref_ns)s>
PREFIX java: <%(java_ns)s>

SELECT DISTINCT ?pname ?ptyname ?pname_ ?ptyname_ ?dims ?dims_
                ?mname ?msig ?cfqn ?mname_ ?msig_ ?abst_ ?cfqn_ ?ver ?ver_
WHERE {
GRAPH <%(graph_uri)s> {
?r a jref:ChangeParameterType ;
   a ?ref ;
   jref:originalTypeName ?ptyname;
   jref:modifiedTypeName ?ptyname_;
   jref:originalParameterName ?pname ;
   jref:modifiedParameterName ?pname_ ;
   jref:originalMethod ?meth ;
   jref:modifiedMethod ?meth_ .

  OPTIONAL {
    ?r jref:originalTypeDims ?dims .
  }
  OPTIONAL {
    ?r jref:modifiedTypeDims ?dims_ .
  }
  {
    SELECT DISTINCT ?meth ?mname ?msig ?cfqn ?ver
    WHERE {
      ?meth a java:MethodOrConstructor ;
            java:inTypeDeclaration ?tdecl ;
            java:name ?mname ;
            java:fullyQualifiedName ?mfqn ;
            java:signature ?msig .

      ?tdecl a java:TypeDeclaration ;
             java:fullyQualifiedName ?cfqn ;
             ver:version ?ver .

    } GROUP BY ?meth ?mname ?msig ?cfqn ?ver
  }
  {
    SELECT DISTINCT ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?abst_
    WHERE {
      ?meth_ a java:MethodOrConstructor ;
             java:inTypeDeclaration ?tdecl_ ;
             java:name ?mname_ ;
             java:fullyQualifiedName ?mfqn_ ;
             java:signature ?msig_ .

      ?tdecl_ a java:TypeDeclaration ;
              java:fullyQualifiedName ?cfqn_ ;
              ver:version ?ver_ .

      OPTIONAL {
        ?meth_ java:isAbstract ?abst_ .
      }

    } GROUP BY ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?abst_
  }
  ?ver ver:next ?ver_ .
}
}
'''

CVT_QUERY = '''DEFINE input:inference "ont.cpi"
PREFIX ver:  <%(ver_ns)s>
PREFIX jref: <%(jref_ns)s>
PREFIX java: <%(java_ns)s>

SELECT DISTINCT ?vname ?vtyname ?vname_ ?vtyname_ ?dims ?dims_
                ?mname ?msig ?cfqn ?mname_ ?msig_ ?cfqn_ ?ver ?ver_
WHERE {
GRAPH <%(graph_uri)s> {
?r a jref:ChangeVariableType ;
   a ?ref ;
   jref:originalTypeName ?vtyname;
   jref:modifiedTypeName ?vtyname_;
   jref:originalVariableName ?vname ;
   jref:modifiedVariableName ?vname_ ;
   jref:originalMethod ?meth ;
   jref:modifiedMethod ?meth_ .

  OPTIONAL {
    ?r jref:originalTypeDims ?dims .
  }
  OPTIONAL {
    ?r jref:modifiedTypeDims ?dims_ .
  }
  {
    SELECT DISTINCT ?meth ?mname ?msig ?cfqn ?ver
    WHERE {
      ?meth a java:MethodOrConstructor ;
            java:inTypeDeclaration ?tdecl ;
            java:name ?mname ;
            java:fullyQualifiedName ?mfqn ;
            java:signature ?msig .

      ?tdecl a java:TypeDeclaration ;
             java:fullyQualifiedName ?cfqn ;
             ver:version ?ver .

    } GROUP BY ?meth ?mname ?msig ?cfqn ?ver
  }
  {
    SELECT DISTINCT ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_
    WHERE {
      ?meth_ a java:MethodOrConstructor ;
             java:inTypeDeclaration ?tdecl_ ;
             java:name ?mname_ ;
             java:fullyQualifiedName ?mfqn_ ;
             java:signature ?msig_ .

      ?tdecl_ a java:TypeDeclaration ;
              java:fullyQualifiedName ?cfqn_ ;
              ver:version ?ver_ .

    } GROUP BY ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_
  }
  ?ver ver:next ?ver_ .
}
}
'''

CAT_QUERY = '''DEFINE input:inference "ont.cpi"
PREFIX ver:  <%(ver_ns)s>
PREFIX jref: <%(jref_ns)s>
PREFIX java: <%(java_ns)s>

SELECT DISTINCT ?vname ?vtyname ?vname_ ?vtyname_ ?dims ?dims_
                ?cfqn ?cfqn_ ?ver ?ver_
WHERE {
GRAPH <%(graph_uri)s> {
?r a jref:ChangeFieldType ;
   a ?ref ;
   jref:originalTypeName ?vtyname;
   jref:modifiedTypeName ?vtyname_;
   jref:originalFieldName ?vname ;
   jref:modifiedFieldName ?vname_ ;
   jref:originalClass ?tdecl ;
   jref:modifiedClass ?tdecl_ .

  OPTIONAL {
    ?r jref:originalTypeDims ?dims .
  }
  OPTIONAL {
    ?r jref:modifiedTypeDims ?dims_ .
  }
  {
    SELECT DISTINCT ?tdecl ?cfqn ?ver
    WHERE {
      ?tdecl a java:TypeDeclaration ;
             java:fullyQualifiedName ?cfqn ;
             ver:version ?ver .

    } GROUP BY ?tdecl ?cfqn ?ver
  }
  {
    SELECT DISTINCT ?tdecl_ ?cfqn_ ?ver_
    WHERE {
      ?tdecl_ a java:TypeDeclaration ;
              java:fullyQualifiedName ?cfqn_ ;
              ver:version ?ver_ .

    } GROUP BY ?tdecl_ ?cfqn_ ?ver_
  }
  ?ver ver:next ?ver_ .
}
}
'''

EV_QUERY = '''DEFINE input:inference "ont.cpi"
PREFIX ver:  <%(ver_ns)s>
PREFIX jref: <%(jref_ns)s>
PREFIX java: <%(java_ns)s>
PREFIX src:  <%(src_ns)s>

SELECT DISTINCT ?vname_ ?vtyname_ ?dims_
                ?mname ?msig ?cfqn ?mname_ ?msig_ ?cfqn_ ?ver ?ver_
                ?offset ?length ?offset_ ?length_ ?loc ?loc_
WHERE {
GRAPH <%(graph_uri)s> {
[] a jref:ExtractVariable ;
   a ?ref ;
   jref:originalExpr ?expr ;
   jref:movedExpr ?expr_ ;
   jref:extractedDtor ?dtor_ ;
   jref:extractedVariableName ?vname_ ;
   jref:originalMethod ?meth ;
   jref:modifiedMethod ?meth_ .
  {
    SELECT DISTINCT ?decl_ ?vtyname_ ?dims_
    WHERE {
      ?dtor_ src:parent ?decl_ .
      ?decl_ src:child1 ?vty_ .
      ?vty_ a java:Type ;
            a ?cat_ OPTION (INFERENCE NONE) .
      {
        GRAPH <http://codinuum.com/ont/cpi> {
          ?cat_ rdfs:label ?vtyname0_ .
        }
        BIND (STR(?vtyname0_) AS ?vtyname_)
      }
      UNION
      {
        ?vty_ java:name ?vtyname_ .
      }
      OPTIONAL {
        ?vty_ java:dimensions ?dims_ .
      }
    }  GROUP BY ?dtor_ ?vtyname_ ?dims_
  }
  {
    SELECT DISTINCT ?meth ?mname ?msig ?cfqn ?ver ?loc
    WHERE {
      ?meth a java:MethodOrConstructor ;
            java:inTypeDeclaration ?tdecl ;
            java:name ?mname ;
            java:fullyQualifiedName ?mfqn ;
            java:signature ?msig .

      ?tdecl a java:TypeDeclaration ;
             java:fullyQualifiedName ?cfqn ;
             src:inFile/src:location ?loc ;
             ver:version ?ver .

    } GROUP BY ?meth ?mname ?msig ?cfqn ?ver ?loc
  }
  {
    SELECT DISTINCT ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?loc_
    WHERE {
      ?meth_ a java:MethodOrConstructor ;
             java:inTypeDeclaration ?tdecl_ ;
             java:name ?mname_ ;
             java:fullyQualifiedName ?mfqn_ ;
             java:signature ?msig_ .

      ?tdecl_ a java:TypeDeclaration ;
              java:fullyQualifiedName ?cfqn_ ;
              src:inFile/src:location ?loc_ ;
              ver:version ?ver_ .

    } GROUP BY ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?loc_
  }
  ?ver ver:next ?ver_ .
  OPTIONAL {
    ?expr java:exprOffset ?offset ;
           java:exprLength ?length .
    ?expr_ java:exprOffset ?offset_ ;
           java:exprLength ?length_ .
  }
}
}
'''


IV_QUERY = '''DEFINE input:inference "ont.cpi"
PREFIX ver:  <%(ver_ns)s>
PREFIX jref: <%(jref_ns)s>
PREFIX java: <%(java_ns)s>
PREFIX src:  <%(src_ns)s>

SELECT DISTINCT ?vname ?vtyname ?dims
                ?mname ?msig ?cfqn ?mname_ ?msig_ ?cfqn_ ?ver ?ver_
                ?offset ?length ?offset_ ?length_ ?loc ?loc_
WHERE {
GRAPH <%(graph_uri)s> {
[] a jref:ExtractVariable ;
   a ?ref ;
   jref:originalExpr ?expr ;
   jref:movedExpr ?expr_ ;
   jref:eliminatedDtor ?dtor ;
   jref:eliminatedVariableName ?vname ;
   jref:originalMethod ?meth ;
   jref:modifiedMethod ?meth_ .
  {
    SELECT DISTINCT ?decl ?vtyname ?dims
    WHERE {
      ?dtor src:parent ?decl .
      ?decl src:child1 ?vty .
      ?vty a java:Type ;
           a ?cat OPTION (INFERENCE NONE) .
      {
        GRAPH <http://codinuum.com/ont/cpi> {
          ?cat rdfs:label ?vtyname0 .
        }
        BIND (STR(?vtyname0) AS ?vtyname)
      }
      UNION
      {
        ?vty java:name ?vtyname .
      }
      OPTIONAL {
        ?vty java:dimensions ?dims .
      }
    }  GROUP BY ?dtor ?vtyname ?dims
  }
  {
    SELECT DISTINCT ?meth ?mname ?msig ?cfqn ?ver ?loc
    WHERE {
      ?meth a java:MethodOrConstructor ;
            java:inTypeDeclaration ?tdecl ;
            java:name ?mname ;
            java:fullyQualifiedName ?mfqn ;
            java:signature ?msig .

      ?tdecl a java:TypeDeclaration ;
             java:fullyQualifiedName ?cfqn ;
             src:inFile/src:location ?loc ;
             ver:version ?ver .

    } GROUP BY ?meth ?mname ?msig ?cfqn ?ver ?loc
  }
  {
    SELECT DISTINCT ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?loc_
    WHERE {
      ?meth_ a java:MethodOrConstructor ;
             java:inTypeDeclaration ?tdecl_ ;
             java:name ?mname_ ;
             java:fullyQualifiedName ?mfqn_ ;
             java:signature ?msig_ .

      ?tdecl_ a java:TypeDeclaration ;
              java:fullyQualifiedName ?cfqn_ ;
              src:inFile/src:location ?loc_ ;
              ver:version ?ver_ .

    } GROUP BY ?meth_ ?mname_ ?msig_ ?cfqn_ ?ver_ ?loc_
  }
  ?ver ver:next ?ver_ .
  OPTIONAL {
    ?expr java:exprOffset ?offset ;
           java:exprLength ?length .
    ?expr_ java:exprOffset ?offset_ ;
           java:exprLength ?length_ .
  }
}
}
'''


QUERY_TBL = {
    RENAME_METHOD: RM_QUERY,
    RENAME_PARAMETER: RP_QUERY,
    RENAME_VARIABLE: RV_QUERY,
    RENAME_ATTRIBUTE: RA_QUERY,
    CHANGE_RETURN_TYPE: CRT_QUERY,
    CHANGE_PARAMETER_TYPE: CPT_QUERY,
    CHANGE_VARIABLE_TYPE: CVT_QUERY,
    CHANGE_ATTRIBUTE_TYPE: CAT_QUERY,

    EXTRACT_VARIABLE: EV_QUERY,
    INLINE_VARIABLE: IV_QUERY,
}
