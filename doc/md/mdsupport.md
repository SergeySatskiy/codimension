# Markdown Support

Codimension uses markdown for its own embedded documentation. It also offers
features to use markdown for documenting user projects. To cover these items
the following has been implemented:

* Recognition of the markdown file type
* Markdown renderer to support editing and browsing markdown files
* Project property which tells where the project documentation start page is

The rendering facilities are based on (and limited by respectively) on a few components:

* [Mistune](https://github.com/lepture/mistune) markdown parser written in pure
  Python. It also renders the source to an html
* [Pygments](http://pygments.org/) python library to highlight the code
  fragments in the documentation
* QT library [QTextBrowser](https://doc.qt.io/Qt-5/qtextbrowser.html) widget 
  to display the rendered html. The widget has major limitations on what html
  can be shown so the rendered text is not always as perfect as it could be.

## Markdown flavor

The supported flavor is defined by what is recognised by mistune and what
Codimension adds. It will be highlighted what is added by Codimension.

### Headings


```markdown
# Heading one
## Heading two
### Heading three
...
```

or

```markdown
Heading one
===========

Heading two
-----------
```

### Emphasis

| Notation  | Render   |
| --------- | -------- |
| \*Italic* | *Italic* |
| \_Italic_ | _Italic_ |
| \**Bold** | **Bold** |
| \__Bold__ | __Bold__ |


### Thematic break

```markdown
---
***
___
```

### Code block

Codimension tries to find lexer for the code block using two tries.
If the language name is provided then it is used to pick a lexer. Otherwise
a magic library is used to make the best guess of the code mime type.

Back ticked code like

    ```python
    # code block
    print('3 backticks or')
    print('indent 4 spaces')
    ```

will be rendered as:

```python
# code block
print('3 backticks or')
print('indent 4 spaces')
```


Indented code like
<pre>
    # code block
    print('3 backticks or')
    print('indent 4 spaces')
</pre>

will be rendered as:

    # code block
    print('3 backticks or')
    print('indent 4 spaces')


### Inline code

| Notation                         | Render                          |
| -------------------------------- | ------------------------------- |
| Inline \`keyword` is highlighted | Inline `keyword` is highlighted |


### Block quote

The notation like

    > Block quote
    > second line
    >
    >> nested level
    >>> more nested level
    >>> text continues


will be rendered as:

> Block quote
> second line
>
>> nested level
>>> more nested level
>>> text continues

### List

Unnumbered list items may use '-', '+' and '*' characters.

    * List 1
        * List 11
            * List 111

will be rendered as:

* List 1
    * List 11
        * List 111


    1. One
    2. Two
    3. Three

will be rendered as:

1. One
2. Two
3. Three


### Table


    | Default column alignment | Center column alignment | Left column alignment | Right column alignment |
    | ------------------------ |:-----------------------:|:----------------------|-----------------------:|
    | Default alignment        | Center alignment        | Left alignment        | Right alignment        |

will be rendered as:

| Default column alignment | Center column alignment | Left column alignment | Right column alignment |
| ------------------------ |:-----------------------:|:----------------------|-----------------------:|
| Default alignment        | Center alignment        | Left alignment        | Right alignment        |


### Links

```markdown
[Link to something](http://a.com)
```
will be rendered as:

[Link to something](http://a.com)


```markdown
[Link with the URL provided later][1]
[1]: http://b.org
```
will be rendered as:

[Link with the URL provided later][1]
[1]: http://b.org

Codimension extends the link format and uses the following approach:
- if the http or https scheme is used then the external browser is invoked
- otherwise the link is treated as a file with an optional line number

| Link format |
| ----------- |
| file:./relative/fname[:lineno] |
| file:relative/fname[:lineno] |
| file:/absolute/fname[:lineno] |
| file:///absolute/fname[:lineno] |
| relative/fname[:lineno] |
| /absolute/fname[:lineno] |

When clicked the corresponding file will be opened the same way as it would be
a click in the file list.


### Images

Pixmaps are supported as
- local absolute path
- local relative path
- web resource

Here are examples:

```markdown
![Local absolute path pixmap](/home/username/codimension/codimension/pixmaps/add.png)
![Local relative path pixmap](./add.png)
![Local relative path pixmap](add.png)
![Pixmap from the internet](http://codimension.org/assets/cdm/images/shouldInstall.png)
```

In case of the web resources there is a cache of the downloaded items. The cache
is per IDE and is located at `~/.codimension3/webresourcecache/`. The cache is
autocleaned at the IDE startup - the files older than 24 hours are deleted.
