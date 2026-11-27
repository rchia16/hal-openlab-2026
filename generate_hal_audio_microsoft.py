#!/usr/bin/env python3
"""Regenerate HAL website narration using Microsoft Edge neural speech."""
import argparse
from pathlib import Path
from html.parser import HTMLParser
import asyncio
import shutil
import subprocess
import edge_tts
import tempfile

STATIONS = ('yihao', 'nhan', 'shurui', 'minh', 'yu', 'games')
class Transcripts(HTMLParser):
    def __init__(self):
        super().__init__(); self.station = None; self.after_heading = False; self.capture = False; self.data = {}
    def handle_starttag(self, tag, attrs):
        if tag == 'section':
            self.station = dict(attrs).get('id'); self.after_heading = False
        if tag == 'p' and self.station in STATIONS and self.after_heading:
            self.capture = True; self.data[self.station] = ''
    def handle_endtag(self, tag):
        if tag == 'h3' and self.station in STATIONS: self.after_heading = True
        if tag == 'p' and self.capture: self.capture = False; self.after_heading = False
        if tag == 'section': self.station = None
    def handle_data(self, data):
        if self.capture: self.data[self.station] += data

async def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder', nargs='?', default='.')
    p.add_argument('--voice', default='en-AU-NatashaNeural')
    p.add_argument('--seconds', type=float, default=20)
    p.add_argument('--rate', default='+0%', help='Initial speaking rate, e.g. -5%%')
    a = p.parse_args()
    if not 10 <= a.seconds <= 60: p.error('--seconds must be between 10 and 60')
    root = Path(a.folder).expanduser().resolve()
    parser = Transcripts(); parser.feed((root/'index.html').read_text(encoding='utf-8'))
    if any(not parser.data.get(s,'').strip() for s in STATIONS): p.error('Could not find all six transcripts in index.html.')
    if not shutil.which('ffprobe'): p.error('Install ffmpeg: brew install ffmpeg')
    def duration(path):
        return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)], text=True))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for s in STATIONS:
            dest = work/f'{s}.mp3'
            rate = int(a.rate.rstrip('%'))
            for attempt in range(3):
                await edge_tts.Communicate(parser.data[s].strip(), a.voice, rate=f'{rate:+d}%').save(str(dest))
                d = duration(dest)
                if abs(d-a.seconds) <= 1.5 or attempt == 2: break
                new_rate = max(-25, min(35, round((100+rate)*d/a.seconds-100)))
                if new_rate == rate: break
                rate = new_rate
            print(f'{s}.mp3: {d:.1f}s (rate {rate:+d}%)', flush=True)
        backup = root.parent/(root.name+'-audio-backup')
        backup.mkdir(exist_ok=True)
        for s in STATIONS:
            dest = root/f'{s}.mp3'
            if dest.exists() and not (backup/dest.name).exists(): shutil.copy2(dest,backup/dest.name)
            shutil.copy2(work/dest.name,dest)
    print(f'Updated six MP3 files. Backup: {backup}')

if __name__ == '__main__': asyncio.run(main())
