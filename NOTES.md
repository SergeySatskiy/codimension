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
4. Run
```shell
python setup.py sdist
```
5. Make sure that `tar.gz` in the `dist` directory has all the required files
6. Upload to pypitest
```shell
python setup.py sdist upload -r pypitest
```
7. Make sure it looks all right at [pypitest](https://testpypi.python.org/pypi)
8. Install it from pypitest
```shell
pip install --index-url https://test.pypi.org/simple/ codimension
```
9. Check the installed version
```shell
codimension &
```
10. Uninstall the pypitest version
```shell
pip uninstall codimension
```
11. Upload to pypy
```shell
python setup.py sdist upload
```
12. Make sure it looks all right at [pypi](https://pypi.python.org/pypi)
13. Install it from pypi
```shell
pip install codimension
```
14. Check the installed version
```shell
codimension &
```
15. Create an annotated tag
```shell
git tag -a 4.0.0 -m "Release 4.0.0"
git push --tags
```
16. Publish the release on github at [releases](https://github.com/SergeySatskiy/codimension/releases)


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

