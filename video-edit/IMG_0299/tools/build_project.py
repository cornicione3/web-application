#!/usr/bin/env python3
"""Generate the Shotcut/MLT project IMG_0299_edit.mlt.

The .mlt file is the editable project: open it in Shotcut (File > Open) and
every clip, text, image, SFX and BGM can be adjusted individually.  This script
only exists so the initial edit is reproducible; you do not need it to edit.

Usage:  python3 tools/build_project.py   (run from the IMG_0299 folder)
"""
import os
import xml.etree.ElementTree as ET

FPS = 30
W, H = 1080, 1920
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "IMG_0299_edit.mlt")

SRC = "source/IMG_0299_edited.mp4"
IMG_NOSMOKE = "assets/images/cards/card_no_smoking.png"
IMG_TOAST = "assets/images/cards/card_toast.png"
BGM = "assets/music/mixkit-2_comical_ahjay-stelino.mp3"
SFX_POP = "assets/sfx/mixkit-3005_explainer-video-pops-whoosh-light-pop.wav"
SFX_COINS = "assets/sfx/mixkit-1993_clinking-coins.wav"
SFX_FANFARE = "assets/sfx/mixkit-722_successful-horns-fanfare.wav"
SFX_APPLAUSE = "assets/sfx/mixkit-518_small-group-cheer-and-applause.wav"

# ---- Cut list (source frames, inclusive) -------------------------------
# 0.00-0.87s  leading silence             -> cut
# 3.80-4.23s  pause before 「飲み代」      -> cut
# 5.23-5.77s  pause before 「宣誓します」  -> cut
# 8.73-9.80s  trailing tail               -> cut
CUTS = [(26, 113, "次飲みに行った時に僕がタバコ吸ってたら"),
        (127, 156, "飲み代全員おごりします"),
        (173, 261, "宣誓します、ここに / ナイス")]
TOTAL = sum(o - i + 1 for i, o, _ in CUTS)  # 207 frames = 6.9 s

# ---- Subtitles (timeline frames, inclusive) -----------------------------
SUBS = [
    (0, 38, "次 飲みに行った時に", "#ffffffff"),
    (39, 87, "僕がタバコ吸ってたら…", "#ffffffff"),
    (88, 117, "飲み代 全員おごりします！", "#ffffffff"),
    (118, 147, "宣誓します、ここに。", "#ffffffff"),
    (152, 190, "ナイス！", "#ffffe14d"),   # other speaker -> yellow
]
TITLE = (145, TOTAL - 1, " 禁煙宣誓！ ")

# ---- Inserts (timeline frames) ------------------------------------------
# (start, end, resource, final rect x y w h)
INSERTS = [
    (49, 87, IMG_NOSMOKE, (350, 30, 380, 380)),   # 「タバコ吸ってたら」
    (88, 120, IMG_TOAST, (275, 20, 530, 411)),    # 「飲み代全員おごり」
]

# ---- SFX: (track, start frame, length, resource, gain dB, fade-out frames)
SFX = [
    (1, 49, 6, SFX_POP, -6, 0),
    (1, 88, 6, SFX_POP, -6, 0),
    (1, 103, 30, SFX_COINS, -10, 6),
    (1, 145, TOTAL - 145, SFX_FANFARE, -12, 18),
    (2, 171, TOTAL - 171, SFX_APPLAUSE, -6, 14),
]
BGM_GAIN = -22  # dB, keeps BGM about 20 dB under the voice

_id = [0]


def nid(prefix):
    _id[0] += 1
    return f"{prefix}{_id[0]}"


def props(el, **kw):
    for k, v in kw.items():
        p = ET.SubElement(el, "property", name=k.replace("__", ":").replace("_dot_", "."))
        p.text = str(v)
    return el


def tc(frames):
    s = frames / FPS
    return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{s % 60:06.3f}"


root = ET.Element("mlt", LC_NUMERIC="C", version="7.22.0", title="IMG_0299 禁煙宣誓 edit",
                  )
