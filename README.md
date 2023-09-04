# XSD2SHACL

A tool to generate SHACL shapes from XSD for RDF graphs validation.

## Prerequisite

Install the required dependencies:

```
$ pip install -r requirements.txt
```

## Usage

To translate XSD to SHACL shapes:

```
$ python main.py XSD_FILE
```

Or you can specify the location for storing the generated SHACL shapes

```
$ python main.py XSD_FILE -s SHACL_PATH
```

For example, if you execute the following:

```
$ python main.py test/test.xsd
```

The generated shape file will then be located here: test/test.xsd.shape.ttl. 


## Post-adjustment

To adjust the generated SHACL shapes with corresponding RML mapping files to the post-adjusted shapes on two use cases:

You can run the following for RINF:

```
$ python post_adjustment/main.py validation/RINF/RINF-metadata.xsd.shape.ttl -r validation/RINF/mappings/RINF-contact-line-systems.yml.ttl -a validation/RINF/RINF-metadata.xsd.shape.RINF-contact-line-systems.adjustment.ttl
```

And the following for TED:

```
$ python python main.py validation/TED/TED_EXPORT_merge.xsd.shape.ttl -r validation/TED/mappings/F03 -a validation/TED/TED_EXPORT_merge_F03.shape.adjustment.ttl
```

