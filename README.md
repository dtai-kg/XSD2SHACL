# XSD2SHACL

See translation and implementation detail in this [report](https://drive.google.com/file/d/1WP9T27y8oViv4AI3F-wJpZx2QgR-VTr3/view?usp=drive_link).

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
$ python XSDtoSHACL.py evaluation/example.xml
```

The generated shape file will then be located here: evaluation/example.xml.shape.ttl

## Translation correspondences:

<div align="center">
  <img src="image/table1.png">
</div>

<div align="center">
  <img src="image/table2.png">
</div>

## To Do

- [ ] choice
- [ ] fix issue: extension => emueneration.xml and sequence.xml 
- [ ] Evaluation 



