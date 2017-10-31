#!/bin/bash
# clean SVGS *IN PLACE*
source ~/virtualenvs/pymalcolm/bin/activate
for f in *.svg; do
    mv $f $f.orig
    scour -i $f.orig -o $f --remove-metadata --strip-xml-prolog --enable-id-stripping --protect-ids-noninkscape
done

