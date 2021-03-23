#!/usr/bin/env bash

getcount() {
    pgrep rec | wc -l
}

running=$(getcount)

mpid=$$
recpid=0

autorecpath=$(dirname `realpath $0`)/autorec.sh

startRecodrding() {
    cnt=$(getcount)
    if [ $cnt -ne 0 ]
    then
        return
    fi
    $autorecpath &
    recpid=$!
    getcount
}

stopRecodrding() {
    cnt=$(getcount)
    if [ $cnt -eq 0 ]
    then
        return
    fi
    kill `pgrep --parent $recpid rec`
    getcount
}

trap startRecodrding SIGUSR1
trap stopRecodrding SIGUSR2

while true
do
    getcount
    sleep 1
done
