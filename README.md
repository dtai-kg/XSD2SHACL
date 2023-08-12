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
- [ ] complexType with simpleContent should be considered as PS, see test case todo1.xsd . NS cannot has datatype.
- [ ] complexContent with xsd:anyType see test case todo2.xsd
- [ ] fix restriction on complexType/complexContent
- [ ] translate import and include

- [ ] fix element without type => type is required ?
- [ ] attribute language => Add languageIn? Or to which shape? To be disccused 
- [ ] Evaluation 



