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


To adjust the generated SHACL shapes with corresponding RML mapping files:

```
$ python XSDtoSHACL.py XSD_FILE -R RML_PATH/DICTIONARY_PATH
```

For example, if you execute the following:

```
$ python python main.py usecase/RINF/RINF-metadata.xsd -r usecase\RINF\mappings
```

The generated shape file will then be located here: usecase/RINF/RINF-metadata.xsd.shape.ttl AND RINF-metadata.xsd.shape.ttl.adjustment.ttl

