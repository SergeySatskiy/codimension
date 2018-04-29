# Codimension skins

Individual directories hold all the files required to set a codimension skin.

A skin is composed of:
- application style sheet (app.css)
- general settings (skin.json)
- control flow diagram settings (cflow.json)

The .css file follows the QT library application css spec.

Note: do not create a directory called 'default'. The default skin is created
      in the user ~/.codimension3/skins/default directory at first run (or
      re-created if lost). All the other skin directories are copied from the
      installation package at first run (or restored if lost).

# Platform specific support

Sometimes settings need to be platform specific, e.g. different platforms may
have different monospace fonts available. To cover these cases Codimension does
the following when it copies the skin files:
- a platform specific suffix is formed as '.' + sys.platform.lower()
- for each file in the skin directory:
  - presence of the platform specific file is checked as <file name><suffix>
    if found then the file is copied to into the user skin directory as <file name>
  - if a platform specific file is not found then a generic file is copied

Ultimately, the user skin directories will have files without a platform
specific suffix while the installation package skin directories may have
different versions depending on a platform.
