pid=$1
cat $pid.tar.bz2* | tar -xjvf -
mkdir $pid
cp single/$pid*.pkl $pid/
rm -rf single
