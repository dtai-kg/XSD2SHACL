# XSD2SHACL

See translation and implementation detail in this [report](https://drive.google.com/file/d/1vFHQnm-dv6EAjq5gXR66wWf-3D9U85bo/view?usp=drive_link).

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
  <img src="image/table1.png">
</div>

<div align="center">
  <img src="image/table2.png">
</div>

## To Do

- [ ] choice
- [ ] Evaluation 



