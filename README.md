# XSD2SHACL

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![DOI](https://zenodo.org/badge/687035494.svg)](https://zenodo.org/badge/latestdoi/687035494)

A tool to generate SHACL shapes from XSD for RDF graphs validation. 

- The results of comparison and evaluation of supported XSD components are under [comparison folder](https://github.com/dtai-kg/XSD2SHACL/tree/main/comparison).

- The results of validation on two usecases are under [usecases folder](https://github.com/dtai-kg/XSD2SHACL/tree/main/usecases). 

## Installation

- From PyPi package
```bash
pip install xsd2shacl
```

- From source code:
```bash
python -m pip install poetry
poetry update
poetry build
```
## Usage

To translate XSD to SHACL shapes:

```bash
python -m xsd2shacl -x XSD_PATH [-s SHACL_PATH]
```

For example, if you execute the following:

```bash
python -m xsd2shacl -x comparison/pos.xsd
```

The generated shape file will then be located here: comparison/pos.xsd.shape.ttl. 


## Post-adjustment

To adjust the generated SHACL shapes with corresponding RML mapping files to the post-adjusted shapes on two use cases:

- RINF:

```bash
python -m xsd2shacl -i usecases/RINF/RINF-metadata.xsd.shape.ttl -r usecases/RINF/mappings/RINF-contact-line-systems.yml.ttl -a usecases/RINF/RINF-metadata.xsd.shape.RINF-contact-line-systems.adjustment.ttl
```

-  TED:

```bash
python -m xsd2shacl -i usecases/TED/TED_EXPORT_merge.xsd.shape.ttl -r usecases/TED/mappings/F03 -a usecases/TED/TED_EXPORT_merge_F03.shape.adjustment.ttl
```

Run following get the validation results (C_T, R/T, R/T', C_P, R/P, R/P'):

```bash
python usecases/RINF/metrics.py
python usecases/TED/metrics.py
```

## Cite 

To cite our work:
```bib
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
```