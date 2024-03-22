# XSD2SHACL

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![DOI](https://zenodo.org/badge/687035494.svg)](https://zenodo.org/badge/latestdoi/687035494)

A tool to generate SHACL shapes from XSD for RDF graphs validation. 

- The results of comparison and evaluation of supported XSD components are under [comparison folder](https://github.com/dtai-kg/XSD2SHACL/tree/main/comparison).

- The results of validation on two usecases are under [usecases folder](https://github.com/dtai-kg/XSD2SHACL/tree/main/usecases). 

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
$ python main.py comparison/pos.xsd
```

The generated shape file will then be located here: test/test.xsd.shape.ttl. 


## Post-adjustment

To adjust the generated SHACL shapes with corresponding RML mapping files to the post-adjusted shapes on two use cases:

You can run the following for RINF:

```
$ python post_adjustment/main.py usecases/RINF/RINF-metadata.xsd.shape.ttl -r usecases/RINF/mappings/RINF-contact-line-systems.yml.ttl -a usecases/RINF/RINF-metadata.xsd.shape.RINF-contact-line-systems.adjustment.ttl
```

And the following for TED:

```
$ python main.py usecases/TED/TED_EXPORT_merge.xsd.shape.ttl -r usecases/TED/mappings/F03 -a usecases/TED/TED_EXPORT_merge_F03.shape.adjustment.ttl
```

Run following get the validation results (C_T, R/T, R/T', C_P, R/P, R/P'):

```
$ python usecases/RINF/metrics.py
$ python usecases/TED/metrics.py
```

## Cite 

To cite our work:

    @inproceedings{duan2023xsd,
        author = {Duan, Xuemin and Chaves-Fraga, David and Dimou, Anastasia},
        title = {{XSD2SHACL: Capturing RDF Constraints from XML Schema}},
        year = {2023},
        isbn = {9798400701412},
        publisher = {ACM},
        doi = {10.1145/3587259.3627565},
        booktitle = {Proceedings of the 12th Knowledge Capture Conference 2023},
        keywords = {Validation, XSD, SHACL, RDF shapes, XML Schema},
        series = {K-CAP '23}
        }