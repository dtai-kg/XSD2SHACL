import rdflib
from rdflib import Namespace

class SHACLMetric:
    def __init__(self, ground_truth, predicted):
        self.RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        self.SHACL = Namespace("http://www.w3.org/ns/shacl#")

        #sh:class to be added 
        self.constraints_list = [self.SHACL.datatype, self.SHACL.nodeKind, self.SHACL.minCount, self.SHACL.maxCount, self.SHACL.minLength, self.SHACL.maxLength, self.SHACL.minExclusive, self.SHACL.maxExclusive, self.SHACL.minInclusive, self.SHACL.maxInclusive, self.SHACL.pattern, self.SHACL.uniqueLang]
        self.constraint_list = self.constraints_list.extend([self.SHACL["in"], self.SHACL.hasValue, self.SHACL.equals, self.SHACL.disjoint, self.SHACL.lessThan, self.SHACL.lessThanOrEquals, self.SHACL["not"], self.SHACL["and"], self.SHACL["or"], self.SHACL.xone])
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

        for subject, _, t in self.ground_truth.triples((None, self.RDF.type, self.SHACL.PropertyShape)):
            self.gt_property_shape_list.append(subject)
        for _,_,bn in self.ground_truth.triples((None, self.SHACL.property, None)):
            self.gt_property_shape_list.append(bn)
        for subject, _, t in self.predicted.triples((None, self.RDF.type, self.SHACL.PropertyShape)):
            self.pd_property_shape_list.append(subject)
        

    def target_declaration_coverage_score(self):
        predicated_targets, ground_truth_targets = set(), set()
        for target in [self.SHACL.targetClass, self.SHACL.targetNode, self.SHACL.targetObjectsOf, self.SHACL.targetSubjectsOf]:
            for o in self.ground_truth.objects(None, target):
                ground_truth_targets.add(o)
            for o in self.predicted.objects(None, target):
                predicated_targets.add(o)

        recall = self.get_recall(ground_truth_targets, predicated_targets)
        precision = self.get_precision(ground_truth_targets, predicated_targets)
        # f1_score = self.get_F1_score(ground_truth_targets, predicated_targets)
        print("Target declaration coverage score: ")
        print("Recall: " + str(recall))
        print("Precision: " + str(precision))
        # print("F1 score: " + str(f1_score))
        return recall, precision


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

        print("Property path coverage score: ")
        print("Recall: " + str(recall))
        print("Precision: " + str(precision))
        # print("F1 score: " + str(f1_score))
        return recall, precision

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
        print("Referencing relationship coverage score: ")
        print("Recall: " + str(recall))
        print("Precision: " + str(precision))
        # print("F1 score: " + str(f1_score))
        return recall, precision


    def constraints_coverage(self):
        predicated_constraints_dict, ground_truth_constraints_dict = {},{}
        predicated_constraints, ground_truth_constraints = set(), set()
        # Load constraints from ground truth shape that has target and path
        for targetAndpath in [self.SHACL.targetClass, self.SHACL.targetNode, self.SHACL.targetObjectsOf, self.SHACL.targetSubjectsOf, self.SHACL.path]:
            for subject, _, t in self.ground_truth.triples((None, targetAndpath,None)):
                if subject in self.gt_property_shape_list:
                    predicated_constraints = ground_truth_constraints_dict.get(t,set())
                    for cs,sp,co in self.ground_truth.triples((subject, None, None)):
                        if sp in self.constraints_list:
                            predicated_constraints.add((sp,str(co)))
                    ground_truth_constraints_dict[t] = predicated_constraints

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

        print("Constraints coverage score: ")
        print("Recall: " + str(recall))
        print("Precision: " + str(precision))
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
        return len(ground_truth.intersection(predicted)) / len(predicted)

    def get_recall(self, ground_truth, predicted):
        if len(ground_truth) == 0:
            return 0
        return len(ground_truth.intersection(predicted)) / len(ground_truth)


if __name__ == "__main__":
    i = -1
    name = ["RINF-contact-line-systems","RINF-etcs-levels","RINF-meso-net-elements","RINF-meso-net-relations","RINF-op-tracks","RINF-operational-points"]
    name.extend(["RINF-platforms","RINF-sections-of-line","RINF-sidings","RINF-sol-not-applicable","RINF-sol-tracks"])
    name.extend(["RINF-train-detection-systems","RINF-tunnels"])
    ground_truth = "usecase/RINF/shapes/"+name[i]+".ttl"
    predicted = "usecase/RINF/RINF-metadata.xsd.shape.ttl."+name[i]+".yml.adjustment.ttl"
    metric = SHACLMetric(ground_truth, predicted)
    print("##### Start calculate metric for " + name[i])
    metric.target_declaration_coverage_score()
    metric.property_path_coverage_score()
    metric.referencing_relationship_coverage_score()
    metric.constraints_coverage()