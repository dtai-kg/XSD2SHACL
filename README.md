# XSD2SHACL

See translation and implementation detail in report.

## Prerequisite

Install the required dependencies:

```
$ pip install -r requirements.txt
```

## Usage

To translate XML Schema to SHACL shapes:

```
$ python XSDtoSHACL.py XSD_FILE
```

For example, if you execute the following:

```
$ python XSDtoSHACL.py testcase/example.xml
```

The generated shape file will then be located here: testcase/example.xml.shape.ttl

## Translation correspondences:

<div align="center">
  <img src="image/image.png">
</div>


## To Do
像shapes一样加一个trackPaths[]，然后再shape pop后面另起一个elemetn的path pop，先从简单的假想一个，应该是每遍历结束一个element pop yige出去
- [ ] complexType也直接引用翻译吧跟simpleType，！！！！！改动！别这样了！！！改回原来，complexType还是生成NS吧省好多事情，能生成这种NS的也都是name唯一的，不影响。XPATH可以加入complexType杂质用来redict无所谓的
- [ ] multiple constriants error, see RINF-metadata.xsd. Add XPath track info in subject to solve this problem and do pre-adjustment.

- [ ] use for cardinality

- [ ] attributeGroup with ref, add multiple ps together
- [ ] Add annotation ->appinfo documentation as comment after create RDF data, insert this sentences, if the annotation is inside shape, then add it as description following string template
- [ ] complexType with simpleContent should be considered as PS, see test case todo1.xsd . NS cannot has datatype.
- [ ] complexContent with xsd:anyType see test case todo2.xsd
- [ ] fix restriction on complexType/complexContent
- [ ] attribute language
- [ ] fix element without type
- [ ] Evaluation 



