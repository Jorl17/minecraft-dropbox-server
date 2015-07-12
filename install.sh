#!/bin/bash
if [ -z "$1" ]
  then
    PREFIX=/usr/bin
  else
    PREFIX=$1
fi
cp mc-dbox-server $PREFIX
cp mc-dbox-central-server $PREFIX
chmod +x $PREFIX/mc-dbox-server
chmod +x $PREFIX/mc-dbox-central-server
