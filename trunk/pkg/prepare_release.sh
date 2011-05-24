#!/bin/sh
#
# Prepare source tarballs of Codimension components.
# $Id$

script_name="`basename "$0"`"

trunk_url='https://codimension.googlecode.com/svn/trunk'
libantlr='libantlr3c-3.2'

if test "$#" -lt 2; then
    cat <<EOF >&2
Usage:
    $script_name <COMPONENT> <VERSION> [<REV>]

Where:
    COMPONENT         : Component name, either "pythonparser"
                        or "codimension".

    VERSION           : Package version to release.

    REV               : Subversion revision number (will be
                        used to export from trunk; HEAD by
                        default).

EOF
    exit 1
fi

component="$1"

release_pythonparser()
{
    version="$1"
    rev="$2"

    test "x$rev" = 'x' && rev='HEAD'

    pkg_basename='codimension-parser'

    echo "Releasing $pkg_basename version $version based on trunk@$rev..."

    working_dir="/tmp/$script_name.`date '+%Y%m%d%H%M%S'`.$$"

    echo "Creating working directory $working_dir"
    mkdir "$working_dir" || exit 3

    pkg_name="$pkg_basename-$version"

    pkg_dir="$working_dir/$pkg_name"
    mkdir "$pkg_dir" || exit 4

    echo "Exporting '$libantlr' from Subversion..."
    svn export -q "-r$rev" "$trunk_url/thirdparty/$libantlr" \
        "$pkg_dir/$libantlr" || exit 5

    echo "Exporting 'pythonparser' from Subversion..."
    svn export -q "-r$rev" "$trunk_url/pythonparser" \
        "$pkg_dir/pythonparser" || exit 6

    echo "Exporting 'debian' from Subversion..."
    svn export -q "-r$rev" "$trunk_url/pkg/pythonparser/debian" \
        "$pkg_dir/debian" || exit 7

    echo "Exporting 'configure' from Subversion..."
    svn export -q "-r$rev" "$trunk_url/pkg/pythonparser/configure" \
        "$pkg_dir/configure" || exit 8

    echo "Fixing relative paths..."
    grep -rl '\.\./thirdparty' "$pkg_dir/pythonparser" | \
        xargs sed -i 's,\.\./thirdparty,..,g'

    tarball="${pkg_basename}_$version.orig.tar.gz"
    echo "Preparing $tarball"
    tar czf "$tarball" -C "$working_dir" --owner=root --group=root \
        "$pkg_name" || exit 9

    rm -rf "$working_dir"

    echo 'Done.'

    return 0
}

case "$component" in
pythonparser)
    release_$component $2 $3
    ;;
*)
    echo "Unknown component '$component'" >&2
    exit 2
esac
