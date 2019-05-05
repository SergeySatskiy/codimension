# Codimension Python 3 IDE

Essential links:

- [Presentation of the technology and the tool](http://codimension.org/documentation/technologypresentation/)
- [Project home page](http://codimension.org/)
- [Packages and installation](http://codimension.org/download/linuxdownload.html)
- [Running Codimension from a git clone](http://codimension.org/download/runfromgit.html)
- [Hot keys cheat sheet](http://codimension.org/documentation/cheatsheet.html)

---

**Codimension** is yet another free experimental Python IDE licensed under GPL v3.

Codimension aims to provide an integrated system for:

- traditional text-based code editing, and
- diagram-based code analysis.

At the moment a few graphics oriented features are implemented.
One of the major (and the most visible) is a generation of a control flow diagram
while the code is typed. The screenshot below shows the main area divided into two parts.
The left one is a traditional text editor while the right one is a generated diagram.
The diagram is updated when the IDE detects a pause in typing the code.

![Screenshot](http://codimension.org/assets/cdm/images/habr/overviewSmall.png "Screenshot")


The IDE implements many of the typical features to support the development process.
The uniqueness of the IDE however is in the graphics representation of the code.
Thus the main focus of the project is to implement more features for the graphics pane.


## Installation

**Note:** python 3.5/3.6/3.7 is required

The IDE is pip installable:

```shell
pip install codimension
```

The feature of building some diagrams e.g. a dependency diagram requires a graphviz
package. The installation depends on a system. E.g. on Ubuntu you would need
to do the following:

```shell
sudo apt-get install graphviz
```

To have plantUML diagram support java needs to be installed. The installation depends
on a system. E.g. on Ubuntu you would need to do the following:


```shell
sudo apt-get install default-jre
```


## Troubleshooting

The IDE depends on a couple of the binary modules which are compiled at the
time of the installation. So your system needs a g++ compiler installed as well
as python interpreter header files. To install the required packages on Ubuntu you
would need to do the following:

```shell
sudo apt-get install g++
sudo apt-get install python3-dev
sudo apt-get install libpcre3-dev
```

