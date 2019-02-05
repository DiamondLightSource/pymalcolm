#!/bin/bash
HERE=$(dirname $0)

# Pull in changes from a built version of malcolmjs
RELEASE=https://github.com/dls-controls/malcolmjs/releases/download/1.6.0/malcolmjs-1.6.0-0-g18ef035.tar.gz

TMP=/tmp/malcolmjs.tar.gz

git rm -rf $HERE/www
rm -rf $HERE/www
mkdir $HERE/www
wget -O $TMP $RELEASE
tar -C $HERE/www -zxf $TMP
git add $HERE/www

