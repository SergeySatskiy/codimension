#!/bin/bash

[ -z $1 ] && echo "need version"
[ -z $1 ] && exit 1

git add *
git commit -m "test"
git tag -a v$1 -m "Test version"
git push origin master --tag

