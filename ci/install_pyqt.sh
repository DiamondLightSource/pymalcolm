#!/bin/sh
# sip
SIP_VER=4.13.3
SIP_DIR=sip-${SIP_VER}
SIP_TAR=${SIP_DIR}.tar.gz
# pyqt
PYQT_VER=4.9.4
PYQT_DIR=PyQt-x11-gpl-${PYQT_VER}
PYQT_TAR=${PYQT_DIR}.tar.gz
SITE_PACKAGES=${VIRTUAL_ENV}/lib/python${TRAVIS_PYTHON_VERSION}/site-packages
set -ex
if [ ! -e ${SITE_PACKAGES}/PyQt4 ]; then
    # Install sip
    wget http://sourceforge.net/projects/pyqt/files/sip/${SIP_DIR}/${SIP_TAR}
    tar -xzf ${SIP_TAR}
    cd ${SIP_DIR}
    python ./configure.py \
        --bindir=$(pwd)/prefix/bin \
        --sipdir=$(pwd)/prefix/share/sip \
        --incdir=$(pwd)/prefix/include \
        --destdir=${SITE_PACKAGES}
    make -j 2
    make install
    cd ..
    # Install pyqt
    export PATH=$PATH:$(pwd)/${SIP_DIR}/prefix/bin
    wget http://sourceforge.net/projects/pyqt/files/PyQt4/PyQt-${PYQT_VER}/${PYQT_TAR}
    tar -xzf ${PYQT_TAR}
    rm ${PYQT_TAR}
    cd ${PYQT_DIR}
    mkdir prefix
    python ./configure.py \
        --confirm-license \
        --bindir=$(pwd)/prefix/bin \
        --destdir=${SITE_PACKAGES}
    make -j 2
    make install
    cd ..
fi
