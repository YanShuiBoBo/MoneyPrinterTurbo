import glob
import os
import random
from typing import List

from loguru import logger
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    afx,
    concatenate_videoclips,
)
from moviepy.video.tools.subtitles import SubtitlesClip
from PIL import ImageFont

from app.models import const
from app.models.schema import (
    MaterialInfo,
    VideoAspect,
    VideoConcatMode,
    VideoParams,
    VideoTransitionMode,
)
from app.services.utils import video_effects
from app.utils import utils


def get_bgm_file(bgm_type: str = "random", bgm_file: str = ""):
    if not bgm_type:
        return ""

    if bgm_file and os.path.exists(bgm_file):
        return bgm_file

    if bgm_type == "random":
        suffix = "*.mp3"
        song_dir = utils.song_dir()
        files = glob.glob(os.path.join(song_dir, suffix))
        return random.choice(files)

    return ""


def combine_videos(
        # 输出视频的保存路径
        combined_video_path: str,
        # 输入视频路径列表（需要拼接的原始视频）
        video_paths: List[str],
        # 背景音乐文件路径
        audio_file: str,
        # 视频比例设置（默认竖屏）
        video_aspect: VideoAspect = VideoAspect.portrait,
        # 拼接模式（默认随机顺序）
        video_concat_mode: VideoConcatMode = VideoConcatMode.random,
        # 转场效果模式（默认无转场）
        video_transition_mode: VideoTransitionMode = None,
        # 单个片段最大时长（默认5秒）
        max_clip_duration: int = 5,
        # 视频渲染线程数（默认2线程）
        threads: int = 2,
) -> str:
    # 加载背景音乐文件
    audio_clip = AudioFileClip(audio_file)
    # 获取音频总时长（单位：秒）
    audio_duration = audio_clip.duration
    # 记录音频时长日志
    logger.info(f"max duration of audio: {audio_duration} seconds")

    # 计算每个视频片段的建议时长（此处被max_clip_duration覆盖，实际未使用）
    req_dur = audio_duration / len(video_paths)
    req_dur = max_clip_duration  # 强制使用最大片段时长
    logger.info(f"each clip will be maximum {req_dur} seconds long")

    # 获取输出文件所在目录
    output_dir = os.path.dirname(combined_video_path)

    # 根据选择的宽高比获取目标分辨率
    aspect = VideoAspect(video_aspect)
    video_width, video_height = aspect.to_resolution()

    # 初始化最终视频片段列表
    clips = []
    # 已处理视频总时长
    video_duration = 0

    # 原始视频片段池（切割后的片段）
    raw_clips = []

    # 遍历所有输入视频文件
    for video_path in video_paths:
        # 加载视频并移除原声
        clip = VideoFileClip(video_path).without_audio()
        # 获取当前视频总时长
        clip_duration = clip.duration
        start_time = 0  # 切割起始时间

        # 将长视频切割为小片段
        while start_time < clip_duration:
            # 计算切割结束时间（不超过视频结尾）
            end_time = min(start_time + max_clip_duration, clip_duration)
            # 截取子片段
            split_clip = clip.subclipped(start_time, end_time)
            # 添加到原始片段池
            raw_clips.append(split_clip)
            # 更新切割起始时间
            start_time = end_time
            # 如果是顺序模式，只取第一个有效片段
            if video_concat_mode.value == VideoConcatMode.sequential.value:
                break

    # 如果是随机模式，打乱片段顺序
    if video_concat_mode.value == VideoConcatMode.random.value:
        random.shuffle(raw_clips)

    # 循环添加片段直到覆盖音频时长
    while video_duration < audio_duration:
        for clip in raw_clips:
            # 处理最后一个片段
            if (audio_duration - video_duration) < clip.duration:
                # 截取需要的剩余时长
                clip = clip.subclipped(0, (audio_duration - video_duration))
            # 常规片段处理
            elif req_dur < clip.duration:
                # 截取不超过最大时长
                clip = clip.subclipped(0, req_dur)
            # 统一设置帧率为30fps
            clip = clip.with_fps(30)

            # 获取当前片段分辨率
            clip_w, clip_h = clip.size
            # 分辨率不一致时需要调整
            if clip_w != video_width or clip_h != video_height:
                # 计算宽高比
                clip_ratio = clip.w / clip.h
                video_ratio = video_width / video_height

                if clip_ratio == video_ratio:
                    # 直接缩放至目标分辨率
                    clip = clip.resized((video_width, video_height))
                else:
                    # 计算缩放比例
                    if clip_ratio > video_ratio:
                        # 以宽度为基准缩放
                        scale_factor = video_width / clip_w
                    else:
                        # 以高度为基准缩放
                        scale_factor = video_height / clip_h

                    # 计算新分辨率
                    new_width = int(clip_w * scale_factor)
                    new_height = int(clip_h * scale_factor)
                    # 缩放视频
                    clip_resized = clip.resized(new_size=(new_width, new_height))

                    # 创建黑色背景
                    background = ColorClip(
                        size=(video_width, video_height),
                        color=(0, 0, 0)  # RGB黑色
                    )
                    # 将视频合成到背景中央
                    clip = CompositeVideoClip(
                        [
                            background.with_duration(clip.duration),
                            clip_resized.with_position("center"),
                        ]
                    )

                logger.info(
                    f"resizing video to {video_width} x {video_height}, clip size: {clip_w} x {clip_h}"
                )

            # 随机选择转场方向
            shuffle_side = random.choice(["left", "right", "top", "bottom"])
            logger.info(f"Using transition mode: {video_transition_mode}")

            # 应用转场效果
            if video_transition_mode.value == VideoTransitionMode.none.value:
                pass  # 无效果
            elif video_transition_mode.value == VideoTransitionMode.fade_in.value:
                clip = video_effects.fadein_transition(clip, 1)  # 1秒淡入
            elif video_transition_mode.value == VideoTransitionMode.fade_out.value:
                clip = video_effects.fadeout_transition(clip, 1)  # 1秒淡出
            elif video_transition_mode.value == VideoTransitionMode.slide_in.value:
                clip = video_effects.slidein_transition(clip, 1, shuffle_side)  # 滑动进入
            elif video_transition_mode.value == VideoTransitionMode.slide_out.value:
                clip = video_effects.slideout_transition(clip, 1, shuffle_side)  # 滑动退出
            elif video_transition_mode.value == VideoTransitionMode.shuffle.value:
                # 随机选择转场效果
                transition_funcs = [
                    lambda c: video_effects.fadein_transition(c, 1),
                    lambda c: video_effects.fadeout_transition(c, 1),
                    lambda c: video_effects.slidein_transition(c, 1, shuffle_side),
                    lambda c: video_effects.slideout_transition(c, 1, shuffle_side),
                ]
                shuffle_transition = random.choice(transition_funcs)
                clip = shuffle_transition(clip)

            # 二次时长校验
            if clip.duration > max_clip_duration:
                clip = clip.subclipped(0, max_clip_duration)

            # 将处理后的片段加入最终列表
            clips.append(clip)
            # 更新总时长
            video_duration += clip.duration

    # 将片段列表转换为合成剪辑
    clips = [CompositeVideoClip([clip]) for clip in clips]
    # 拼接所有视频片段
    video_clip = concatenate_videoclips(clips)
    # 强制设置输出帧率
    video_clip = video_clip.with_fps(30)
    logger.info("writing")

    # 输出视频文件（重要参数说明）
    video_clip.write_videofile(
        filename=combined_video_path,  # 输出路径
        threads=threads,  # 多线程渲染
        logger=None,  # 禁用moviepy日志
        temp_audiofile_path=output_dir,  # 临时文件存放目录
        audio_codec="aac",  # 音频编码格式
        fps=30  # 输出帧率
    )
    # 释放视频资源
    video_clip.close()
    logger.success("completed")
    return combined_video_path