ET.SubElement(root, "profile", description="HD Vertical 1080x1920 30 fps", width=str(W),
              height=str(H), progressive="1", sample_aspect_num="1", sample_aspect_den="1",
              display_aspect_num="9", display_aspect_den="16", frame_rate_num=str(FPS),
              frame_rate_den="1", colorspace="709")


def producer(resource, service, length, extra=None, name=None):
    pid = nid("producer")
    p = ET.SubElement(root, "producer", id=pid, **{"in": "0", "out": str(length - 1)})
    props(p, length=length, eof="pause", resource=resource, mlt_service=service, seekable=1)
    if extra:
        props(p, **extra)
    if name:
        props(p, shotcut__caption=name)
    return p


def volume_filter(parent, level=None, anim=None, kind="audioGain"):
    f = ET.SubElement(parent, "filter", id=nid("filter"))
    props(f, window=75, max_gain="20dB", mlt_service="volume", shotcut__filter=kind)
    if level is not None:
        props(f, level=level)
    if anim is not None:
        props(f, level=anim)
    return f


# -------- background track
bg = producer("0", "color", TOTAL, {"mlt_image_format": "rgba", "set.test_audio": 0})
bg.set("id", "black")
bg_pl = ET.SubElement(root, "playlist", id="background")
ET.SubElement(bg_pl, "entry", producer="black", **{"in": "0", "out": str(TOTAL - 1)})

playlists = []


def playlist(name, kind):
    pl = ET.Element("playlist", id=nid("playlist"))
    props(pl, shotcut__name=name)
    props(pl, **({"shotcut__video": 1} if kind == "video" else {"shotcut__audio": 1}))
    playlists.append((pl, kind))
    return pl


def blank(pl, frames):
    if frames > 0:
        ET.SubElement(pl, "blank", length=str(frames))


# -------- V1: main footage (cut)
src_len = 294
main = producer(SRC, "avformat-novalidate", src_len,
                {"audio_index": 1, "video_index": 0, "mute_on_pause": 0}, "IMG_0299_edited.mp4")
v1 = playlist("V1 本編", "video")
for i, o, _ in CUTS:
    ET.SubElement(v1, "entry", producer=main.get("id"), **{"in": str(i), "out": str(o)})

# -------- V2: inserts
v2 = playlist("V2 差し込み画像", "video")
cursor = 0
for s, e, res, (x, y, w, h) in INSERTS:
    blank(v2, s - cursor)
    length = e - s + 1
    p = producer(res, "qimage", 15000, {"ttl": 1, "aspect_ratio": 1, "meta.media.progressive": 1},
                 os.path.basename(res))
    ent = ET.SubElement(v2, "entry", producer=p.get("id"), **{"in": "0", "out": str(length - 1)})
    # Size/Position: pop-in (5 frames, overshoot) and pop-out (4 frames)
    cx, cy = x + w / 2, y + h / 2

    def r(scale, op):
        ww, hh = w * scale, h * scale
        return f"{cx - ww / 2:.0f} {cy - hh / 2:.0f} {ww:.0f} {hh:.0f} {op}"
    # scale-only pop (opacity keyframes render as a black box in the affine filter)
    anim = (f"0={r(0.05, 1)};3={r(1.08, 1)};5={r(1.0, 1)};"
            f"{length - 5}={r(1.0, 1)};{length - 2}={r(1.06, 1)};{length - 1}={r(0.02, 1)}")
    f = ET.SubElement(ent, "filter", id=nid("filter"))
    props(f, background="color:#00000000", mlt_service="affine", shotcut__filter="affineSizePosition",
          transition_dot_fill=1, transition_dot_distort=0, transition_dot_rect=anim,
          transition_dot_valign="middle", transition_dot_halign="center",
          shotcut__animIn="00:00:00.167", shotcut__animOut="00:00:00.133", transition_dot_threads=0)
    cursor = e + 1

