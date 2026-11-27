# XSD2SHACL Vs. XMLSchema2ShEX

We compared XSD2SHACL with [XMLSchema2ShEX](https://github.com/herminiogg/XMLSchema2ShEx/tree/develop)+[Shaclex](https://github.com/weso/shaclex)

The evalation on XMLSchema2ShEx's supported components are under xmlschema2shex folder.

The cases under this folder covers our supported XSD components in addtion to components in xmlschema2shex.

## Known inconsistencies in the stored files

- `xmlschema2shex/example.xsd.shex` is the ShEx output for another test case (`PurchaseOrderType` with `shipTo`) and does not correspond to `example.xsd` (`Items`), whereas `example.xsd.shex.shape.ttl` does. The file was committed in this state and no version matching `example.xsd` exists in the history, so it is left as is rather than replaced by a file that would not be a genuine XMLSchema2ShEx output.
- `xmlschema2shex/-enumeration.xsd` uses the `xsd:` prefix (line 27) without declaring it, so it cannot be parsed by any XML parser; no parseable version exists in the history.
- The stored outputs in `xmlschema2shex/` were produced by an earlier version of the translator and differ from the current output in the naming of shapes (for example attribute property shapes are now named `PropertyShape/<element path>/@<attribute>`, and nested complex elements are linked through property shapes).
