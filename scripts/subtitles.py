#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
video-subtitles: 本地识别 → Agent 翻译 → SRT / 视频渲染

Copyright (c) 2026 wangjianqi and video-subtitles contributors
Licensed under the MIT License. See LICENSE for details.

SPDX-License-Identifier: MIT
"""
import argparse
import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave
from functools import lru_cache


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def probe(path):
    try:
        executable = os.environ.get('SUBTITLE_FFPROBE') or 'ffprobe'
        r = run([executable, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', path], capture_output=True, text=True)
        info = json.loads(r.stdout)
    except (OSError, subprocess.CalledProcessError):
        # 某些系统没有可读取本地文件的 ffprobe；用完整 FFmpeg 回读媒体信息。
        r = subprocess.run([ffmpeg_for('srt'), '-hide_banner', '-i', str(path)], capture_output=True, text=True)
        match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', r.stderr)
        if not match:
            raise ValueError('无法读取媒体时长：' + r.stderr[-500:])
        h, m, sec = map(float, match.groups())
        info = dict(format=dict(duration=h*3600+m*60+sec), streams=[])
        for line in r.stderr.splitlines():
            if 'Stream #' in line:
                for kind in ('video', 'audio', 'subtitle'):
                    if kind.capitalize() + ':' in line:
                        info['streams'].append(dict(codec_type=kind))
    if not any(s['codec_type'] == 'video' for s in info['streams']):
        raise ValueError('输入不含视频轨道')
    return info


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def free_paths(paths):
    for path in paths:
        if path.exists():
            raise ValueError(f'输出已存在，请使用新的输出目录或文件名：{path}')


def transcribe(a):
    video = Path(a.video).resolve()
    info = probe(video)
    if not any(s['codec_type'] == 'audio' for s in info['streams']):
        raise ValueError('输入不含音轨，不能识别对白')
    out = Path(a.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    source, target = out / 'source.json', out / 'translation.json'
    free_paths([source, target])
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / 'audio.wav'
        cmd = [ffmpeg_for('srt'), '-v', 'error', '-nostdin', '-i', video]
        if a.limit_seconds:
            cmd += ['-t', str(a.limit_seconds)]
        run(cmd + ['-map', '0:a:0', '-ac', '1', '-ar', '16000', audio])
        if a.backend == 'mlx':
            import mlx_whisper
            import numpy as np
            with wave.open(str(audio), 'rb') as wav:
                samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            result = mlx_whisper.transcribe(samples, path_or_hf_repo=a.model or 'mlx-community/whisper-small-mlx', language=None if a.source_lang == 'auto' else a.source_lang, task='transcribe', word_timestamps=True, verbose=False)
            lang, raw = result['language'], result['segments']
        else:
            from faster_whisper import WhisperModel
            model = WhisperModel(a.model or 'small', device='cpu', compute_type='int8')
            segments, result = model.transcribe(str(audio), language=None if a.source_lang == 'auto' else a.source_lang, task='transcribe', vad_filter=True, word_timestamps=True)
            lang = result.language
            raw, reported = [], 0
            for segment in segments:
                raw.append(dict(start=segment.start, end=segment.end, text=segment.text, words=[dict(start=w.start, end=w.end, word=w.word) for w in (segment.words or [])]))
                if segment.end >= reported + 30:
                    print(f'已识别至 {segment.end:.0f} 秒', file=sys.stderr, flush=True)
                    reported = segment.end
    duration = min(float(info['format']['duration']), a.limit_seconds or float('inf'))
    cues = segment_cues(raw, lang, duration)
    if not cues:
        raise ValueError('未识别到有效对白；请检查音轨、模型及语言参数')
    target_lang = a.target_lang or ('zh' if lang == 'en' else 'en' if lang == 'zh' else None)
    if not target_lang:
        raise ValueError(f'检测到 {lang}，请明确 --target-lang')
    data = dict(video=str(video), duration=duration, source_language=lang, target_language=target_lang, preview=bool(a.limit_seconds), segments=cues)
    save(source, data)
    save(target, dict(target_language=target_lang, segments=[dict(id=s['id'], source_text=s['text'], text='') for s in cues]))
    print(json.dumps(dict(source=str(source), translation=str(target), segments=len(cues), source_language=lang), ensure_ascii=False))


def append_cue(cues, words, duration):
    if not words:
        return
    start = max(0, float(words[0]['start']), cues[-1]['end'] if cues else 0)
    end = min(duration, float(words[-1]['end']))
    text = ''.join(w['word'] for w in words).strip()
    if text and end > start:
        cues.append(dict(id=len(cues) + 1, start=start, end=end, text=text))


def segment_cues(raw, lang, duration):
    # 汇总连续片段后切分，避免 Whisper 原始 segment 边界制造碎条。
    cues, group = [], []
    limit = 24 if lang == 'zh' else 72
    for segment in raw:
        words = segment.get('words') or [dict(start=segment['start'], end=segment['end'], word=segment['text'])]
        for word in words:
            gap = group and float(word['start']) - float(group[-1]['end']) > 0.8
            overflow = group and (float(word['end']) - float(group[0]['start']) > 6 or len(''.join(w['word'] for w in group)) + len(word['word']) > limit)
            if gap or overflow:
                # 优先回退到最近的标点；无标点才按完整词边界切。
                boundary = next((i + 1 for i in range(len(group)-1, -1, -1) if re.search(r'[.,!?;:，。！？；：]["”\']?$', group[i]['word'].strip())), len(group))
                append_cue(cues, group[:boundary], duration)
                group = group[boundary:]
            word = dict(word)
            if lang != 'zh' and group and group[-1]['word'][-1:].isalnum() and word['word'][:1].isalnum():
                word['word'] = ' ' + word['word']
            group.append(word)
            if re.search(r'[.!?。！？]["”\']?$', word['word'].strip()):
                append_cue(cues, group, duration)
                group = []
    append_cue(cues, group, duration)
    return merge_short_cues(cues, lang)


def merge_short_cues(cues, lang):
    cues = [dict(cue) for cue in cues]
    i = 0
    while i < len(cues):
        cue = cues[i]
        short = cue['end'] - cue['start'] < 0.4 or len(cue['text'].strip()) < 4
        continuation = (lang == 'en' and i > 0 and cue['end'] - cue['start'] < 1.2
                        and len(cue['text'].split()) <= 3
                        and not re.search(r'[.!?]$', cues[i-1]['text']))
        if short or continuation:
            # 不跨明显静音合并，也不让正常短回答无限扩成长字幕。
            candidates = [j for j in (i-1, i+1) if 0 <= j < len(cues)
                          and max(cue['end'], cues[j]['end']) - min(cue['start'], cues[j]['start']) <= 8
                          and max(cue['start'], cues[j]['start']) - min(cue['end'], cues[j]['end']) <= 0.8]
            if candidates:
                j = i-1 if continuation and i-1 in candidates else min(candidates, key=lambda j: abs(cues[j]['start'] - cue['start']))
                left, right = sorted((i, j))
                first, last = cues[left], cues[right]
                cues[left] = dict(id=0, start=first['start'], end=last['end'], text=first['text'] + ('' if lang == 'zh' else ' ') + last['text'])
                del cues[right]
                i = max(0, left - 1)
                continue
        i += 1
    for i, cue in enumerate(cues, 1):
        cue['id'] = i
    return cues


def default_font():
    return {'darwin': 'PingFang SC', 'win32': 'Microsoft YaHei'}.get(sys.platform, 'Noto Sans CJK SC')


def warn_layout(text, language, cue_id):
    limit = 22 if language == 'zh' else 42
    lines = text.splitlines()
    if len(lines) > 2 or any(len(line) > limit for line in lines):
        print(f'警告：字幕 ID {cue_id} 超过建议的两行 / 每行 {limit} 字，请精炼或按语义换行', file=sys.stderr)


def stamp(seconds):
    ms = round(seconds * 1000)
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    secs, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02},{ms:03}'


@lru_cache(maxsize=3)
def ffmpeg_for(mode):
    candidates = [os.environ.get('SUBTITLE_FFMPEG'), shutil.which('ffmpeg')]
    try:
        import imageio_ffmpeg
        candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
    except ImportError:
        pass
    for c in candidates:
        if c and (mode != 'burn' or ' subtitles ' in run([c, '-hide_banner', '-filters'], capture_output=True, text=True).stdout):
            return c
    raise ValueError('烧录需要含 libass/subtitles 滤镜的 FFmpeg。设置 SUBTITLE_FFMPEG，或用 uv run --with imageio-ffmpeg 执行')


def render(a):
    source = json.loads(Path(a.source).read_text(encoding='utf-8'))
    target = json.loads(Path(a.translation).read_text(encoding='utf-8'))
    if target.get('target_language') != source['target_language']:
        raise ValueError('译文目标语言与 source.json 不一致')
    cues, translations = source['segments'], target['segments']
    if not cues or len(translations) != len(cues) or [s['id'] for s in translations] != [s['id'] for s in cues]:
        raise ValueError('译文 ID、顺序、数量必须与源字幕完全一致')
    blocks, prev = [], 0
    duration = float(source['duration'])
    for s, t in zip(cues, translations):
        start, end = float(s['start']), float(s['end'])
        if not all(math.isfinite(x) for x in [start, end]) or not 0 <= prev <= start < end <= duration or round(end*1000) <= round(start*1000):
            raise ValueError(f'非法时间轴：ID {s["id"]}')
        prev = end
        text = t['text'].strip()
        if not text or '\n\n' in text or '\r' in text or '\x00' in text or '-->' in text:
            raise ValueError(f'空译文或非法字幕文本：ID {s["id"]}')
        warn_layout(text, source['target_language'], s['id'])
        if a.bilingual:
            warn_layout(s['text'], source['source_language'], s['id'])
            text += '\n' + s['text'].strip().replace('\n', ' ')
        blocks.append(f'{s["id"]}\n{stamp(start)} --> {stamp(end)}\n{text}\n')
    out = Path(a.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    srt, video = out / 'subtitles.srt', out / 'subtitled.mp4'
    free_paths([srt] + ([video] if a.mode != 'srt' else []))
    srt.write_text('\n'.join(blocks), encoding='utf-8')
    if a.mode != 'srt':
        executable = ffmpeg_for(a.mode)
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copyfile(srt, Path(tmp) / 'captions.srt')
            cmd = [executable, '-v', 'error', '-nostdin', '-n', '-i', source['video']]
            if a.mode == 'soft':
                cmd += ['-i', 'captions.srt', '-map', '0:v:0', '-map', '0:a?', '-map', '1:0', '-c:v', 'copy', '-c:a', 'copy', '-c:s', 'mov_text', '-metadata:s:s:0', 'language=' + {'zh':'zho', 'en':'eng'}.get(source['target_language'], 'und'), '-disposition:s:0', 'default']
            else:
                font = a.font
                font_file = Path(a.font_file).expanduser() if a.font_file else None
                if font_file and not font_file.is_file():
                    raise ValueError(f'字体文件不存在：{font_file}')
                if sys.platform == 'darwin' and not font_file and font == 'PingFang SC':
                    pingfang = Path('/System/Library/Fonts/PingFang.ttc')
                    fallback = Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
                    if pingfang.is_file():
                        font_file = pingfang
                    elif fallback.is_file():
                        font, font_file = 'Arial Unicode MS', fallback
                        print('警告：未发现 PingFang.ttc，使用已安装的 Arial Unicode MS 字体文件', file=sys.stderr)
                    else:
                        raise ValueError('未发现默认中文字体文件；请通过 --font-file 指定支持中文的字体，并用 --font 指定其字体族名')
                font_filter = ''
                if font_file:
                    fonts = Path(tmp) / 'fonts'
                    fonts.mkdir()
                    shutil.copyfile(font_file, fonts / ('subtitle' + font_file.suffix))
                    font_filter = ':fontsdir=fonts'
                if any(x in font for x in "'\\,:;[]"):
                    raise ValueError('字体名包含不支持的滤镜分隔符')
                style = f'FontName={font},FontSize={a.font_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,MarginV={a.margin_v}'
                cmd += ['-map', '0:v:0', '-map', '0:a?', '-vf', f"subtitles=captions.srt{font_filter}:force_style='{style}'", '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', a.audio_codec]
                if a.audio_codec == 'aac':
                    cmd += ['-b:a', '192k']
            if source.get('preview'):
                cmd += ['-t', str(duration)]
            run(cmd + ['-movflags', '+faststart', video], cwd=tmp)
        actual = probe(video)
        if abs(float(actual['format']['duration']) - duration) > 1:
            raise ValueError('输出时长与源时间轴不一致，请检查产物')
    print(json.dumps(dict(srt=str(srt), video=str(video) if a.mode != 'srt' else None, segments=len(cues)), ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    t = sub.add_parser('transcribe')
    t.add_argument('video')
    t.add_argument('--output-dir', required=True)
    t.add_argument('--source-lang', default='auto')
    t.add_argument('--target-lang', choices=['zh', 'en'])
    t.add_argument('--backend', choices=['mlx', 'faster-whisper'], default='mlx' if sys.platform == 'darwin' and os.uname().machine == 'arm64' else 'faster-whisper')
    t.add_argument('--model')
    t.add_argument('--limit-seconds', type=float)
    r = sub.add_parser('render')
    r.add_argument('--source', required=True)
    r.add_argument('--translation', required=True)
    r.add_argument('--output-dir', required=True)
    r.add_argument('--mode', choices=['burn', 'soft', 'srt'], default='burn')
    r.add_argument('--bilingual', action='store_true')
    r.add_argument('--font', default=default_font())
    r.add_argument('--audio-codec', choices=['copy', 'aac'], default='copy', help='烧录默认复制音频；不兼容 MP4 的源音频可选 aac')
    r.add_argument('--font-file', help='显式加载 TTF/OTF/TTC 字体文件，配合 --font 字体族名')
    r.add_argument('--font-size', type=int, default=22)
    r.add_argument('--margin-v', type=int, default=24)
    a = p.parse_args()
    try:
        if a.command == 'transcribe' and a.limit_seconds is not None and a.limit_seconds <= 0:
            raise ValueError('--limit-seconds 必须大于零')
        (transcribe if a.command == 'transcribe' else render)(a)
    except (ValueError, OSError, subprocess.CalledProcessError, ImportError) as e:
        if 'socksio' in str(e):
            print('SOCKS 代理依赖缺失：在 uv run 中添加 --with \"httpx[socks]\" 后重试', file=sys.stderr)
        print(f'失败：{e}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
