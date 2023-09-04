import rdflib
from rdflib import Namespace, URIRef
import pandas as pd
import argparse
import os

class SHACLMetric:
    def __init__(self, ground_truth, predicted, mapping):
        self.RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        self.SHACL = Namespace("http://www.w3.org/ns/shacl#")
        self.RML = Namespace("http://semweb.mmlab.be/ns/rml#")
        self.RR = Namespace("http://www.w3.org/ns/r2rml#")

        #sh:class to be added 
        self.constraints_list = [self.SHACL.datatype, self.SHACL.nodeKind, self.SHACL.minCount, self.SHACL.maxCount, self.SHACL.minLength, self.SHACL.maxLength, self.SHACL.minExclusive, self.SHACL.maxExclusive, self.SHACL.minInclusive, self.SHACL.maxInclusive, self.SHACL.pattern, self.SHACL.uniqueLang]
        self.constraints_list.extend([self.SHACL["in"], self.SHACL.hasValue, self.SHACL.equals, self.SHACL.disjoint, self.SHACL.lessThan, self.SHACL.lessThanOrEquals, self.SHACL["not"], self.SHACL["and"], self.SHACL["or"], self.SHACL.xone])
        self.gt_property_shape_list = []
        self.pd_property_shape_list = []
        
        if isinstance(ground_truth, rdflib.Graph):
            self.ground_truth = ground_truth
        elif isinstance(ground_truth, str):
            self.ground_truth = rdflib.Graph().parse(ground_truth, format='turtle')

        if isinstance(predicted, rdflib.Graph):
            self.predicted = predicted
        elif isinstance(predicted, str):
            self.predicted = rdflib.Graph().parse(predicted, format='turtle')

        if isinstance(mapping, rdflib.Graph):
            self.mapping = mapping
        elif isinstance(mapping, str) and mapping.endswith(".ttl"):
            self.mapping = rdflib.Graph().parse(mapping, format='turtle')
        elif isinstance(mapping, list):
            self.mapping = rdflib.Graph()
            for path in mapping:
                self.mapping.parse(path, format='turtle')

        for subject, _, t in self.ground_truth.triples((None, self.RDF.type, self.SHACL.PropertyShape)):
            self.gt_property_shape_list.append(subject)
        for _,_,bn in self.ground_truth.triples((None, self.SHACL.property, None)):
            self.gt_property_shape_list.append(bn)
        for subject, _, t in self.predicted.triples((None, self.RDF.type, self.SHACL.PropertyShape)):
            self.pd_property_shape_list.append(subject)

    def parseRML(self):
        #Get all subject class and predicate from mapping
        self.class_predicate = set()
        self.reference = set()
        
        for o in self.mapping.objects(None, self.RR.constant):
            if isinstance(o, rdflib.term.URIRef) and o not in self.class_predicate:
                self.class_predicate.add(o)
            elif isinstance(o, str) and o.startswith("http") and o not in self.class_predicate:
                self.class_predicate.add(URIRef(o))

        for o in self.mapping.objects(None, self.RR["class"]):
            if isinstance(o, rdflib.term.URIRef) and o not in self.class_predicate:
                self.class_predicate.add(o)
            elif isinstance(o, str) and o.startswith("http") and o not in self.class_predicate:
                self.class_predicate.add(URIRef(o))

        for o in self.mapping.objects(None, self.RR.predicate):
            if isinstance(o, rdflib.term.URIRef) and o not in self.class_predicate:
                self.class_predicate.add(o)
            elif isinstance(o, str) and o.startswith("http") and o not in self.class_predicate:
                self.class_predicate.add(URIRef(o))

        for o in self.mapping.objects(None, self.RR.predicateObjectMap):
            om = self.mapping.value(o, self.RR.objectMap)
            pm = self.mapping.value(o, self.RR.predicateMap)
            # if om has reference instead of tempalte or constant
            for r in self.mapping.objects(om, self.RML.reference):
                self.reference.add(self.mapping.value(pm, self.RR.constant))
    
    def target_declaration_coverage_score(self, classDefined = None):
        new_classDefined = set()
        if classDefined:
            for i in classDefined:
                new_classDefined.add(i)
            for i in self.class_predicate:
                new_classDefined.add(i)
        predicated_targets, ground_truth_targets = set(), set()
        for target in [self.SHACL.targetClass, self.SHACL.targetNode, self.SHACL.targetObjectsOf, self.SHACL.targetSubjectsOf]:
            for o in self.ground_truth.objects(None, target):
                ground_truth_targets.add(o)
            for o in self.predicted.objects(None, target):
                predicated_targets.add(o)

        # the common target between ground truth and predicted
        R_T = ground_truth_targets.intersection(new_classDefined)
        # the common target between ground truth and predicted
        P_T = ground_truth_targets.intersection(predicated_targets)
        # the differnce between RT and PT
        D_T = R_T.difference(P_T)
        print("C_T", len(ground_truth_targets.intersection(predicated_targets)))
        if classDefined:
            return len(ground_truth_targets), len(predicated_targets),len(ground_truth_targets.intersection(new_classDefined)), len(predicated_targets.intersection(new_classDefined))
        return len(ground_truth_targets), len(predicated_targets),len(ground_truth_targets.intersection(self.class_predicate)), len(predicated_targets.intersection(self.class_predicate))


    def property_path_coverage_score(self):
        predicated_property_paths, ground_truth_property_paths = set(), set()
        for s,_,o in self.ground_truth.triples((None, self.SHACL.path,None)):
            if s in self.gt_property_shape_list:
                ground_truth_property_paths.add(o)
        for s,_,o in self.predicted.triples((None, self.SHACL.path,None)):
            if s in self.pd_property_shape_list:
                predicated_property_paths.add(o)


        R_T = ground_truth_property_paths.intersection(self.class_predicate)
        # the common target between ground truth and predicted
        P_T = ground_truth_property_paths.intersection(predicated_property_paths)
        # the differnce between RT and PT
        D_T = R_T.difference(P_T)
        print("C_P", len(ground_truth_property_paths.intersection(predicated_property_paths))), len(ground_truth_property_paths.intersection(self.class_predicate))

        return len(ground_truth_property_paths), len(predicated_property_paths), len(ground_truth_property_paths.intersection(self.class_predicate)), len(predicated_property_paths.intersection(self.class_predicate))

name = ["RINF-contact-line-systems","RINF-etcs-levels","RINF-meso-net-elements","RINF-meso-net-relations","RINF-op-tracks","RINF-operational-points"]
name.extend(["RINF-platforms","RINF-sections-of-line","RINF-sidings","RINF-sol-tracks"])
name.extend(["RINF-train-detection-systems","RINF-tunnels"])

for case in name:
    ground_truth = f"usecases/RINF/shapes/{case}.ttl"
    predicted = f"usecases/RINF/RINF-metadata.xsd.shape.ttl.{case}.yml.adjustment.ttl"
    mapping = f"usecases/RINF/mappings//{case}.yml.ttl"

    metric = SHACLMetric(ground_truth, predicted, mapping)
    metric.parseRML()

    print(f"##### Start calculate metric for {case}")

    num_gt, num_pd, inRML, pd_inRML = metric.target_declaration_coverage_score()

    print("R/T: ",inRML,"/",num_gt)
    print("R/T': ",pd_inRML,"/",num_pd)

    num_gt, num_pd, inRML, pd_inRML = metric.property_path_coverage_score()

    print("R/P: ", inRML,"/",num_gt)
    print("R/P': ", pd_inRML,"/",num_pd)
