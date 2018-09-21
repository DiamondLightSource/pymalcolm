#!/bin/bash
HERE=$(dirname $0)

# Pull in changes from a built version of malcolmjs
GITHUB=https://github.com/dls-controls/malcolmjs/releases/download
RELEASE=$GITHUB/1.1.0/malcolmjs-1.1.0-0-g5c677f0.tar.gz

TMP=/tmp/malcolmjs.tar.gz

git rm -rf $HERE/www
rm -rf $HERE/www
mkdir $HERE/www
wget -O $TMP $RELEASE
tar -C $HERE/www -zxf $TMP
git add $HERE/www

