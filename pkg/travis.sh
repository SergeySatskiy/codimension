#!/bin/bash -x

script=$(readlink -f $0)
script_dir=$(dirname $script)

VERSION=$(git describe --always --tags --abbrev=0)
if [ -z "${VERSION}" ]; then
	echo "Can't get version"
	exit 1
fi

VERSION=${VERSION#v}

TRAVIS_REPO_NAME=$(echo $TRAVIS_REPO_SLUG | cut -d '/' -f 2)
DOCKER_REPO=tarantool/build

project=${TRAVIS_REPO_NAME}
projectfull=${project}-${VERSION}

echo "Building ${projectfull}"

cd ..

case ${PACK} in
	deb)
		TARANTOOL_IMAGE=${DOCKER_REPO}:${OS}-${DIST}
		;;
	rpm)
		TARANTOOL_IMAGE=${DOCKER_REPO}:${OS}${DIST}
		;;
	*)
		echo "Packaging ${PACK} is not supported."
		exit 1
		;;
esac


tar_name=${projectfull}.tar.gz

mkdir out

cp -r ${TRAVIS_REPO_NAME} ${projectfull}
echo "__version__='${VERSION}'" > ${projectfull}/src/cdmverspec.py
tar czf ${tar_name} ${projectfull}
cp ${tar_name} out/
cp ${TRAVIS_REPO_NAME}/pkg/build_${PACK}.sh out/

echo "FROM ${TARANTOOL_IMAGE}" > Dockerfile
echo "RUN useradd -s ${SHELL} -u $(id -u) -d ${HOME} ${USER}" >> Dockerfile
echo "RUN usermod -a -G wheel ${USER} || :;\\" >> Dockerfile
echo "    usermod -a -G adm ${USER} || :;\\" >> Dockerfile
echo "    usermod -a -G sudo ${USER} || :;\\" >> Dockerfile
echo "    usermod -a -G mock ${USER} || :" >> Dockerfile
echo "USER ${USER}" >> Dockerfile

cat Dockerfile

mv Dockerfile out/

docker build --rm=true --quiet=true -t ${TARANTOOL_IMAGE}-for-${USER} out

docker run --volume ${PWD}/out:/home/${USER}/result --workdir /home/${USER}/result --rm=true --user=${USER} ${TARANTOOL_IMAGE}-for-${USER} bash -x /home/${USER}/result/build_${PACK}.sh ${projectfull} ${project} ${VERSION}

