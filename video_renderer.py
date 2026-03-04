"""30秒竖屏 TTS 视频生成器 — 信号塔Tech"""
import asyncio
import subprocess
import os
from pathlib import Path

TTS_VOICE = "zh-CN-YunxiNeural"
TTS_RATE = "+30%"
VIDEO_W, VIDEO_H = 1080, 1920
COVER_DUR = 2
OUTRO_DUR = 2


def _get_duration(path):
    r = subprocess.run(
        ["ffprobe", "-i", str(path), "-show_entries", "format=duration",
         "-v", "quiet", "-of", "csv=p=0"],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


async def _generate_tts(texts, out_dir):
    """生成每张卡片的 TTS 音频，返回 [(path, duration)]"""
    import edge_tts
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    results = []
    for i, text in enumerate(texts):
        path = audio_dir / f"card{i}.mp3"
        comm = edge_tts.Communicate(text, TTS_VOICE, rate=TTS_RATE)
        await comm.save(str(path))
        dur = _get_duration(path)
        results.append((str(path), dur))
        print(f"  🔊 Card {i}: {dur:.1f}s")
    return results


def generate_video(title, card_images, narrations, out_dir):
    """
    生成 30 秒竖屏视频
    - title: 视频标题（封面用）
    - card_images: [cover.png, card1.png, ..., card6.png] 绝对路径
    - narrations: [str] 每张卡片的旁白文字（6条）
    - out_dir: 输出目录
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. 生成 TTS
    print("生成语音...")
    audio_data = asyncio.run(_generate_tts(narrations, out_dir))
    total_audio = sum(d for _, d in audio_data)
    print(f"  总语音: {total_audio:.1f}s + 封面{COVER_DUR}s + 结尾{OUTRO_DUR}s = {total_audio + COVER_DUR + OUTRO_DUR:.1f}s")

    # 2. 用 ffmpeg 拼接视频
    # 策略：每张卡片图片显示时长 = 对应音频时长，封面和结尾用固定时长
    print("合成视频...")

    # 先把所有音频拼成一个
    audio_list = out_dir / "audio" / "concat.txt"
    # 生成静音封面音频
    silence_cover = out_dir / "audio" / "silence_cover.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(COVER_DUR), "-q:a", "9", str(silence_cover),
    ], capture_output=True)

    silence_outro = out_dir / "audio" / "silence_outro.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
        "-t", str(OUTRO_DUR), "-q:a", "9", str(silence_outro),
    ], capture_output=True)

    # 写 concat 列表
    with open(audio_list, "w") as f:
        f.write(f"file '{silence_cover}'\n")
        for audio_path, _ in audio_data:
            f.write(f"file '{audio_path}'\n")
        f.write(f"file '{silence_outro}'\n")

    merged_audio = out_dir / "audio" / "merged.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(audio_list), "-c", "copy", str(merged_audio),
    ], capture_output=True)

    # 3. 构建视频：每张图片按对应时长显示
    # 图片顺序：cover, card1-6, cover(作为outro)
    durations = [COVER_DUR] + [d for _, d in audio_data] + [OUTRO_DUR]
    images = [card_images[0]] + card_images[1:7] + [card_images[0]]

    # 用 ffmpeg concat demuxer
    img_list = out_dir / "images.txt"
    with open(img_list, "w") as f:
        for img, dur in zip(images, durations):
            f.write(f"file '{img}'\n")
            f.write(f"duration {dur}\n")
        # ffmpeg concat 需要最后一张图片再写一次
        f.write(f"file '{images[-1]}'\n")

    video_path = out_dir / "video.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(img_list),
        "-i", str(merged_audio),
        "-vf", f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=decrease,pad={VIDEO_W}:{VIDEO_H}:(ow-iw)/2:(oh-ih)/2:color=white",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-pix_fmt", "yuv420p",
        str(video_path),
    ], capture_output=True)

    final_dur = _get_duration(video_path)
    size_mb = os.path.getsize(video_path) / 1024 / 1024
    print(f"  ✅ {video_path}: {final_dur:.1f}s, {size_mb:.1f}MB")
    return str(video_path)
