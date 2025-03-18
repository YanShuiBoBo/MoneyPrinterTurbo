import warnings
from enum import Enum
from typing import Any, List, Optional, Union

import pydantic
from pydantic import BaseModel

# 忽略 Pydantic 的特定警告
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Field name.*shadows an attribute in parent.*",
)


class VideoConcatMode(str, Enum):
    random = "random"
    sequential = "sequential"


class VideoTransitionMode(str, Enum):
    none = None
    shuffle = "Shuffle"
    fade_in = "FadeIn"
    fade_out = "FadeOut"
    slide_in = "SlideIn"
    slide_out = "SlideOut"


class VideoAspect(str, Enum):
    landscape = "16:9"
    portrait = "9:16"
    square = "1:1"

    def to_resolution(self):
        if self == VideoAspect.landscape.value:
            return 1920, 1080
        elif self == VideoAspect.portrait.value:
            return 1080, 1920
        elif self == VideoAspect.square.value:
            return 1080, 1080
        return 1080, 1920


class _Config:
    arbitrary_types_allowed = True


@pydantic.dataclasses.dataclass(config=_Config)
class MaterialInfo:
    provider: str = "pexels"
    url: str = ""
    duration: int = 0


class VideoParams(BaseModel):
    """
    视频生成核心参数配置模型
    完整配置示例：
    {
      "video_subject": "夏日旅行日记",  # 必填，视频核心主题描述
      "video_aspect": "portrait",       # 竖屏9:16（抖音/快手）或 landscape 横屏16:9（YouTube/西瓜）
      "voice_name": "女生-晓晓",        # 支持多个预置语音声线
      "bgm_type": "random",            # 随机背景音乐或指定风格
      "font_name": "STHeitiMedium.ttc",# 中文字体文件名称
      "text_color": "#FFFFFF",         # 字幕文字颜色
      "font_size": 60,                 # 字幕字号（建议范围40-80）
      "stroke_color": "#000000",       # 文字描边颜色
      "stroke_width": 1.5              # 描边粗细（建议0.5-2.0）
    }
    """

    # 核心内容配置
    video_subject: str                  # 视频主题（必填，用于生成脚本和素材搜索）
    video_script: str = ""              # 视频脚本内容（留空时自动生成）
    video_terms: Optional[str | list] = None  # 视频关键词（如：["旅行", "海滩", "夏日"]）

    # 视频技术参数
    video_aspect: Optional[VideoAspect] = VideoAspect.portrait.value  # 画面比例
    video_concat_mode: Optional[VideoConcatMode] = VideoConcatMode.random.value  # 拼接模式：随机/顺序
    video_transition_mode: Optional[VideoTransitionMode] = None  # 转场效果（无/淡入淡出/滑动/随机）
    video_clip_duration: Optional[int] = 5   # 单素材最大时长（秒，建议3-15秒）
    video_count: Optional[int] = 1          # 生成视频数量（批量生成时使用）

    # 素材配置
    video_source: Optional[str] = "pexels"  # 素材源（pexels/unsplash/local）
    video_materials: Optional[List[MaterialInfo]] = None  # 自定义素材列表（优先级高于自动搜索）

    # 多语言配置
    video_language: Optional[str] = ""  # 视频语言（auto自动检测/zh-CN/en等）

    # 语音合成配置
    voice_name: Optional[str] = ""      # 发音人（如：女生-晓晓/男生-云扬）
    voice_volume: Optional[float] = 1.0 # 音量大小（0.0静音 ~ 2.0两倍音量）
    voice_rate: Optional[float] = 1.0   # 语速（0.5慢速 ~ 2.0快速）

    # 背景音乐配置
    bgm_type: Optional[str] = "random"  # 音乐类型（pop/rock/acoustic/random）
    bgm_file: Optional[str] = ""        # 自定义背景音乐文件路径（优先使用）
    bgm_volume: Optional[float] = 0.2   # 背景音乐音量（0.0静音 ~ 1.0原声）

    # 字幕渲染配置
    subtitle_enabled: Optional[bool] = True     # 是否启用字幕
    subtitle_position: Optional[str] = "bottom" # 字幕位置（top/bottom/center）
    custom_position: float = 70.0        # 自定义位置（百分比，如底部向上70%位置）
    font_name: Optional[str] = "STHeitiMedium.ttc"  # 字体文件名称（需存在于字体目录）
    text_fore_color: Optional[str] = "#FFFFFF"  # 文字颜色（HEX格式）
    text_background_color: Union[bool, str] = True  # 文字背景（True=半透明黑/False=无/#RRGGBDAA格式）

    # 文字样式高级设置
    font_size: int = 60                 # 基础字号（根据视频分辨率自动缩放）
    stroke_color: Optional[str] = "#000000"  # 文字描边颜色
    stroke_width: float = 1.5           # 描边宽度（像素）

    # 系统参数
    n_threads: Optional[int] = 2        # 渲染线程数（建议不超过CPU核心数）
    paragraph_number: Optional[int] = 1  # 脚本段落数（用于控制内容结构复杂度）


