# How to prepare a release

## Prepare the pypi config file `~/.pypirc`:

```
[distutils]
index-servers =
  pypi
  pypitest

[pypi]
repository=https://pypi.python.org/pypi
username=<user>
password=<password>

[pypitest]
repository=https://test.pypi.org/legacy/
username=<user>
password=<password>
```
**Note:** the user name and password are open text, so it is wise to change permissions:

```
chmod 600 ~/.pypirc
```

## Release Steps

1. Update ChangeLog
2. Make sure git clone is clean
3. Edit `codimension/cdmverspec.py` setting the new version
4. Make sure pandoc is installed as well as pypandoc
5. Run
```shell
python setup.py sdist
```
6. Make sure that `tar.gz` in the `dist` directory has all the required files
7. Upload to pypitest
```shell
python setup.py sdist upload -r pypitest
```
8. Make sure it looks all right at [pypitest](https://testpypi.python.org/pypi)
9. Install it from pypitest
```shell
pip install --index-url https://test.pypi.org/simple/ codimension
```
10. Check the installed version
```shell
codimension &
```
11. Uninstall the pypitest version
```shell
pip uninstall codimension
```
12. Upload to pypy
```shell
python setup.py sdist upload
```
13. Make sure it looks all right at [pypi](https://pypi.python.org/pypi)
14. Install it from pypi
```shell
pip install codimension
```
15. Check the installed version
```shell
codimension &
```
16. Create an annotated tag
```shell
git tag -a 4.0.0 -m "Release 4.0.0"
git push --tags
```
17. Publish the release on github at [releases](https://github.com/SergeySatskiy/codimension/releases)


## Development

```shell
# Install a develop version (create links)
python setup.py develop

# Uninstall the develop version
python setup.py develop --uninstall
```

## Links

[Peter Downs instructions](http://peterdowns.com/posts/first-time-with-pypi.html)

[Ewen Cheslack-Postava instructions](https://ewencp.org/blog/a-brief-introduction-to-packaging-python/)

