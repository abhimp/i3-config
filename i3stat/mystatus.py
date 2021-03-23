import json
import time
import os
import sys
from pulsemixer import Pulse
from string import Template

CONFIG = {
        "version": 1,
        "click_events": True,
        }

def initiate():
    print(json.dumps(CONFIG))
    print("[")
    sys.stdout.flush()

class modules:
    def __init__(self, name, instance):
        self.name = name
        self.instance = instance

    def __call__(self):
        return "Not Implemented"

class AudioConf(modules):
    def __init__(self, instance="Pulse"):
        self.pulse = Pulse()
        super().__init__("PulseAudio", instance)

    def getDefSink(self):
        defSinkName = self.pulse.get_server_info().default_sink_name
        defSink = [y for y in self.pulse.sink_list() if y.name == defSinkName]
        return defSink[0] if len(defSinkName) else None

    def getDefSource(self):
        defSourceName = self.pulse.get_server_info().default_source_name
        defSource = [y for y in self.pulse.source_list() if y.name == defSourceName]
        return defSource[0] if len(defSourceName) else None

    def getSinkStatus(self):
        sink = self.getDefSink()
        mute = sink.mute
        vol = sink.volume.values
        if type(vol) == list:
            vol = sum(vol)/len(vol)
        return {"omute": mute, "onum": vol}

    def getSourceStatus(self):
        source = self.getDefSource()
        mute = source.mute
        vol = source.volume.values
        if type(vol) == list:
            vol = sum(vol)/len(vol)
        return {"imute": mute, "inum": vol}

    def __call__(self, fmt="$ovol:$onum <--> $ivol:$inum", **a):
        basefmt = self.getSinkStatus()
        basefmt.update(self.getSourceStatus())
        primaryfmt=dict(otext="Vol", omute="Mute", itext="vol", imute="mute")
        primaryfmt.update(a)
#         print(basefmt)
        ovol = primaryfmt['omute'] if basefmt['omute'] else primaryfmt['otext']
        ivol = primaryfmt['imute'] if basefmt['imute'] else primaryfmt['itext']
        primaryfmt.update(ovol = ovol, ivol=ivol, **basefmt)
        op = Template(fmt).safe_substitute(primaryfmt)
        return op

def dumpModules(modules):
    status = []
    for mod in modules:
        output = mod()
        if type(output) != str:
            output = str(output)
        mo = {'name': mod.name, 'instance': mod.instance, 'color': "#00FF00", 'full_text': output}
        status += [mo]
    return status

def showStatus(modules):
    print(json.dumps(dumpModules(modules)))
    sys.stdout.flush()

def main():
    initiate()
    modules = [AudioConf()]
    while 1:
        showStatus(modules)
        time.sleep(1)

if __name__ == "__main__":
    main()
