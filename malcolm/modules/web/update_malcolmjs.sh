#!/bin/bash
HERE=$(dirname $0)

# Pull in changes from a built version of malcolmjs
GITHUB=https://github.com/dls-controls/malcolmjs/releases
RELEASE=$GITHUB/download/1.3.1/malcolmjs-1.3.1-0-gebca738.tar.gz

TMP=/tmp/malcolmjs.tar.gz

git rm -rf $HERE/www
rm -rf $HERE/www
mkdir $HERE/www
wget -O $TMP $RELEASE
tar -C $HERE/www -zxf $TMP
git add $HERE/www

