from __future__ import annotations
import os
import urllib.parse
from dataclasses import dataclass, field
from typing import List
import aaf2, aaf2.mobs, aaf2.mobslots, aaf2.components

@dataclass
class AAFClip:
    clip_id: str
    track_name: str
    source_file: str
    source_in: float
    source_out: float
    timeline_pos: float
    clip_name: str = ""
    source_hint: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, self.source_out - self.source_in)

@dataclass
class AAFTrack:
    name: str
    clips: List[AAFClip] = field(default_factory=list)
    suggested_role: str = "unknown"

@dataclass
class AAFSession:
    tracks: List[AAFTrack]
    source_path: str
    missing_media: List[str] = field(default_factory=list)

def parse_aaf(path: str, groups: list) -> AAFSession:
    tracks: List[AAFTrack] = []
    missing: List[str] = []
    aaf_dir = os.path.dirname(os.path.abspath(path))

    with aaf2.open(path, "r") as aaf:
        comp_mob = None
        for mob in aaf.content.mobs:
            if isinstance(mob, aaf2.mobs.CompositionMob):
                comp_mob = mob
                break

        if comp_mob is None:
            raise RuntimeError("Invalid AAF file")

        for slot in comp_mob.slots:
            if not isinstance(slot, aaf2.mobslots.TimelineMobSlot):
                continue
            try:
                mk = slot.media_kind
            except Exception:
                mk = ""
            if mk not in ("Sound", "sound", "SoundWithTimecode"):
                continue

            track_name = _slot_name(slot)
            edit_rate = float(slot.edit_rate)
            try:
                origin = int(slot.origin)
            except Exception:
                origin = 0

            clips: List[AAFClip] = []
            seq_offset = 0

            for comp in _iter_components(slot.segment):
                comp_len = _component_length(comp)
                source_clip = _unwrap_source_clip(comp, aaf2)

                if source_clip is not None:
                    timeline_pos = (seq_offset - origin) / edit_rate
                    source_in = _component_start(source_clip) / edit_rate
                    source_out = source_in + comp_len / edit_rate

                    src_file, unresolved = _resolve_source_file(source_clip, aaf_dir, aaf)
                    if unresolved and unresolved not in missing:
                        missing.append(unresolved)

                    clips.append(AAFClip(
                        clip_id = f"{track_name}__{len(clips)}",
                        track_name = track_name,
                        source_file = src_file,
                        source_in = source_in,
                        source_out = source_out,
                        timeline_pos = timeline_pos,
                        clip_name = _get_clip_name(source_clip),
                        source_hint= unresolved,
                    ))
                seq_offset += comp_len

            if clips:
                tracks.append(AAFTrack(
                    name = track_name,
                    clips = clips,
                    suggested_role = _suggest_role(track_name, groups),
                ))
    return AAFSession(tracks=tracks, source_path=path, missing_media=missing)

def resolve_missing_media(session: AAFSession, search_dir: str) -> int:
    """
    Try to resolve unresolved clips by searching search_dir recursively for
    files whose basename matches the stored source_hint.

    Updates clip.source_file in place and rebuilds session.missing_media.
    Returns the number of clips newly resolved.
    """
    if not session.missing_media:
        return 0

    file_index: dict[str, str] = {}
    file_index_lower: dict[str, str] = {}
    try:
        for dirpath, _dirs, filenames in os.walk(search_dir):
            for name in filenames:
                full = os.path.join(dirpath, name)
                file_index.setdefault(name, full)
                file_index_lower.setdefault(name.lower(), full)
    except OSError:
        return 0

    resolved_count = 0
    for track in session.tracks:
        for clip in track.clips:
            if clip.source_file or not clip.source_hint:
                continue
            basename = _hint_basename(clip.source_hint)
            if not basename:
                continue
            found = file_index.get(basename) or file_index_lower.get(basename.lower())
            if found:
                clip.source_file = found
                clip.source_hint = ""
                resolved_count += 1

    still_missing: list[str] = []
    seen: set[str] = set()
    for track in session.tracks:
        for clip in track.clips:
            if not clip.source_file and clip.source_hint and clip.source_hint not in seen:
                still_missing.append(clip.source_hint)
                seen.add(clip.source_hint)
    session.missing_media = still_missing

    return resolved_count


