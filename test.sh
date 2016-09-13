#!/bin/bash

#export https_proxy=http://192.168.12.1:3129
#export http_proxy=http://192.168.12.1:3129

export DISTRO=ubuntu-trusty
#export DISTRO=debian-jessie
#export DISTRO=debian-wheezy

export CODIMENSION_VERSION=3.0.0

if test ! -z http_proxy ; then
	export http_proxy_var="http_proxy=${http_proxy}"
fi

if test ! -z https_proxy ; then
	export https_proxy_var="https_proxy=${http_proxy}"
fi

function fetch_debs()
{
	wget --continue https://github.com/SergeySatskiy/cdm-flowparser/releases/download/v1.0.1/cdm-flowparser_1.0.1-Ubuntu.trusty_amd64.deb
	wget --continue https://github.com/SergeySatskiy/cdm-pythonparser/releases/download/v2.0.1/cdm-pythonparser_2.0.1-Ubuntu.trusty_amd64.deb
	wget --continue https://github.com/SergeySatskiy/codimension/releases/download/v${CODIMENSION_VERSION}/codimension_${CODIMENSION_VERSION}-Ubuntu.trusty_all.deb
}

function create_docker_file()
{
cat > Dockerfile <<EOF
FROM tarantool/build:${DISTRO}

RUN mkdir -p /tmp/0
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

RUN sudo ${http_proxy_var} apt-get update
RUN sudo ${http_proxy_var} apt-get update
RUN sudo ${http_proxy_var} apt-get install -y xterm
RUN sudo ${http_proxy_var} apt-get install -y xterm
RUN sudo ${http_proxy_var} apt-get install -y python-qt4
RUN sudo ${http_proxy_var} apt-get install -y python-qscintilla2
RUN sudo ${http_proxy_var} apt-get install -y pylint
RUN sudo ${http_proxy_var} apt-get install -y pymetrics
RUN sudo ${http_proxy_var} apt-get install -y python-pygments
RUN sudo ${http_proxy_var} apt-get install -y python-chardet
RUN sudo ${http_proxy_var} apt-get install -y python-yapsy
RUN sudo ${http_proxy_var} apt-get install -y pyflakes
RUN sudo ${http_proxy_var} apt-get install -y python-rope
RUN sudo ${http_proxy_var} apt-get install -y graphviz
RUN sudo ${http_proxy_var} apt-get install -y python-svn
 
RUN sudo useradd -s ${SHELL} -u $(id -u) -d ${HOME} ${USER}
# RUN sudo usermod -a -G wheel ${USER}
RUN sudo usermod -a -G adm ${USER}
RUN sudo usermod -a -G sudo ${USER}
# RUN sudo usermod -a -G mock ${USER}

RUN mkdir /home/${USER}
RUN chown ${USER} /home/${USER}

RUN sudo bash -c 'echo "${USER} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/${USER}'
RUN sudo chmod 0440 /etc/sudoers.d/${USER}

ADD cdm-flowparser_1.0.1-Ubuntu.trusty_amd64.deb /tmp/0/cdm-flowparser_1.0.1-Ubuntu.trusty_amd64.deb
ADD cdm-pythonparser_2.0.1-Ubuntu.trusty_amd64.deb /tmp/0/cdm-pythonparser_2.0.1-Ubuntu.trusty_amd64.deb
ADD codimension_${CODIMENSION_VERSION}-Ubuntu.trusty_all.deb /tmp/0/codimension_${CODIMENSION_VERSION}-Ubuntu.trusty_all.deb

RUN dpkg -i /tmp/0/cdm-flowparser_1.0.1-Ubuntu.trusty_amd64.deb
RUN dpkg -i /tmp/0/cdm-pythonparser_2.0.1-Ubuntu.trusty_amd64.deb
RUN dpkg -i /tmp/0/codimension_${CODIMENSION_VERSION}-Ubuntu.trusty_all.deb

USER ${USER}
ENV HOME /home/${USER}
CMD /usr/bin/codimension
# CMD /bin/bash

EOF
}

function build_docker_image()
{
	create_docker_file
	docker build --rm=true --quiet=false -t cdtest:${DISTRO} .
}

function run_x_enabled_image()
{
	docker run -ti --rm=true -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix --ipc=host --net=host --pid=host cdtest:${DISTRO}
}

mkdir cd-docker
cd cd-docker
fetch_debs
build_docker_image
run_x_enabled_image


