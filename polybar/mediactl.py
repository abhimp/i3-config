#!/usr/bin/env python
from pydbus import SessionBus
import sys
import time
import os, signal

PIDFILE="/tmp/mediactl_instance.pid"

bus = SessionBus()
remote_object = bus.get(
    "org.freedesktop.DBus", # Bus name
    "/org/freedesktop/DBus" # Object path
)

DEBUG = False
if "MEDIA_CTL" in os.environ:
    DEBUG = True

def deamonize():
    pid = os.fork()

    if pid < 0:
        exit(-1)

    if pid != 0:
        exit(0)


    pid = os.fork()

    if pid < 0:
        exit(-1)

    if pid != 0:
        exit(0)

def getMediaObj():
    media = None

    vlc = None
    rhythmbox = None

    for x in remote_object.ListNames():
        if x.startswith("org.mpris.MediaPlayer2."):
            if media is None:
                media=x
            y = x.lower()
            if 'vlc' in y:
                vlc = x
            elif 'rhythmbox' in y:
                rhythmbox = x

    if vlc is not None:
        media = vlc
    if rhythmbox is not None:
        media = rhythmbox

    if media is None:
        return None

    try:
        mediaobj = bus.get(media, "/org/mpris/MediaPlayer2")
        return mediaobj
    except:
        return None

def debugPrint(*a, **b):
    if not DEBUG:
        return
    print(*a, **b)

def runCmd():
    #deamonize()
    mediaobj = getMediaObj()
    if mediaobj is None:
        exit(1)
    command = sys.argv[1]
    if command == "PlayPause":
        mediaobj.PlayPause ()
    elif command == "Stop":
        mediaobj.Stop()
    elif command == "Previous":
        mediaobj.Previous()
    elif command == "Next":
        mediaobj.Next()
    elif command == "Seek" and len(sys.argv) >= 3:
        p = float(sys.argv[2]) * 1000 * 1000 * 10
        mediaobj.Seek(p)
    try:
        with open(PIDFILE) as fp:
            pid = int(float(fp.read()))
            os.kill(pid, signal.SIGUSR1)
    except:
        pass

def minsec(us):
    sec = int(us/1000/1000)
    m = int(sec/60)
    sec = sec%60
    return f"{m}:{sec:02d}"

def printStatus(count = -1):
    mediaobj = None
    cmd = "  %{A1:python "+sys.argv[0]+" Previous:}%{F#ff0}"+chr(0xe054)+"%{F-}%{A}"
    cmd += " | " + "%{A1:python "+sys.argv[0]+" PlayPause:}%{F#f0}"+chr(0xe058)+chr(0xe059)+"%{F-}%{A}"
    cmd += " | " + "%{A1:python "+sys.argv[0]+" Next:}%{F#ff0}"+chr(0xe05a)+"%{F-}%{A}"
    emojis = {"Playing": chr(0xe058), "Paused": chr(0xe059), "Stopped": chr(0xe057)}
    acceptableStatus = {"Playing", "Paused"}
    sleep = False
    while True:
        if not sleep:
            sleep = True
        else:
            time.sleep(5)
        if count == 0:
            break
        if count > 0:
            count -= 1
        if mediaobj is None:
            mediaobj = getMediaObj()
        if mediaobj is None:
            debugPrint("da")
            print("")
            sys.stdout.flush()
            continue

        try:
            status = mediaobj.PlaybackStatus
            debugPrint(status, file=sys.stderr)
            if status not in acceptableStatus:
                print(emojis.get(status, ""))
                sys.stdout.flush()
                continue
            md = mediaobj.Metadata
            debugPrint(md, file=sys.stderr)
            artist = ", ".join(md['xesam:artist'])
            title = md['xesam:title']
            album = md['xesam:album']
            length = md['mpris:length']
            pos = 0
            try:
                pos = mediaobj.Position
            except:
                pass
            ppos = ['─'] * 10
            ppos[int(pos * 10 / length)] = '|'
            ppos = "".join(ppos)
            spos = "%{F#0f0}" + minsec(pos) + "%{F-} / %{F#fa8148}" + minsec(length) + "%{F-}"


            print("%{F#f00}" + emojis.get(status, "") + "%{F-}", title[:30], spos, cmd)#, "%{T2}" + ppos + "%{T-}")
            sys.stdout.flush()
        except Exception as e:
            debugPrint(f"Exception {e} [{mediaobj}, {status}]", file=sys.stderr)
            mediaobj = None
            print("")
            sys.stdout.flush()

def handleStatus(signum, frame):
    printStatus(1)
    print("Handled", file=sys.stderr)

def runStatus():
    signal.signal(signal.SIGUSR1, handleStatus)
    with open(PIDFILE, "w") as fp:
        print(os.getpid(), file=fp)
    printStatus()

if len(sys.argv) > 1:
    runCmd()
else:
    runStatus()