def _suggest_role(name: str, groups: list) -> str:
    n = name.lower()
    # for g in groups:
    #     if g in n:
    #         return g
    # return "unknown"
    if "4060" in n:    return "4060"
    if "4061" in n:    return "4061"
    if "416" in n:     return "416"
    if "selects" in n: return "selects"
    if "alts" in n:    return "alts"
    return "unknown"

def _slot_name(slot) -> str:
    try:
        return str(slot.name) or f"Track_{slot.index}"
    except Exception:
        try:
            return f"Track_{slot.index}"
        except Exception:
            return "Track"

def _iter_components(segment):
    try:
        return list(segment.components)
    except AttributeError:
        return [segment]

def _unwrap_source_clip(comp, aaf2_module):
    """Return the SourceClip inside comp, or None.

    Pro Tools wraps every clip in an OperationGroup (gain/automation);
    the real SourceClip lives in OperationGroup.segments[0].
    """
    try:
        if isinstance(comp, aaf2_module.components.SourceClip):
            return comp
        if type(comp).__name__ == "OperationGroup":
            for s in comp.segments:
                if isinstance(s, aaf2_module.components.SourceClip):
                    return s
    except Exception:
        pass
    return None

def _component_length(comp) -> int:
    try:
        return int(comp.length)
    except Exception:
        return 0

def _component_start(comp) -> int:
    try:
        return int(comp.start)
    except Exception:
        return 0

def _get_clip_name(source_clip) -> str:
    try:
        mob = source_clip.mob
        if mob is not None:
            name = str(mob.name or "").strip()
            if name:
                return name
    except Exception:
        pass
    return ""

def _hint_basename(hint: str) -> str:
    """
    Extract just the filename from a source_hint, which may be:
      - a POSIX absolute path   /Volumes/Drive/Audio Files/clip.wav
      - a Windows absolute path C:\\path\\to\\clip.wav
      - a raw file:// URI that _uri_to_path didn't decode (rare)
    """
    if hint.lower().startswith("file://"):
        try:
            hint = urllib.parse.unquote(urllib.parse.urlparse(hint).path)
        except Exception:
            pass
    normalised = hint.replace("\\", "/").rstrip("/")
    return normalised.rsplit("/", 1)[-1]

def _resolve_source_file(source_clip, aaf_dir: str, aaf_file) -> tuple[str, str]:
    """
    Walk SourceClip → MasterMob → SourceMob → FileDescriptor → locator URL.

    Returns (resolved_path, unresolved_hint).
    resolved_path is "" if the file could not be found.
    unresolved_hint is the raw URI/path when resolution failed, else "".
    """
    try:
        master_mob = source_clip.mob
        if master_mob is None:
            return "", ""

        source_mob = None
        for ms in master_mob.slots:
            try:
                for ic in _iter_components(ms.segment):
                    if type(ic).__name__ == "SourceClip":
                        candidate = ic.mob
                        if candidate is not None and type(candidate).__name__ == "SourceMob":
                            source_mob = candidate
                            break
            except Exception:
                continue
            if source_mob is not None:
                break

        if source_mob is None:
            return "", ""

        desc      = source_mob.descriptor
        locators  = list(desc.locator) if desc.locator else []

        for loc in locators:
            try:
                uri  = str(loc["URLString"].value)
                path = _uri_to_path(uri)

                if os.path.isfile(path):
                    return path, ""

                basename = _hint_basename(path or uri)
                if not basename:
                    return "", path or uri

                # Try AAF directory itself
                candidate = os.path.join(aaf_dir, basename)
                if os.path.isfile(candidate):
                    return candidate, ""

                # Try one level of subdirectories (covers "Audio Files/" structure)
                try:
                    for entry in os.scandir(aaf_dir):
                        if entry.is_dir():
                            candidate = os.path.join(entry.path, basename)
                            if os.path.isfile(candidate):
                                return candidate, ""
                except OSError:
                    pass

                return "", path or uri
            except Exception:
                continue

    except Exception:
        pass

    return "", ""


def _uri_to_path(uri: str) -> str:
    if uri.startswith("file://") or uri.startswith("FILE://"):
        parsed = urllib.parse.urlparse(uri)
        path   = urllib.parse.unquote(parsed.path)
        # Windows: file:///C:/foo → /C:/foo — strip leading slash
        if os.name == "nt" and len(path) > 2 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        return path
    return uri