def wrap_text(text, max_width, font="Arial", fontsize=60):
    # Create ImageFont
    font = ImageFont.truetype(font, fontsize)

    def get_text_size(inner_text):
        inner_text = inner_text.strip()
        left, top, right, bottom = font.getbbox(inner_text)
        return right - left, bottom - top

    width, height = get_text_size(text)
    if width <= max_width:
        return text, height

    # logger.warning(f"wrapping text, max_width: {max_width}, text_width: {width}, text: {text}")

    processed = True

    _wrapped_lines_ = []
    words = text.split(" ")
    _txt_ = ""
    for word in words:
        _before = _txt_
        _txt_ += f"{word} "
        _width, _height = get_text_size(_txt_)
        if _width <= max_width:
            continue
        else:
            if _txt_.strip() == word.strip():
                processed = False
                break
            _wrapped_lines_.append(_before)
            _txt_ = f"{word} "
    _wrapped_lines_.append(_txt_)
    if processed:
        _wrapped_lines_ = [line.strip() for line in _wrapped_lines_]
        result = "\n".join(_wrapped_lines_).strip()
        height = len(_wrapped_lines_) * height
        # logger.warning(f"wrapped text: {result}")
        return result, height

    _wrapped_lines_ = []
    chars = list(text)
    _txt_ = ""
    for word in chars:
        _txt_ += word
        _width, _height = get_text_size(_txt_)
        if _width <= max_width:
            continue
        else:
            _wrapped_lines_.append(_txt_)
            _txt_ = ""
    _wrapped_lines_.append(_txt_)
    result = "\n".join(_wrapped_lines_).strip()
    height = len(_wrapped_lines_) * height
    # logger.warning(f"wrapped text: {result}")
    return result, height