class SubtitleRequest(BaseModel):
    video_script: str
    video_language: Optional[str] = ""
    voice_name: Optional[str] = "zh-CN-XiaoxiaoNeural-Female"
    voice_volume: Optional[float] = 1.0
    voice_rate: Optional[float] = 1.2
    bgm_type: Optional[str] = "random"
    bgm_file: Optional[str] = ""
    bgm_volume: Optional[float] = 0.2
    subtitle_position: Optional[str] = "bottom"
    font_name: Optional[str] = "STHeitiMedium.ttc"
    text_fore_color: Optional[str] = "#FFFFFF"
    text_background_color: Union[bool, str] = True
    font_size: int = 60
    stroke_color: Optional[str] = "#000000"
    stroke_width: float = 1.5
    video_source: Optional[str] = "local"
    subtitle_enabled: Optional[str] = "true"


class AudioRequest(BaseModel):
    video_script: str
    video_language: Optional[str] = ""
    voice_name: Optional[str] = "zh-CN-XiaoxiaoNeural-Female"
    voice_volume: Optional[float] = 1.0
    voice_rate: Optional[float] = 1.2
    bgm_type: Optional[str] = "random"
    bgm_file: Optional[str] = ""
    bgm_volume: Optional[float] = 0.2
    video_source: Optional[str] = "local"


class VideoScriptParams:
    """
    {
      "video_subject": "春天的花海",
      "video_language": "",
      "paragraph_number": 1
    }
    """

    video_subject: Optional[str] = "春天的花海"
    video_language: Optional[str] = ""
    paragraph_number: Optional[int] = 1


class VideoTermsParams:
    """
    {
      "video_subject": "",
      "video_script": "",
      "amount": 5
    }
    """

    video_subject: Optional[str] = "春天的花海"
    video_script: Optional[str] = (
        "春天的花海，如诗如画般展现在眼前。万物复苏的季节里，大地披上了一袭绚丽多彩的盛装。金黄的迎春、粉嫩的樱花、洁白的梨花、艳丽的郁金香……"
    )
    amount: Optional[int] = 5


class BaseResponse(BaseModel):
    status: int = 200
    message: Optional[str] = "success"
    data: Any = None


class TaskVideoRequest(VideoParams, BaseModel):
    pass


class TaskQueryRequest(BaseModel):
    pass


class VideoScriptRequest(VideoScriptParams, BaseModel):
    pass


class VideoTermsRequest(VideoTermsParams, BaseModel):
    pass


######################################################################################################
######################################################################################################
######################################################################################################
######################################################################################################
class TaskResponse(BaseResponse):
    class TaskResponseData(BaseModel):
        task_id: str

    data: TaskResponseData

    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {"task_id": "6c85c8cc-a77a-42b9-bc30-947815aa0558"},
            },
        }


class TaskQueryResponse(BaseResponse):
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {
                    "state": 1,
                    "progress": 100,
                    "videos": [
                        "http://127.0.0.1:8080/tasks/6c85c8cc-a77a-42b9-bc30-947815aa0558/final-1.mp4"
                    ],
                    "combined_videos": [
                        "http://127.0.0.1:8080/tasks/6c85c8cc-a77a-42b9-bc30-947815aa0558/combined-1.mp4"
                    ],
                },
            },
        }


class TaskDeletionResponse(BaseResponse):
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {
                    "state": 1,
                    "progress": 100,
                    "videos": [
                        "http://127.0.0.1:8080/tasks/6c85c8cc-a77a-42b9-bc30-947815aa0558/final-1.mp4"
                    ],
                    "combined_videos": [
                        "http://127.0.0.1:8080/tasks/6c85c8cc-a77a-42b9-bc30-947815aa0558/combined-1.mp4"
                    ],
                },
            },
        }


class VideoScriptResponse(BaseResponse):
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {
                    "video_script": "春天的花海，是大自然的一幅美丽画卷。在这个季节里，大地复苏，万物生长，花朵争相绽放，形成了一片五彩斑斓的花海..."
                },
            },
        }


class VideoTermsResponse(BaseResponse):
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {"video_terms": ["sky", "tree"]},
            },
        }


class BgmRetrieveResponse(BaseResponse):
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {
                    "files": [
                        {
                            "name": "output013.mp3",
                            "size": 1891269,
                            "file": "/MoneyPrinterTurbo/resource/songs/output013.mp3",
                        }
                    ]
                },
            },
        }


class BgmUploadResponse(BaseResponse):
    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
                "data": {"file": "/MoneyPrinterTurbo/resource/songs/example.mp3"},
            },
        }