# -------- V3: subtitles  /  V4: title telop
def text_track(name, items, style):
    pl = playlist(name, "video")
    cur = 0
    for s, e, txt, color in items:
        blank(pl, s - cur)
        p = producer("#00000000", "color", 15000, {"mlt_image_format": "rgba"}, f"字幕: {txt.strip()}")
        ent = ET.SubElement(pl, "entry", producer=p.get("id"), **{"in": "0", "out": str(e - s)})
        f = ET.SubElement(ent, "filter", id=nid("filter"))
        props(f, argument=txt, fgcolour=color, mlt_service="dynamictext",
              shotcut__filter="dynamicText", **style)
        cur = e + 1
    return pl


SUB_STYLE = dict(geometry="50 1250 980 330", family="Noto Sans CJK JP", size=84, weight=900,
                 style="normal", bgcolour="#00000000", olcolour="#ff000000", outline=4, pad=0,
                 halign="center", valign="bottom", opacity=1)
TITLE_STYLE = dict(geometry="90 150 900 200", family="Noto Sans CJK JP", size=104, weight=900,
                   style="normal", bgcolour="#ffe53935", olcolour="#00000000", outline=0, pad=18,
                   halign="center", valign="middle", opacity=1)
v3 = text_track("V3 字幕", SUBS, SUB_STYLE)
v4 = text_track("V4 タイトル", [(TITLE[0], TITLE[1], TITLE[2], "#ffffffff")], TITLE_STYLE)

# -------- A1: BGM
a1 = playlist("A1 BGM", "audio")
bgm = producer(BGM, "avformat-novalidate", 3434, {"audio_index": 0, "video_index": -1},
               "Comical - Ahjay Stelino (Mixkit)")
ent = ET.SubElement(a1, "entry", producer=bgm.get("id"), **{"in": "0", "out": str(TOTAL - 1)})
volume_filter(ent, level=BGM_GAIN)
volume_filter(ent, anim=f"0=-60;8=0", kind="fadeInVolume")
volume_filter(ent, anim=f"{TOTAL - 24}=0;{TOTAL - 1}=-60", kind="fadeOutVolume")

# -------- A2/A3: SFX
a2 = playlist("A2 効果音", "audio")
a3 = playlist("A3 効果音2", "audio")
curs = {1: 0, 2: 0}
for trk, s, length, res, gain, fo in SFX:
    pl = a2 if trk == 1 else a3
    blank(pl, s - curs[trk])
    p = producer(res, "avformat-novalidate", 600, {"audio_index": 0, "video_index": -1},
                 os.path.basename(res))
    ent = ET.SubElement(pl, "entry", producer=p.get("id"), **{"in": "0", "out": str(length - 1)})
    volume_filter(ent, level=gain)
    if fo:
        volume_filter(ent, anim=f"{length - fo}=0;{length - 1}=-60", kind="fadeOutVolume")
    curs[trk] = s + length

# -------- write playlists, tractor with compositing / audio mix
for pl, _ in playlists:
    root.append(pl)

tractor = ET.SubElement(root, "tractor", id="tractor0", title="IMG_0299 edit",
                        **{"in": "00:00:00.000", "out": tc(TOTAL - 1)})
props(tractor, shotcut=1, shotcut__projectAudioChannels=2, shotcut__projectFolder=0)
ET.SubElement(tractor, "track", producer="background")
for pl, kind in playlists:
    attrs = {"producer": pl.get("id")}
    if kind == "audio":
        attrs["hide"] = "video"
    ET.SubElement(tractor, "track", **attrs)
for idx, (pl, kind) in enumerate(playlists, start=1):
    t = ET.SubElement(tractor, "transition", id=nid("transition"))
    props(t, a_track=0, b_track=idx, mlt_service="mix", always_active=1, sum=1)
    if kind == "video":
        t = ET.SubElement(tractor, "transition", id=nid("transition"))
        props(t, a_track=0, b_track=idx, version=0.9, mlt_service="qtblend", threads=0,
              disable=0, compositing=0, distort=0, rotate_center=0)

ET.indent(root, space="  ")
ET.ElementTree(root).write(OUT, encoding="utf-8", xml_declaration=True)
print("wrote", OUT, "frames", TOTAL)
