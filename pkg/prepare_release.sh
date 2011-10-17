#!/bin/sh
#
# Prepare source tarballs of Codimension components.
# $Id$

script_name="`basename "$0"`"
script_dir="`dirname "$0"`"
script_dir="`cd "$script_dir" && pwd`"

root_url='https://codimension.googlecode.com/svn'
trunk_url="$root_url/trunk"
libantlr='libantlr3c-3.2'

tag_cmd_synopsis='Create a Subversion tag for a new component version.'
maketar_cmd_synopsis='Create a tarball for building a distribution package.'
help_cmd_synopsis='Get help on the commands of this script.'

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
        maketar) cat <<EOF ;;
maketar: $maketar_cmd_synopsis

Usage: $script_name maketar PKGTYPE COMPONENT [VERSION]

Arguments:
    PKGTYPE           : Target package type, either "deb"
                        or "rpm".

    COMPONENT         : Component name, either "pythonparser"
                        or "codimension".

    VERSION           : Desired package version. Must correspond
                        to a tag created earlier with the help of
                        the tag command. Alternatively, keyword
                        'trunk' can be specified to create a
                        tarball off trunk sources. If omitted,
                        'trunk' is assumed.
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

case "$#$1" in
0)
    echo "Type '$script_name help' for usage."
    exit 1
    ;;
1help|1--help|1-h)
    cat <<EOF
Usage:
    $script_name help COMMAND...
    $script_name COMMAND ARG...

Available commands:
    tag         - $tag_cmd_synopsis
    maketar     - $maketar_cmd_synopsis
    help        - $help_cmd_synopsis

EOF
    exit 0
    ;;
*help)
    shift
    cmd_help "$@"
    exit 0
esac

error()
{
    echo "Error: $2" >&2
    exit $1
}

action_tag()
{
    echo 'Checking whether changelogs have been updated...'
    changelog="trunk/pkg/$component/debian/changelog"
    svn cat "$root_url/$changelog" | \
            grep "^$pkg_basename ($version" > /dev/null && \
        changelog="trunk/pkg/$component/$pkg_basename.spec" && \
        svn cat "$root_url/$changelog" | \
            grep "^Version: $version" > /dev/null || \
        error 3 "$changelog hasn't been updated."

    echo "Releasing $component version $version based on trunk@$rev..."
    version_dir="tags/$component/$version"
    args="-U $root_url mkdir $version_dir"
    while read source target; do
        if test -n "$target"; then
            args="$args cp $rev trunk/$source $version_dir/$target"
        else
            args="$args mkdir $version_dir/$source"
        fi
    done
    svnmucc -m"Created a tag for $component version $version." $args || exit 4
}

action_get_from_trunk()
{
    echo "Retrieving $component from trunk as version $version..."
    while read source target; do
        if test -n "$target"; then
            svn export -q "$root_url/trunk/$source" "$pkg_dir/$target" || exit 4
        else
            mkdir "$pkg_dir/$source"
        fi
    done
}

act_on_pythonparser()
{
    $1 <<EOF
pythonparser pythonparser
thirdparty/$libantlr $libantlr
pkg/pythonparser/configure configure
pkg/pythonparser/debian debian
pkg/pythonparser/codimension-parser.spec codimension-parser.spec
EOF
}

act_on_codimension()
{
    $1 <<EOF
src src
thirdparty
thirdparty/pymetrics-0.8.1 thirdparty/pymetrics
pkg/codimension/debian debian
pkg/codimension/codimension.spec codimension.spec
EOF
}

patch_pythonparser()
{
    echo 'Patching...'
    grep -rl '\.\./thirdparty' "$pkg_dir/pythonparser" | \
        xargs sed -i 's,\.\./thirdparty,..,g'
    sed -i "s/\\(version.*\\)trunk/\\1$version/" \
        "$pkg_dir/pythonparser/setup.py"
}

patch_codimension()
{
    echo 'Readying for packaging...'
    rm -f "$pkg_dir/src/codimension"
    test "x$pkgtype" = 'xdeb' && rm -rf "$pkg_dir/thirdparty"
}

maketar()
{
    working_dir="/tmp/$script_name.`date '+%Y%m%d%H%M%S'`.$$"

    echo "Creating working directory $working_dir"
    mkdir "$working_dir" || exit 4

    if test -z "$version"; then
        version="`head -n1 "$script_dir/$component/debian/changelog" | \
            sed 's/.*\([0-9]\+\.[0-9.]\+\).*/\1/'`"
        use_trunk=yes
    fi
    pkg_name="$pkg_basename-$version"
    pkg_dir="$working_dir/$pkg_name"

    if test -n "$use_trunk"; then
        act_on_$component action_get_from_trunk
    else
        echo "Exporting $component v$version from Subversion..."
        svn export -q "$root_url/tags/$component/$version" "$pkg_dir" || exit 4
    fi

    patch_$component

    echo "Adjusting for the target distribution type ($pkgtype)..."
    case "$pkgtype" in
    deb)
        tarball="${pkg_basename}_$version.orig.tar.gz"
        rm -f "$pkg_dir"/*.spec
        ;;
    rpm)
        tarball="$pkg_basename-$version.tar.gz"
        rm -rf "$pkg_dir/debian"
    esac

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
tag|maketar)
    if test "$command" = 'maketar'; then
        pkgtype="$1"

        case "$pkgtype" in
        '')
            error 2 "$script_name $command: package type required"
            ;;
        deb|rpm)
            shift
            ;;
        *)
            error 2 "$script_name $command: unknown package type '$pkgtype'"
        esac
    fi

    component="$1"

    case "$component" in
    '')
        error 2 "$script_name $command: component name required"
        ;;
    pythonparser)
        pkg_basename='codimension-parser'
        shift
        ;;
    codimension)
        pkg_basename='codimension'
        shift
        ;;
    *)
        error 2 "$script_name $command: unknown component '$component'"
    esac

    version="$1"

    case "$version" in
    ''|trunk)
        if test "$command" != 'maketar'; then
            error 2 "$script_name $command: version number required"
        elif test -n "$version"; then
            version=''
        fi
        ;;
    *.*)
        ;;
    *)
        error 2 "$script_name: invalid version number '$version'"
    esac
    ;;
*)
    error 2 "$script_name: unknown command '$command'"
    ;;
esac

case "$command" in
tag)
    rev="$2"
    test -z "$rev" && rev='HEAD'

    act_on_$component action_tag
    ;;
maketar)
    rev="$2"
    test -z "$rev" && rev='HEAD'

    maketar
esac
