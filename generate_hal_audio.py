#!/usr/bin/env python3
"""Regenerate HAL website narration using macOS native speech."""
import argparse
from pathlib import Path
from html.parser import HTMLParser
import platform
import shutil
import subprocess
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

def run(*args):
    subprocess.run(args, check=True)

def duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)], text=True))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder', nargs='?', default='.', help='Extracted website folder containing index.html')
    p.add_argument('--voice', default='Karen', help='Installed macOS voice (default: Karen, Australian English)')
    p.add_argument('--seconds', type=float, default=20, help='Target duration per recording')
    a = p.parse_args()
    if not 10 <= a.seconds <= 60: p.error('--seconds must be between 10 and 60')
    if platform.system() != 'Darwin': p.error('Run this script on macOS.')
    for tool in ('say','ffmpeg','ffprobe'):
        if not shutil.which(tool): p.error(f'{tool} not found. Install FFmpeg with brew install ffmpeg.')
    root = Path(a.folder).expanduser().resolve()
    parser = Transcripts(); parser.feed((root/'index.html').read_text(encoding='utf-8'))
    if any(not parser.data.get(s,'').strip() for s in STATIONS): p.error('Could not find all six transcripts in index.html.')
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        work = Path(tmp)
        for s in STATIONS:
            text = parser.data[s].strip(); wav = work/f'{s}.aiff'; mp3 = work/f'{s}.mp3'
            rate = max(90, min(220, round(len(text.split())*60/(a.seconds-0.5))))
            for _ in range(3):
                if wav.exists(): wav.unlink()
                run('say','-v',a.voice,'-r',str(rate),'-o',str(wav),text)
                d = duration(wav)
                if abs(d-(a.seconds-0.3)) < 0.6: break
                rate = max(85,min(260,round(rate*d/(a.seconds-0.3))))
            # Preserve pitch when making a small final timing adjustment; pad shorter clips.
            tempo = max(1.0, d/(a.seconds-0.15))
            if tempo > 2: raise RuntimeError(f'{s}: narration too long; adjust speech rate.')
            run('ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(wav),'-af',f'atempo={tempo:.6f},apad','-t',str(a.seconds),'-ac','1','-ar','44100','-c:a','libmp3lame','-b:a','96k',str(mp3))
            print(f'{s}.mp3: {duration(mp3):.2f} seconds', flush=True)
        backup = root/'audio-backup'; backup.mkdir(exist_ok=True)
        for s in STATIONS:
            dest = root/f'{s}.mp3'
            if dest.exists() and not (backup/dest.name).exists(): shutil.copy2(dest,backup/dest.name)
            shutil.copy2(work/dest.name,dest)
    print(f'Updated six MP3 files in {root}. Original audio saved in audio-backup.')

if __name__ == '__main__': main()
