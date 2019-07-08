# CML - Codimension Markup Language


CML is a micro markup language which uses Python comments to store the
additional information which is used at the time the graphics code
representation is generated.

Each CML comment consists of one or more adjacent lines. A first line format
is as follows:

```python
# cml <version> <type> [key=value pairs]
```

A format of the further lines (if needed) is as follows:

```python
# cml+ <continue of the previous CML line>
```

The ‘cml’ and ‘cml+’ literals distinguish a CML comment from all the other
comments. A version field is an integer and introduced for the future
extensions if CML evolves. A type defines what exactly will be done when a
diagram is drawn. A type is a string identifier, e.g. ‘rt’ (stands for ‘replace
text’). Key=value pairs in turn let to have an arbitrary number of arguments
for the CML comments.


## CML v.1

### Key - Value pairs

The keys must be valid identifiers.

The values are arbitrary strings. If the value contains spaces then it must be
in double quotes otherwise the double quotes are optional. The double quote
charater inside values has to be escaped with the backslash character. 

### Colors

Some of the CML comments support color specs, e.g. for a graphics primitive
background. The color value can be specifies in one of the following ways:

| Format          | Description          |
| :-------------: | -------------------- |
| #hhh            | hexadecimal RGB      |
| #hhhh           | hexadecimal RGBA     |
| #hhhhhh         | hexadecimal RRGGBB   |
| #hhhhhhhh       | hexadecimal RRGGBBAA |
| ddd,ddd,ddd     | decimal RGB          |
| ddd,ddd,ddd,ddd | decimal RGBA         |



### cc

The 'cc' comment is used for custom colors of most of the graphics items.

Supported properties:

| Property | Description                             |
| :------: | --------------------------------------- |
| bg       | background color for the item, optional |
| fg       | foreground color for the item, optional |
| border   | border color for the item, optional     |


Example:
```python
# cml 1 cc bg=#f6f4e4 fg=#000 border=#fff
```

### gb

The 'gb' comment is used to indicate the beginning of the visual group.
It needs a counterpart 'ge' CML comment which indicates the end of the visual
group.

Supported properties:

| Property | Description                                             |
| :------: | ------------------------------------------------------- |
| id       | unique identifier of the visual group, mandatory        |
| title    | title to be shown when the group is collapsed, optional |
| bg       | background color for the item, optional                 |
| fg       | foreground color for the item, optional                 |
| border   | border color for the item, optional                     |


Example:
```python
# cml 1 gb id="1234-5678-444444" title="MD5 calculation"
```

### ge

The 'ge' comment is used to indicate the end of the visual group. It needs a
counterpart 'gb' CML comment which indicates the beginning of the visual group.


Supported properties:

| Property | Description                                      |
| :------: | ------------------------------------------------ |
| id       | unique identifier of the visual group, mandatory |


Example:
```python
# cml 1 ge id="1234-5678-444444"
```


### rt

The 'rt' comment is used for replacing the text of most of the graphics items.
Supported properties:

| Property | Description                                          |
| :------: | ---------------------------------------------------- |
| text     | text to be shown instead of the real code, mandatory |


Example:
```python
# cml 1 rt text="Reset the dictionary"
```

### sw

The 'sw' comment is used for 'if' and 'elif' statements to switch default branch
location i.e. to have the 'No' branch at the right.

Supported properties: none


Example:
```python
# cml 1 sw
```



### doc

The 'doc' comment is used for links to some sort of documentation.
This comment may appear as:
- independent comment
- leading comment
- trailing comment

It is not recognized in side comments.


Supported properties:

| Property | Description                                          |
| :------: | ---------------------------------------------------- |
| link     | link to the documentation, optional |
| anchor   | anchor id to reference this point in the code from the documentation, optional |
| title    | text to be shown on graphics, optional (if not provided then 'doc' will be shown) |

At least one: a link or an anchor must be provided.

The link supports the following formats:
- http://... an external browser will be invoked
- https://... an external browser will be invoked
- [file:]absolute path
- [file:]relative path. The relative is tried to the current file and then to the project root

Example:
```python
# cml 1 doc link="http://codimension.org"
```


