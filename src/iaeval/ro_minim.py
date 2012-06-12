# ro_minim.py

"""
Research Object minimum information model access functions
"""

import re
import urlparse
import logging

log = logging.getLogger(__name__)

import rdflib
import rdflib.namespace

from rocommand import ro_manifest
from rocommand import ro_namespaces
from rocommand.ro_namespaces import RDF, RDFS

minimnsuri = rdflib.URIRef("http://purl.org/minim/minim#")
MINIM      = ro_namespaces.makeNamespace(minimnsuri,
            [ "Constraint", "Model", "Requirement", "RequirementRule"
            , "SoftwareEnvironmentRule", "DataRequirementRule", "ContentMatchRequirementRule"
            , "hasConstraint", "forPurpose", "onResource", "toModel"
            , "hasMustRequirement", "hasShouldRequirement", "hasMayRequirement", "hasRequirement"
            , "derives", "reports", "isDerivedBy"
            , "show", "showpass", "showfail"
            , "aggregates"
            , "command", "response"
            , "forall", "exists", "aggregatesTemplate"
            , "minimallySatisfies", "nominallySatisfies", "fullySatisfies"
            # Result properties
            , "satisfied", "missingMay", "missingShould", "missingMust"
            , "testedConstraint", "testedPurpose", "testedTarget"
            , "minimUri", "modelUri"
            #, "tryRule"
            , "tryRequirement"
            ])

resultnsuri = rdflib.URIRef("http://www.w3.org/2001/sw/DataAccess/tests/result-set#")
RESULT      = ro_namespaces.makeNamespace(resultnsuri,
            [ "binding", "variable", "value"
            ])

def getElementUri(minimbase, elemname):
    """
    Returns URI of element in Minim file
    
    minimbase   is the URI of the Minim file containing the required element
    elemname    is the relative URI of the element - commonly a fragment identifier
    """
    return rdflib.URIRef(urlparse.urljoin(str(minimbase), elemname))

def readMinimGraph(minimuri):
    """
    Read Minim file, return RDF Graph.
    """
    minimgraph = rdflib.Graph()
    minimgraph.parse(minimuri)
    return minimgraph

def getConstraints(minimgraph):
    for (target, constraint) in minimgraph.subject_objects(predicate=MINIM.hasConstraint):
        c = {'target': target, 'uri': constraint}
        c['purpose']  = minimgraph.value(subject=constraint, predicate=MINIM.forPurpose)
        c['resource'] = minimgraph.value(subject=constraint, predicate=MINIM.onResource)
        c['model']    = minimgraph.value(subject=constraint, predicate=MINIM.toModel)
        yield c
    return

def getConstraint(minimgraph, roref, target_ref, purpose_regex_string):
    target  = target_ref and ro_manifest.getComponentUri(roref, target_ref)
    purpose = purpose_regex_string and re.compile(purpose_regex_string)
    for c in getConstraints(minimgraph):
        if ( ( not target  or target == c['target'] ) and
             ( not purpose or purpose.match(c['purpose']) ) ):
            return c
    return None

def getModels(minimgraph, modeluri=None):
    for (model, p, o) in minimgraph.triples( (modeluri, RDF.type, MINIM.Model) ):
        m = {'uri': model}
        m['label']   = minimgraph.value(subject=model, predicate=RDFS.label)
        m['comment'] = minimgraph.value(subject=model, predicate=RDFS.comment)
        yield m
    return

def getModel(minimgraph, modeluri):
    for m in getModels(minimgraph, modeluri=modeluri):
        return m
    return None

def getRequirements(minimgraph, modeluri):
    def matchRequirement((s, p, o), reqp, reqval):
        req = None
        if p == reqp:
            req = (
                { 'uri':    o
                , 'model':  s
                , 'level':  reqval
                , 'label':  minimgraph.value(subject=o, predicate=RDFS.label)
                })
            ruleuri = minimgraph.value(subject=o, predicate=MINIM.isDerivedBy)
            assert ruleuri, "Requirement %s has no minim:isDerivedBy rule"%(str(o))
            rule = (
                { 'derives':    minimgraph.value(subject=ruleuri, predicate=MINIM.derives) 
                , 'show':       minimgraph.value(subject=ruleuri, predicate=MINIM.show) 
                , 'showpass':   minimgraph.value(subject=ruleuri, predicate=MINIM.showpass)
                , 'showfail':   minimgraph.value(subject=ruleuri, predicate=MINIM.showfail)
                })
            ruletype = minimgraph.value(subject=ruleuri, predicate=RDF.type)
            if ruletype == MINIM.DataRequirementRule:
                rule['aggregates']  = minimgraph.value(subject=ruleuri, predicate=MINIM.aggregates)
                req['datarule'] = rule
            elif ruletype == MINIM.SoftwareEnvironmentRule:
                rule['command']  = minimgraph.value(subject=ruleuri, predicate=MINIM.command)
                rule['response'] = minimgraph.value(subject=ruleuri, predicate=MINIM.response)
                req['softwarerule'] = rule
            elif ruletype == MINIM.ContentMatchRequirementRule:
                rule['forall']   = minimgraph.value(subject=ruleuri, predicate=MINIM.forall)
                rule['exists']   = minimgraph.value(subject=ruleuri, predicate=MINIM.exists)
                rule['template'] = minimgraph.value(subject=ruleuri, predicate=MINIM.aggregatesTemplate)
                req['contentmatchrule'] = rule
            else:
                assert False, "Unrecognized rule type %s for requirement %s"%(str(ruletype), str(o))
        return req
    for stmt in minimgraph.triples( (modeluri, None, None) ):
        pred_level_list = (
            [ (MINIM.hasMustRequirement, "MUST")
            , (MINIM.hasShouldRequirement, "SHOULD")
            , (MINIM.hasMayRequirement, "MAY")
            ])
        for (pred, level) in pred_level_list:
            r = matchRequirement(stmt, pred, level)
            if r:
                yield r
                break
    return

# End.
