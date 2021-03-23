#!/usr/bin/bash

dev_name=AUDIO_RECC
unload_files=$(mktemp)

pactl load-module module-null-sink sink_name=$dev_name | tee $unload_files
pactl load-module module-loopback source=@DEFAULT_MONITOR@ sink=$dev_name | tee -a $unload_files
pactl load-module module-loopback source=@DEFAULT_SOURCE@ sink=$dev_name | tee -a $unload_files

device=$(cat $unload_files | sort -r)
echo "#!/usr/bin/env bash" > $unload_files

for y in $device
do
    echo "pactl unload-module" $y >> $unload_files
done
echo "rm $unload_files" >> $unload_files
chmod +x $unload_files

mkdir -p ~/Downloads/autorecording
rec ~/Downloads/autorecording/$(date +%Y%m%d-%H%M%S).mp3 2> /dev/null &
recpid=$!
sleep 1
streamid=$(pactl list source-outputs | grep -e "^Source" -e "application.process.id" | grep -B1 $recpid | grep "Source" | grep -o -e "#[0-9]\+"| cut -b2-)

pactl move-source-output $streamid ${dev_name}.monitor

wait

bash $unload_files
