#!/bin/bash -x

projectfull="$1"
project="$2"
version="$3"

cp ~/result/${projectfull}.tar.gz ${project}_${version}.orig.tar.gz

tar xzf ${project}_${version}.orig.tar.gz

(
	cd ${projectfull}
	sudo mk-build-deps -i --tool "apt-get -y"
	rm -f *.deb
	dch --force-bad-version --distribution unstable --package ${project} --newversion ${version}-$(lsb_release -si)~$(lsb_release -sc) "new release"
	debuild -us -uc
)

#mv -f *.deb ~/result/

