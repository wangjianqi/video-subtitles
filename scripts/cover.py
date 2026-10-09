#!/usr/bin/env python3
"""少量抽帧拼图，供 Agent 挑选社交平台封面；不使用视觉模型 API。"""
import argparse
import json
import math
from pathlib import Path
import sys
from subtitles import ffmpeg_for, free_paths, probe, run, save


def frame(video, seconds, output, thumbnail=False):
    args = [ffmpeg_for('srt'), '-v', 'error', '-nostdin', '-n', '-ss', str(seconds), '-i', video, '-frames:v', '1']
    if thumbnail:
        args += ['-vf', 'scale=480:270:force_original_aspect_ratio=decrease,pad=480:270:(ow-iw)/2:(oh-ih)/2:black']
    run(args + ['-q:v', '2', output])
    if not output.is_file() or not output.stat().st_size:
        raise ValueError(f'抽帧失败：{seconds} 秒')


def sample(a):
    video = Path(a.video).resolve()
    duration = float(probe(video)['format']['duration'])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('无法取得有效视频时长')
    times = a.times or [duration * f for f in (.08, .24, .4, .56, .72, .88)]
    if not 1 <= len(times) <= 6 or any(not math.isfinite(t) or not 0 <= t < duration for t in times):
        raise ValueError('候选时间点必须为 1–6 个，并位于视频时长范围内')
    out = Path(a.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    sheet, manifest = out / 'contact-sheet.jpg', out / 'candidates.json'
    files = [out / f'candidate-{i+1}.jpg' for i in range(len(times))]
    free_paths([sheet, manifest, *files])
    for t, path in zip(times, files):
        frame(video, t, path, thumbnail=True)
    # 固定 3 列，从左至右、从上至下排列；空格用黑色补齐。
    cmd = [ffmpeg_for('srt'), '-v', 'error', '-nostdin', '-n']
    for file in files:
        cmd += ['-i', file]
    if len(files) == 1:
        import shutil
        shutil.copyfile(files[0], sheet)
    else:
        layout = '|'.join(f'{i%3*480}_{i//3*270}' for i in range(len(files)))
        cmd += ['-filter_complex', f'xstack=inputs={len(files)}:layout={layout}:fill=black', '-frames:v', '1', '-q:v', '3', sheet]
        run(cmd)
    save(manifest, dict(video=str(video), duration=duration, columns=3,
                        candidates=[dict(id=i+1, seconds=t, row=i//3+1, column=i%3+1) for i,t in enumerate(times)]))
    print(json.dumps(dict(sheet=str(sheet), manifest=str(manifest)), ensure_ascii=False))


def export(a):
    data = json.loads(Path(a.manifest).read_text(encoding='utf-8'))
    candidate = next((c for c in data['candidates'] if c['id'] == a.select), None)
    if candidate is None:
        raise ValueError('选择 ID 不在候选列表中')
    out = Path(a.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cover, metadata = out / 'cover.jpg', out / 'cover.json'
    free_paths([cover, metadata])
    frame(data['video'], candidate['seconds'], cover)
    save(metadata, dict(video=data['video'], seconds=candidate['seconds'], candidate_id=a.select,
                        reason=a.reason, cover=str(cover)))
    print(json.dumps(dict(cover=str(cover), metadata=str(metadata)), ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    s = commands.add_parser('sample')
    s.add_argument('video')
    s.add_argument('--times', nargs='+', type=float)
    s.add_argument('--output-dir', required=True)
    e = commands.add_parser('export')
    e.add_argument('--manifest', required=True)
    e.add_argument('--select', type=int, required=True)
    e.add_argument('--reason', required=True, help='简短说明所选画面与视频主题的关系')
    e.add_argument('--output-dir', required=True)
    a = parser.parse_args()
    try:
        (sample if a.command == 'sample' else export)(a)
    except (ValueError, OSError, __import__('subprocess').CalledProcessError) as error:
        print(f'失败：{error}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
