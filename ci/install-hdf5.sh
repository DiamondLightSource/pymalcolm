#!/bin/sh
set -e
# check to see if hdf5 folder is empty
if [ ! -d "$HOME/hdf5-1.10.2/lib" ]; then
  curl -L -O https://www.hdfgroup.org/ftp/HDF5/releases/hdf5-1.10/hdf5-1.10.2/src/hdf5-1.10.2.tar.bz2;
  tar -jxf hdf5-1.10.2.tar.bz2;
  cd hdf5-1.10.2 && ./configure --prefix=$HOME/hdf5-1.10.2 && make -j && make install;
else
  echo 'Using cached directory.';
fi