def generate_video(
    video_path: str,
    audio_path: str,
    subtitle_path: str,
    output_file: str,
    params: VideoParams,
):
    aspect = VideoAspect(params.video_aspect)
    video_width, video_height = aspect.to_resolution()

    logger.info(f"start, video size: {video_width} x {video_height}")
    logger.info(f"  ① video: {video_path}")
    logger.info(f"  ② audio: {audio_path}")
    logger.info(f"  ③ subtitle: {subtitle_path}")
    logger.info(f"  ④ output: {output_file}")

    # https://github.com/harry0703/MoneyPrinterTurbo/issues/217
    # PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: 'final-1.mp4.tempTEMP_MPY_wvf_snd.mp3'
    # write into the same directory as the output file
    output_dir = os.path.dirname(output_file)

    font_path = ""
    if params.subtitle_enabled:
        if not params.font_name:
            params.font_name = "STHeitiMedium.ttc"
        font_path = os.path.join(utils.font_dir(), params.font_name)
        if os.name == "nt":
            font_path = font_path.replace("\\", "/")

        logger.info(f"using font: {font_path}")

    def create_text_clip(subtitle_item):
        params.font_size = int(params.font_size)
        params.stroke_width = int(params.stroke_width)
        phrase = subtitle_item[1]
        max_width = video_width * 0.9
        wrapped_txt, txt_height = wrap_text(
            phrase, max_width=max_width, font=font_path, fontsize=params.font_size
        )
        _clip = TextClip(
            text=wrapped_txt,
            font=font_path,
            font_size=params.font_size,
            color=params.text_fore_color,
            bg_color=params.text_background_color,
            stroke_color=params.stroke_color,
            stroke_width=params.stroke_width,
        )
        duration = subtitle_item[0][1] - subtitle_item[0][0]
        _clip = _clip.with_start(subtitle_item[0][0])
        _clip = _clip.with_end(subtitle_item[0][1])
        _clip = _clip.with_duration(duration)
        if params.subtitle_position == "bottom":
            _clip = _clip.with_position(("center", video_height * 0.95 - _clip.h))
        elif params.subtitle_position == "top":
            _clip = _clip.with_position(("center", video_height * 0.05))
        elif params.subtitle_position == "custom":
            # Ensure the subtitle is fully within the screen bounds
            margin = 10  # Additional margin, in pixels
            max_y = video_height - _clip.h - margin
            min_y = margin
            custom_y = (video_height - _clip.h) * (params.custom_position / 100)
            custom_y = max(
                min_y, min(custom_y, max_y)
            )  # Constrain the y value within the valid range
            _clip = _clip.with_position(("center", custom_y))
        else:  # center
            _clip = _clip.with_position(("center", "center"))
        return _clip

    video_clip = VideoFileClip(video_path)
    audio_clip = AudioFileClip(audio_path).with_effects(
        [afx.MultiplyVolume(params.voice_volume)]
    )

    def make_textclip(text):
        return TextClip(
            text=text,
            font=font_path,
            font_size=params.font_size,
        )

    if subtitle_path and os.path.exists(subtitle_path):
        sub = SubtitlesClip(
            subtitles=subtitle_path, encoding="utf-8", make_textclip=make_textclip
        )
        text_clips = []
        for item in sub.subtitles:
            clip = create_text_clip(subtitle_item=item)
            text_clips.append(clip)
        video_clip = CompositeVideoClip([video_clip, *text_clips])

    bgm_file = get_bgm_file(bgm_type=params.bgm_type, bgm_file=params.bgm_file)
    if bgm_file:
        try:
            bgm_clip = AudioFileClip(bgm_file).with_effects(
                [
                    afx.MultiplyVolume(params.bgm_volume),
                    afx.AudioFadeOut(3),
                    afx.AudioLoop(duration=video_clip.duration),
                ]
            )
            audio_clip = CompositeAudioClip([audio_clip, bgm_clip])
        except Exception as e:
            logger.error(f"failed to add bgm: {str(e)}")

    video_clip = video_clip.with_audio(audio_clip)
    video_clip.write_videofile(
        output_file,
        audio_codec="aac",
        temp_audiofile_path=output_dir,
        threads=params.n_threads or 2,
        logger=None,
        fps=30,
    )
    video_clip.close()
    del video_clip
    logger.success("completed")


