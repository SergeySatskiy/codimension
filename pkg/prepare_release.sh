#!/bin/sh
#
# Prepare source tarballs of Codimension components.
# $Id$

script_name="`basename "$0"`"

trunk_url='https://codimension.googlecode.com/svn/trunk'
libantlr='libantlr3c-3.2'

tag_cmd_synopsis='Create a Subversion tag for a new component version.'
mkorigtar_cmd_synopsis='Create a tarball for building a deb package.'
help_cmd_synopsis='Get help on the commands of this script.'

if test "$#" -lt 2; then
    cat <<EOF >&2
Usage:
    $script_name help COMMAND...
    $script_name COMMAND ARG...

Available commands:
    tag         - $tag_cmd_synopsis
    mkorigtar   - $mkorigtar_cmd_synopsis
    help        - $help_cmd_synopsis

EOF
    exit 1
fi

cmd_help()
{
    for command; do
        case "$command" in
        tag) cat <<EOF ;;
tag: $tag_cmd_synopsis

Usage: $script_name tag COMPONENT VERSION [REVISION]

This command creates a version tag under the /tags directory in the
Subversion repository of Codimension. Requires svnmucc.

Arguments:
    COMPONENT         : Component name, either "pythonparser"
                        or "codimension".

    VERSION           : Package version to make a tag for.

    REVISION          : Source revision number at which to
                        branch from trunk (HEAD by default).
EOF
        mkorigtar) cat <<EOF ;;
mkorigtar: $mkorigtar_cmd_synopsis

Usage: $script_name mkorigtar COMPONENT VERSION

Arguments:
    COMPONENT         : Component name, either "pythonparser"
                        or "codimension".

    VERSION           : Desired package version. Must correspond
                        to a tag created earlier with the help of
                        the tag command.
EOF
        help) cat <<EOF ;;
help: $help_cmd_synopsis

Usage: $script_name help COMMAND...

Run $script_name without arguments to get the list of commands.
EOF
        *)
            echo "$command: unknown command."
        esac
        echo ''
    done
}

mkorigtar_pythonparser()
{
    version="$1"
    rev="$2"

    pkg_basename='codimension-parser'

    echo "Releasing $pkg_basename version $version based on trunk@$rev..."

    working_dir="/tmp/$script_name.`date '+%Y%m%d%H%M%S'`.$$"

    echo "Creating working directory $working_dir"
    mkdir "$working_dir" || exit 4

    pkg_name="$pkg_basename-$version"

    pkg_dir="$working_dir/$pkg_name"
    mkdir "$pkg_dir" || exit 4

    echo "Exporting '$libantlr' from Subversion..."
    svn export -q "-r$rev" "$trunk_url/thirdparty/$libantlr" \
        "$pkg_dir/$libantlr" || exit 4

    echo "Exporting 'pythonparser' from Subversion..."
    svn export -q "-r$rev" "$trunk_url/pythonparser" \
        "$pkg_dir/pythonparser" || exit 4

    echo "Exporting 'debian' from Subversion..."
    svn export -q "-r$rev" "$trunk_url/pkg/pythonparser/debian" \
        "$pkg_dir/debian" || exit 4

    echo "Exporting 'configure' from Subversion..."
    svn export -q "-r$rev" "$trunk_url/pkg/pythonparser/configure" \
        "$pkg_dir/configure" || exit 4

    echo "Fixing relative paths..."
    grep -rl '\.\./thirdparty' "$pkg_dir/pythonparser" | \
        xargs sed -i 's,\.\./thirdparty,..,g'

    tarball="${pkg_basename}_$version.orig.tar.gz"
    echo "Preparing $tarball"
    tar czf "$tarball" -C "$working_dir" --owner=root --group=root \
        "$pkg_name" || exit 4

    rm -rf "$working_dir"

    echo 'Done.'

    return 0
}

command="$1"
shift

case "$command" in
help)
    cmd_help "$@"
    exit 0
    ;;
mkorigtar)
    ;;
*)
    echo "Unknown command '$command'." >&2
    exit 2
    ;;
esac

component="$1"
shift

case "$component" in
pythonparser)
    ;;
*)
    echo "Unknown component '$component'." >&2
    exit 3
esac

case "$command" in
mkorigtar)
    version="$1"

    case "$version" in
    '')
        echo 'Version number is required.' >&2
        exit 3
        ;;
    *.*)
        ;;
    *)
        echo "Argument '$version' doesn't look like a version number." >&2
        exit 3
    esac

    rev="$2"
    test "x$rev" = 'x' && rev='HEAD'

    mkorigtar_$component $version $rev
esac
