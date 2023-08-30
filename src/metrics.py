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

        print("RRRRRRRRRRR",self.reference)
        print("The number of Class and predicate: ", len(self.class_predicate))

    def strictMode(self):
        # delete all property path that not in reference
        for s,p,o in self.ground_truth.triples((None, self.SHACL.path, None)):
            if o not in self.class_predicate:
                self.ground_truth.remove((s,p,o))

        for s,p,o in self.ground_truth.triples((None, self.SHACL.property, None)):
            if o not in self.class_predicate:
                self.ground_truth.remove((s,p,o))

        for s,p,o in self.predicted.triples((None, self.SHACL.path, None)):
            if o not in self.class_predicate:
                self.predicted.remove((s,p,o))

        for s,p,o in self.predicted.triples((None, self.SHACL.property, None)):
            if o not in self.class_predicate:
                self.predicted.remove((s,p,o))
    
    
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

        recall = self.get_recall(ground_truth_targets, predicated_targets)
        precision = self.get_precision(ground_truth_targets, predicated_targets)

        # the common target between ground truth and predicted
        R_T = ground_truth_targets.intersection(new_classDefined)
        # the common target between ground truth and predicted
        P_T = ground_truth_targets.intersection(predicated_targets)
        # the differnce between RT and PT
        D_T = R_T.difference(P_T)
        print("TARGETDDDDDDDDDDDDDDDDDDDDDDDD",len(D_T),D_T)

        # f1_score = self.get_F1_score(ground_truth_targets, predicated_targets)
        # print("Target declaration coverage score: ")
        # print("Recall: " + str(recall))
        # print("Precision: " + str(precision))
        # print("F1 score: " + str(f1_score))
        # print("Difference: ", ground_truth_targets.difference(predicated_targets))
        if classDefined:
            return recall, precision, len(ground_truth_targets), len(predicated_targets),len(ground_truth_targets.intersection(new_classDefined))
        return recall, precision, len(ground_truth_targets), len(predicated_targets),len(ground_truth_targets.intersection(self.class_predicate))


    def property_path_coverage_score(self):
        predicated_property_paths, ground_truth_property_paths = set(), set()
        for s,_,o in self.ground_truth.triples((None, self.SHACL.path,None)):
            if s in self.gt_property_shape_list:
                ground_truth_property_paths.add(o)
        for s,_,o in self.predicted.triples((None, self.SHACL.path,None)):
            if s in self.pd_property_shape_list:
                predicated_property_paths.add(o)

        recall = self.get_recall(ground_truth_property_paths, predicated_property_paths)
        precision = self.get_precision(ground_truth_property_paths, predicated_property_paths)
        # f1_score = self.get_F1_score(ground_truth_property_paths, predicated_property_paths)
        # the common target between ground truth and predicted
        R_T = ground_truth_property_paths.intersection(self.class_predicate)
        # the common target between ground truth and predicted
        P_T = ground_truth_property_paths.intersection(predicated_property_paths)
        # the differnce between RT and PT
        D_T = R_T.difference(P_T)
        print("PROPERTYDDDDDDDDDDDDDDDDDDDDDDDD",len(D_T),D_T)

        # print("Property path coverage score: ")
        # print("Recall: " + str(recall))
        # print("Precision: " + str(precision))
        # print("F1 score: " + str(f1_score))
        # print("Difference PPPPPP: ", ground_truth_property_paths.difference(predicated_property_paths))
        return recall, precision, len(ground_truth_property_paths), len(predicated_property_paths), len(ground_truth_property_paths.intersection(self.class_predicate))

    def referencing_relationship_coverage_score(self):
        predicted_referencing_relationships, ground_truth_referencing_relationships = set(), set()

        for target in [self.SHACL.targetClass, self.SHACL.targetNode, self.SHACL.targetObjectsOf, self.SHACL.targetSubjectsOf]:
            for s in self.ground_truth.subjects(target, None):
                t = self.ground_truth.value(s, target)
                for o in self.ground_truth.objects(s, self.SHACL.property):
                    for path in self.ground_truth.objects(o, self.SHACL.path):
                        ground_truth_referencing_relationships.add((t, path))

        for s in self.ground_truth.subjects(self.SHACL.path, None):
            for o in self.ground_truth.objects(s, self.SHACL.node):
                if (o, self.targetClass, None) in self.ground_truth:
                    node_target = self.ground_truth.value(o, self.targetClass)
                    ground_truth_referencing_relationships.add((o, node_target))
                elif (o, self.targetSubjectsOf, None) in self.ground_truth:
                    node_target = self.ground_truth.value(o, self.targetSubjectsOf)
                    ground_truth_referencing_relationships.add((o, node_target))
                elif (o, self.targetObjectsOf, None) in self.ground_truth:
                    node_target = self.ground_truth.value(o, self.targetObjectsOf)
                    ground_truth_referencing_relationships.add((o, node_target))
                elif (o, self.targetNode, None) in self.ground_truth:
                    node_target = self.ground_truth.value(o, self.targetNode)
                    ground_truth_referencing_relationships.add((o, node_target))
                else:
                    ground_truth_referencing_relationships.add((o, None))

        for target in [self.SHACL.targetClass, self.SHACL.targetNode, self.SHACL.targetObjectsOf, self.SHACL.targetSubjectsOf]:
            for s in self.predicted.subjects(target, None):
                t = self.predicted.value(s, target)
                for o in self.predicted.objects(s, self.SHACL.property):
                    for path in self.predicted.objects(o, self.SHACL.path):
                        predicted_referencing_relationships.add((t, path))
        
        for s in self.predicted.subjects(self.SHACL.path, None):
            for o in self.predicted.objects(s, self.SHACL.node):
                if (o, self.targetClass, None) in self.predicted:
                    node_target = self.predicted.value(o, self.targetClass)
                    predicted_referencing_relationships.add((o, node_target))
                elif (o, self.targetSubjectsOf, None) in self.predicted:
                    node_target = self.predicted.value(o, self.targetSubjectsOf)
                    predicted_referencing_relationships.add((o, node_target))
                elif (o, self.targetObjectsOf, None) in self.predicted:
                    node_target = self.predicted.value(o, self.targetObjectsOf)
                    predicted_referencing_relationships.add((o, node_target))
                elif (o, self.targetNode, None) in self.predicted:
                    node_target = self.predicted.value(o, self.targetNode)
                    predicted_referencing_relationships.add((o, node_target))
                else:
                    predicted_referencing_relationships.add((o, None))

        recall = self.get_recall(ground_truth_referencing_relationships, predicted_referencing_relationships)
        precision = self.get_precision(ground_truth_referencing_relationships, predicted_referencing_relationships)
        # f1_score = self.get_F1_score(ground_truth_referencing_relationships, predicted_referencing_relationships)
        # print("Referencing relationship coverage score: ")
        # print("Recall: " + str(recall))
        # print("Precision: " + str(precision))
        # print("F1 score: " + str(f1_score))
        return recall, precision, len(ground_truth_referencing_relationships), len(predicted_referencing_relationships)


    def constraints_coverage(self):
        predicated_constraints_dict, ground_truth_constraints_dict = {},{}
        predicated_constraints, ground_truth_constraints = set(), set()
        # Load constraints from ground truth shape that has target and path
        for targetAndpath in [self.SHACL.targetClass, self.SHACL.targetNode, self.SHACL.targetObjectsOf, self.SHACL.targetSubjectsOf, self.SHACL.path]:
            for subject, _, t in self.ground_truth.triples((None, targetAndpath,None)):
                if subject in self.gt_property_shape_list:
                    ground_truth_constraints = ground_truth_constraints_dict.get(t,set())
                    for cs,sp,co in self.ground_truth.triples((subject, None, None)):
                        if sp in self.constraints_list:
                            ground_truth_constraints.add((sp,str(co)))
                    ground_truth_constraints_dict[t] = ground_truth_constraints

        # Load constraints from predicted shape that has target and path
        for targetAndpath in [self.SHACL.targetClass, self.SHACL.targetNode, self.SHACL.targetObjectsOf, self.SHACL.targetSubjectsOf, self.SHACL.path]:
            for subject, _, t in self.predicted.triples((None, targetAndpath,None)):
                if subject in self.pd_property_shape_list:
                    predicated_constraints = predicated_constraints_dict.get(t,set())
                    for cs,sp,co in self.predicted.triples((subject, None, None)):
                        if sp in self.constraints_list:
                            predicated_constraints.add((sp,str(co)))
                    if predicated_constraints != set():
                        predicated_constraints_dict[t] = predicated_constraints

        # print("Ground truth constraints: ", ground_truth_constraints_dict)
        # print("Predicated constraints: ", predicated_constraints_dict)
        # return None

        recall_scores, precision_scores, f1_scores = [], [], []
        for t in predicated_constraints_dict:
            if t in ground_truth_constraints_dict:
                predicated_constraints = predicated_constraints.union(predicated_constraints_dict[t])
                ground_truth_constraints = ground_truth_constraints.union(ground_truth_constraints_dict[t])
                recall = self.get_recall(ground_truth_constraints_dict[t], predicated_constraints_dict[t])
                precision = self.get_precision(ground_truth_constraints_dict[t], predicated_constraints_dict[t])
                # f1_score = self.get_F1_score(ground_truth_constraints_dict[t], predicated_constraints_dict[t])
                recall_scores.append(recall)
                precision_scores.append(precision)
                # f1_scores.append(f1_score)
                # print("Constraints coverage score for ", t, recall, precision, f1_score)

        

        if recall_scores == []:
            recall_scores.append(0)
        if precision_scores == []:
            precision_scores.append(0)
        # if f1_scores == []:
        #     f1_scores.append(0)
        recall = sum(recall_scores) / len(recall_scores)
        precision = sum(precision_scores) / len(precision_scores)
        # f1_score = sum(f1_scores) / len(f1_scores)

        # print("Constraints coverage score: ")
        # print("Recall: " + str(recall))
        # print("Precision: " + str(precision))
        # print("F1 score: " + str(f1_score))
        return recall, precision



    def constraints_analysis(self):
        pass

    # def get_F1_score(self, ground_truth, predicted):
    #     if len(predicted) == 0:
    #         return 0

    #     precision = len(ground_truth.intersection(predicted)) / len(predicted)
    #     recall = len(ground_truth.intersection(predicted)) / len(ground_truth)
    #     if precision + recall == 0:
    #         return 0
    #     return 2 * precision * recall / (precision + recall)

    def get_precision(self, ground_truth, predicted):
        ground_truth = set(ground_truth)
        predicted = set(predicted)
        if len(predicted) == 0:
            return 0
        print("#############################PRECISION", len(ground_truth.intersection(predicted)))
        return len(ground_truth.intersection(predicted)) / len(predicted)

    def get_recall(self, ground_truth, predicted):
        if len(ground_truth) == 0:
            return 0
        print("#############################recall", len(ground_truth.intersection(predicted)))
        return len(ground_truth.intersection(predicted)) / len(ground_truth)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Calculate metric for SHACL shapes')
    parser.add_argument("-m", "--mode", type=str, help='Evaluation, RINF, RINF Testing', default='Evaluation')
    parser.add_argument("-n", "--name", type=str, help='name of shape')
    parser.add_argument("-gt", "--ground_truth", type=str, help='gt of shape')
    parser.add_argument("-pd", "--predicted", type=str, help='pd of shape')
    parser.add_argument("-mp", "--mapping", type=str, help='mapping of shape')
    args = parser.parse_args()

    name = ["RINF-contact-line-systems","RINF-etcs-levels","RINF-meso-net-elements","RINF-meso-net-relations","RINF-op-tracks","RINF-operational-points"]
    name.extend(["RINF-platforms","RINF-sections-of-line","RINF-sidings","RINF-sol-tracks"])
    name.extend(["RINF-train-detection-systems","RINF-tunnels"])

    if args.mode == "Evaluation":
        F03 = set()
        F03.add(URIRef("http://data.europa.eu/a4g/ontology#CompetitionNotice"))
        F03.add(URIRef("http://data.europa.eu/a4g/ontology#PlanningNotice"))
        F03.add(URIRef("http://data.europa.eu/a4g/ontology#Business"))
        F03.add(URIRef("http://data.europa.eu/a4g/ontology#ContractAwardNotice"))
        F03.add(URIRef("http://data.europa.eu/a4g/ontology#ResultNotice"))
        TDC_Rec, TDC_Pre, PPC_Rec, PPC_Pre, RRC_Rec, RRC_Pre, CC_Rec, CC_Pre = [], [], [], [], [], [], [], []
        TDC_gt_num, TDC_pd_num, PPC_gt_num, PPC_pd_num, RRC_gt_num, RRC_pd_num, CC_gt_num, CC_pd_num = [], [], [], [], [], [], [], []
        TDC_gt_inRML, PPC_gt_inRML = [], []
        mappings = [args.mapping+"/"+name for name in os.listdir(args.mapping)]
        metric = SHACLMetric(args.ground_truth, args.predicted, mappings)
        metric.parseRML()
        # metric.strictMode()

        print("##### Start calculate metric for " + args.predicted)

        recall, precision, num_gt, num_pd, inRML = metric.target_declaration_coverage_score(F03)
        TDC_Rec.append(round(recall, 2))
        TDC_Pre.append(round(precision, 2))
        TDC_gt_num.append(num_gt)
        TDC_pd_num.append(num_pd)
        TDC_gt_inRML.append(inRML)
        print("The number of target declaration: ", num_gt, num_pd, inRML)

        recall, precision, num_gt, num_pd, inRML = metric.property_path_coverage_score()
        PPC_Rec.append(round(recall, 2))
        PPC_Pre.append(round(precision, 2))
        PPC_gt_num.append(num_gt)
        PPC_pd_num.append(num_pd)
        PPC_gt_inRML.append(inRML)
        print("The number of property path: ", num_gt, num_pd, inRML)

        # recall, precision, num_gt, num_pd = metric.referencing_relationship_coverage_score()
        # RRC_Rec.append(round(recall, 2))
        # RRC_Pre.append(round(precision, 2))
        # RRC_gt_num.append(num_gt)
        # RRC_pd_num.append(num_pd)
        # print("The number of referencing relationship: ", num_gt, num_pd)

        # recall, precision = metric.constraints_coverage()
        # CC_Rec.append(round(recall, 2))
        # CC_Pre.append(round(precision, 2))
        # df = pd.DataFrame({"Name":["ePO_shacl_shapes"], "TDC_Rec":TDC_Rec, "TDC_Pre":TDC_Pre, "TDC_gt_num":TDC_gt_num, "TDC_pd_num":TDC_pd_num, "TDC_inRML":TDC_gt_inRML, "PPC_Rec":PPC_Rec, "PPC_Pre":PPC_Pre, "PPC_gt_num":PPC_gt_num, "PPC_pd_num":PPC_pd_num, "PPC_inRML":PPC_gt_inRML, "RRC_Rec":RRC_Rec, "RRC_Pre":RRC_Pre, "RRC_gt_num":RRC_gt_num, "RRC_pd_num":RRC_pd_num, "CC_Rec":CC_Rec, "CC_Pre":CC_Pre})
        # df.to_csv("usecase/TED/metric.csv", index=False)
        # #Store in excel
        # df.to_excel('usecase/TED/metric.xlsx', index=False)
    
    elif args.mode == "RINF Testing":
        ground_truth = "usecase/RINF/shapes/"+args.name+".ttl"
        predicted = "usecase/RINF/RINF-metadata.xsd.shape.ttl."+args.name+".yml.adjustment.ttl"
        mapping = "usecase/RINF/mappings/"+args.name+".yml.ttl"
        metric = SHACLMetric(ground_truth, predicted,mapping)
        metric.parseRML()
        metric.strictMode()
        print("##### Start calculate metric for " + args.name)
        metric.target_declaration_coverage_score()
        metric.property_path_coverage_score()
        metric.referencing_relationship_coverage_score()
        metric.constraints_coverage()

    elif args.mode == "RINF":

        TDC_Rec, TDC_Pre, PPC_Rec, PPC_Pre, RRC_Rec, RRC_Pre, CC_Rec, CC_Pre = [], [], [], [], [], [], [], []
        TDC_gt_num, TDC_pd_num, PPC_gt_num, PPC_pd_num, RRC_gt_num, RRC_pd_num, CC_gt_num, CC_pd_num = [], [], [], [], [], [], [], []
        TDC_gt_inRML, PPC_gt_inRML = [], []
        for n in name:
            ground_truth = "usecase/RINF/shapes/"+n+".ttl"
            predicted = "usecase/RINF/RINF-metadata.xsd.shape.ttl."+n+".yml.adjustment.ttl"
            mapping = "usecase/RINF/mappings/"+n+".yml.ttl"
            metric = SHACLMetric(ground_truth, predicted, mapping)
            metric.parseRML()

            print("##### Start calculate metric for " + n)

            recall, precision, num_gt, num_pd, inRML = metric.target_declaration_coverage_score()
            TDC_Rec.append(round(recall, 2))
            TDC_Pre.append(round(precision, 2))
            TDC_gt_num.append(num_gt)
            TDC_pd_num.append(num_pd)
            TDC_gt_inRML.append(inRML)

            recall, precision, num_gt, num_pd, inRML = metric.property_path_coverage_score()
            PPC_Rec.append(round(recall, 2))
            PPC_Pre.append(round(precision, 2))
            PPC_gt_num.append(num_gt)
            PPC_pd_num.append(num_pd)
            PPC_gt_inRML.append(inRML)

            # recall, precision, num_gt, num_pd = metric.referencing_relationship_coverage_score()
            # RRC_Rec.append(round(recall, 2))
            # RRC_Pre.append(round(precision, 2))
            # RRC_gt_num.append(num_gt)
            # RRC_pd_num.append(num_pd)

            # recall, precision = metric.constraints_coverage()
            # CC_Rec.append(round(recall, 2))
            # CC_Pre.append(round(precision, 2))
        # df = pd.DataFrame({"Name":name, "TDC_Rec":TDC_Rec, "TDC_Pre":TDC_Pre, "TDC_gt_num":TDC_gt_num, "TDC_pd_num":TDC_pd_num, "TDC_inRML":TDC_gt_inRML, "PPC_Rec":PPC_Rec, "PPC_Pre":PPC_Pre, "PPC_gt_num":PPC_gt_num, "PPC_pd_num":PPC_pd_num, "PPC_inRML":PPC_gt_inRML, "RRC_Rec":RRC_Rec, "RRC_Pre":RRC_Pre, "RRC_gt_num":RRC_gt_num, "RRC_pd_num":RRC_pd_num, "CC_Rec":CC_Rec, "CC_Pre":CC_Pre})
        # df.to_csv("usecase/RINF/metric.csv", index=False)
        # #Store in excel
        # df.to_excel('usecase/RINF/metric.xlsx', index=False)