def preprocess_video(materials: List[MaterialInfo], clip_duration=4):
    for material in materials:
        if not material.url:
            continue

        ext = utils.parse_extension(material.url)
        try:
            clip = VideoFileClip(material.url)
        except Exception:
            clip = ImageClip(material.url)

        width = clip.size[0]
        height = clip.size[1]
        if width < 480 or height < 480:
            logger.warning(f"video is too small, width: {width}, height: {height}")
            continue

        if ext in const.FILE_TYPE_IMAGES:
            logger.info(f"processing image: {material.url}")
            # Create an image clip and set its duration to 3 seconds
            clip = (
                ImageClip(material.url)
                .with_duration(clip_duration)
                .with_position("center")
            )
            # Apply a zoom effect using the resize method.
            # A lambda function is used to make the zoom effect dynamic over time.
            # The zoom effect starts from the original size and gradually scales up to 120%.
            # t represents the current time, and clip.duration is the total duration of the clip (3 seconds).
            # Note: 1 represents 100% size, so 1.2 represents 120% size.
            zoom_clip = clip.resized(
                lambda t: 1 + (clip_duration * 0.03) * (t / clip.duration)
            )

            # Optionally, create a composite video clip containing the zoomed clip.
            # This is useful when you want to add other elements to the video.
            final_clip = CompositeVideoClip([zoom_clip])

            # Output the video to a file.
            video_file = f"{material.url}.mp4"
            final_clip.write_videofile(video_file, fps=30, logger=None)
            final_clip.close()
            del final_clip
            material.url = video_file
            logger.success(f"completed: {video_file}")
    return materials


if __name__ == "__main__":
    m = MaterialInfo()
    m.url = "/Users/harry/Downloads/IMG_2915.JPG"
    m.provider = "local"
    materials = preprocess_video([m], clip_duration=4)
    print(materials)

    # txt_en = "Here's your guide to travel hacks for budget-friendly adventures"
    # txt_zh = "测试长字段这是您的旅行技巧指南帮助您进行预算友好的冒险"
    # font = utils.resource_dir() + "/fonts/STHeitiMedium.ttc"
    # for txt in [txt_en, txt_zh]:
    #     t, h = wrap_text(text=txt, max_width=1000, font=font, fontsize=60)
    #     print(t)
    #
    # task_id = "aa563149-a7ea-49c2-b39f-8c32cc225baf"
    # task_dir = utils.task_dir(task_id)
    # video_file = f"{task_dir}/combined-1.mp4"
    # audio_file = f"{task_dir}/audio.mp3"
    # subtitle_file = f"{task_dir}/subtitle.srt"
    # output_file = f"{task_dir}/final.mp4"
    #
    # # video_paths = []
    # # for file in os.listdir(utils.storage_dir("test")):
    # #     if file.endswith(".mp4"):
    # #         video_paths.append(os.path.join(utils.storage_dir("test"), file))
    # #
    # # combine_videos(combined_video_path=video_file,
    # #                audio_file=audio_file,
    # #                video_paths=video_paths,
    # #                video_aspect=VideoAspect.portrait,
    # #                video_concat_mode=VideoConcatMode.random,
    # #                max_clip_duration=5,
    # #                threads=2)
    #
    # cfg = VideoParams()
    # cfg.video_aspect = VideoAspect.portrait
    # cfg.font_name = "STHeitiMedium.ttc"
    # cfg.font_size = 60
    # cfg.stroke_color = "#000000"
    # cfg.stroke_width = 1.5
    # cfg.text_fore_color = "#FFFFFF"
    # cfg.text_background_color = "transparent"
    # cfg.bgm_type = "random"
    # cfg.bgm_file = ""
    # cfg.bgm_volume = 1.0
    # cfg.subtitle_enabled = True
    # cfg.subtitle_position = "bottom"
    # cfg.n_threads = 2
    # cfg.paragraph_number = 1
    #
    # cfg.voice_volume = 1.0
    #
    # generate_video(video_path=video_file,
    #                audio_path=audio_file,
    #                subtitle_path=subtitle_file,
    #                output_file=output_file,
    #                params=cfg
    #                )
