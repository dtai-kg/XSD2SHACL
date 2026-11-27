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


The syntax of the generated shapes is checked against the copy of `shacl-shacl.ttl` that ships with the package; no network access is needed.

Nested complex elements are linked to their parent through a property shape that carries the element's path, cardinality and `sh:node`, for example:

```turtle
<NodeShape/Items> sh:property <PropertyShape/Items/item> .
<PropertyShape/Items/item> sh:path :item ; sh:node <NodeShape/Items/item> ; sh:minCount 0 .
```

Notes on the translation:

- Attributes without `use` are optional (`sh:maxCount 1` only); `use="required"` gives `sh:minCount 1` and `sh:maxCount 1`, `use="prohibited"` gives `sh:maxCount 0`.
- The `minOccurs`/`maxOccurs` of `xs:sequence`, `xs:choice`, `xs:all` and group references are multiplied into the cardinalities of the elements inside them (a lower bound of 0 or an unbounded upper bound propagates; elements inside a choice get `sh:minCount 0`). A named group takes the loosest occurrence over all its references.
- `xs:pattern` facets are anchored (`^(...)$`); several patterns of one restriction become one alternative pattern; patterns of a user-defined base type are combined with the derived type's patterns through `sh:and`. Facets, enumerations and the datatype of user-defined base types are inherited, the most derived value of a facet winning.
- Enumeration and `fixed` values are literals typed with the built-in type the declaration derives from, the same datatype as the shape's `sh:datatype` (`xsd:token`, `xsd:NMTOKEN`, ... included); values of `xs:string` are plain literals.
- A complex type derived by `xs:restriction` refers to its base type's node shape with `sh:node`, like an extension.
- A reference to a global complex element is linked through a property shape with the element's path and the cardinality of the reference.
- A reference to a global simple element reuses the property shape of the global element, which holds the constraints on the value and no cardinality. The cardinality of each reference is given separately by a property shape of the referring shape (for example `PropertyShape/PurchaseOrderType/comment`) with the element's path, name, cardinality and, in a sequence, `sh:order`.
- The candidates of a choice keep their own property shapes; the combination is an `sh:xone` of "selected" shapes (`sh:path` with `sh:minCount`, or `sh:and` of the mandatory members of a sequence candidate) with a "no candidate" member when the choice may be absent, or an `sh:or` for a repeatable choice that must occur.

## Post-adjustment

To adjust the generated SHACL shapes with the RML mappings of the same XML source:

```bash
python -m xsd2shacl -i SHAPES -r RML_FILE_OR_DIR [-a OUT]
```

`-r` takes one mapping file or a directory of mapping files (`.ttl` or `.rml`), which are processed in the order of their file names. Without `-a`, the result is stored in `SHAPES.RML_FILENAME.adjustment.ttl`. For example:

```bash
python -m xsd2shacl -i usecases/RINF/RINF-metadata.xsd.shape.ttl -r usecases/RINF/mappings/RINF-contact-line-systems.yml.ttl -a RINF-contact-line-systems.adjustment.ttl
python -m xsd2shacl -i usecases/TED/TED_EXPORT_merge.xsd.shape.ttl -r usecases/TED/mappings/F03 -a TED_F03.adjustment.ttl
```

The post-adjustment is the implementation used by [SCOOP](https://github.com/dtai-kg/SCOOP) (`SCOOP/shape_adjustment_single.py`), kept identical in both repositories. The node shape of a triples map takes the classes of the mapping as targets, and the property shapes of the referenced elements and attributes take the mapped predicates. A property shape that links a parent shape to a nested complex element is re-pathed to the predicate the mapping uses between the two resources, replaced by the child's node-level constraints copied onto the parent shape when the mapping puts the child's values on the parent's subject (the parent refers to the child with `sh:node` instead if a single-valued parameter would conflict), or removed when the mapping does not refer to the child. Property shapes whose node kind becomes IRI or blank node lose `sh:datatype`, `sh:languageIn` and value-range constraints. Property shapes that are attached to a node shape get no target of their own; a property shape not referenced by any node shape with a target declaration gets `sh:targetSubjectsOf` with its own path.

## Tests

```bash
pip install pytest xmlschema
pytest tests
```

Some tests compare the validation results with `xmllint`, which has to be installed.

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

## Known limitations

- Attributes referenced from an imported namespace (for example `xlink:type`, `xlink:href` and `xlink:title` in the TED schemas) are looked up by local name only. When no declaration with that local name exists in the parsed schemas, the generated node shape refers to a property shape that is not defined (`PropertyShape/<local name>` without `sh:path`).
- The syntax check with shacl-shacl is skipped for shapes graphs with 10,000 triples or more.
- The shapes are post-adjusted mapping file by mapping file, and triples maps with the same subject template are matched to the shapes created for the first mapping file that used that template. The mapping files of a directory are therefore always processed in a fixed (sorted) order; the numbering of renamed shape identifiers follows that order.
- Outputs of two separate post-adjustment runs are equal up to the numbering of renamed shape identifiers, which depends on the Python process (set iteration order).
- A triples map that iterates over an element but generates another resource (for example a coordinate point or a geometry built from that element's content) has its class and its property shapes attached to the node shape of the iterated element.
- Logical sources with the CSV and JSONPath reference formulations in the mappings are also processed as XPath by the post-adjustment.
