#!python3
# -*- coding: utf-8 -*-
# Author: yinkaisheng@foxmail.com
import os
import sys
import time
import json
import ctypes
import functools
import threading
import logging as log
import ctypes.wintypes
from enum import Enum, IntEnum
from typing import (Any, Callable, Dict, List, Iterable, Tuple)

DefaultConnectionId = 0
ExePath = os.path.abspath(sys.argv[0])
ExeDir, ExeNameWithExt = os.path.split(ExePath)
os.chdir(ExeDir)
ExeName = ExeNameWithExt.split('.')[0]
LogDir = os.path.join(ExeDir, 'agsdklog')
if os.path.exists('Lib') and not os.path.exists('agorasdk'):
    SdkDir = os.path.join('Lib', 'agorasdk')
else:
    SdkDir = 'agorasdk'
SdkDirFull = os.path.join(ExeDir, SdkDir)  # d:\Codes\Python\RteDemo\agorasdk
# the followings must be referenced by full name, such as agorasdk.agorasdk.SdkBinDir
SdkBinDir = ''  # binx86_3.6.200
SdkBinDirFull = ''  # d:\Codes\Python\RteDemo\agorasdk\binx86_3.6.200
SdkVerson = ''  # 3.6.200, arsenal

if not os.path.exists(LogDir):
    os.makedirs(LogDir)
log.Formatter.default_msec_format = '%s.%03d'
log.basicConfig(filename=os.path.join(LogDir, 'AgoraSdk_py.log'), level=log.INFO,
                format='%(asctime)s %(levelname)s %(filename)s L%(lineno)d T%(thread)d %(funcName)s: %(message)s')


class LogFormatter(log.Formatter):
    default_time_format = '%H:%M:%S'

    def __init__(self, fmt=None, datefmt=None, style='%', validate=True):
        super(LogFormatter, self).__init__(fmt, datefmt, style, validate)


class GuiStream():
    def __init__(self):
        self.logHandler = None

    def write(self, output: str) -> None:
        if self.logHandler:
            self.logHandler(output)

    def setLogHandler(self, handler) -> None:
        self.logHandler = handler


GuiStreamObj = GuiStream()
sh = log.StreamHandler(GuiStreamObj)
sh.setFormatter(LogFormatter('%(asctime)s %(filename)s L%(lineno)d T%(thread)d %(funcName)s: %(message)s'))
log.getLogger().addHandler(sh)


if sys.stdout:
    # class MyHandler(log.Handler):
        # def emit(self, record):
            #print('custom handler called with\n', record)

    sh = log.StreamHandler(sys.stdout)
    sh.setFormatter(LogFormatter('%(asctime)s %(filename)s L%(lineno)d T%(thread)d %(funcName)s: %(message)s'))
    log.getLogger().addHandler(sh)


def isPy38OrHigher():
    return (sys.version_info[0] == 3 and sys.version_info[1] >= 8) or sys.version_info[0] > 3


def supportTrapzezoidCorrection() -> bool:
    return SdkVerson.startswith('3.6.200.10') or SdkVerson.startswith('3.7.204.dev')


#class StopWatch():
    #def __init__(self):
        #self.start = time.monotonic()

    #def elapsed(self) -> float:
        #return time.monotonic() - self.start()

    #def reset(self) -> None:
        #self.start = time.monotonic()

    #def __str__(self) -> str:
        #return f'{self.__class__.__name__}(start={self.start}, elapsed={self.elapsed()})'

    #__repr__ = __str__


LastAPICall = ''


def APITime(func):
    @functools.wraps(func)
    def API(*args, **kwargs):
        global LastAPICall
        argsstr = ', '.join(f"'{arg}'" if isinstance(arg, str) else str(arg) for arg in args if not isinstance(arg, RtcEngine))
        keystr = ', '.join('{}={}'.format(k, f"'{v}'" if isinstance(v, str) else v) for k, v in kwargs.items())
        if keystr:
            if argsstr:
                argsstr += ', ' + keystr
            else:
                argsstr = keystr
        LastAPICall = f'{func.__name__}({argsstr})'
        log.info(LastAPICall)
        start = time.monotonic()
        ret = func(*args, **kwargs)
        costTime = time.monotonic() - start
        logStr = f'{func.__name__} returns {ret}, costTime={costTime:.3} s'
        log.info(logStr)
        return ret
    return API


class MyIntEnum(IntEnum):
    __str__ = IntEnum.__repr__


class ChannelProfile(MyIntEnum):
    Communication = 0
    LiveBroadcasting = 1
    Game = 2
    CloudGaming = 3
    Communication1V1 = 4
    LiveBroadcasting2 = 5


class ClientRole(MyIntEnum):
    Broadcaster = 1
    Audience = 2


class LogLevel(MyIntEnum):
    Null = 0x0000
    Info = 0x0001
    Warn = 0x0002
    Error = 0x0004
    Fatal = 0x0008


class AudioScenario(MyIntEnum):
    Default = 0
    GameStreaming = 3
    ChatRoom = 5
    HighDefinition = 6
    Chorus = 7
    Num = 8


class AreaCode(MyIntEnum):
    CN = 0x00000001
    NA = 0x00000002
    EU = 0x00000004
    AS = 0x00000008
    JP = 0x00000010
    IN = 0x00000020
    GLOB = 0xFFFFFFFF


class AreaCodeEx(MyIntEnum):
    OC = 0x00000040
    SA = 0x00000080
    AF = 0x00000100
    OVS = 0xFFFFFFFE


class RenderMode(MyIntEnum):
    Hidden = 1
    Fit = 2
    Adaptive = 3  # same as Full in old sdk


class VideoMirrorMode(MyIntEnum):
    Auto = 0
    Enabled = 1
    Disabled = 2


class MediaSourceType(MyIntEnum):
    AudioPlayoutSource = 0,
    AudioRecordingSource = 1,
    PrimaryCameraSource = 2,
    SecondaryCameraSource = 3,
    PrimaryScreenSource = 4,
    SecondaryScreenSource = 5,
    CustomVideoSource = 6,
    MediaPlayerSource = 7,
    RtcImagePngSource = 8,
    RtcImageJpegSource = 9,
    RtcImageGifSource = 10,
    RemoteVideoSource = 11,
    TranscodedVideoSource = 12,
    UnknownMediaSource = 100,


class VideoSourceType(MyIntEnum):
    CameraPrimary = 0
    CameraSecondary = 1
    Screen = 2
    ScreenSecondary = 3
    Custom = 4
    MediaPlayer = 5
    RtcImagePng = 6
    RtcImageJpeg = 7
    RtcImageGif = 8
    Remote = 9
    Transcoded = 10
    Unknown = 100


class VideoOrientation(MyIntEnum):
    VO_0 = 0
    VO_90 = 90
    VO_180 = 180
    VO_270 = 270


class VideoCodec(MyIntEnum):
    VP8 = 1
    H264 = 2
    H265 = 3
    VP9 = 5
    Generic = 6
    GenericH264 = 7
    GenericJpeg = 20


class VideoPixelFormat(MyIntEnum):
    I420 = 1
    BGRA = 2
    NV21 = 3
    RGBA = 4,


class DegradationPreference(MyIntEnum):
    MaintainQuality = 0
    MaintainFramerate = 1
    MaintainBalanced = 2
    MaintainResolution = 3


class OrientationMode(MyIntEnum):
    Adaptive = 0
    FixedLandscape = 1
    FixedPortrait = 2


class LighteningContrastLevel(MyIntEnum):
    Low = 0
    Normal = 1
    High = 2


class BrightnessCorrectionMode(MyIntEnum):
    AutoMode = 0
    ManualMode = 1


class VideoProfile(MyIntEnum):
    Landscape_120P_15FPS = 0
    Landscape_180P_15FPS = 10
    Landscape_240P_15FPS = 20
    Landscape_360P_15FPS = 30
    Landscape_480P_15FPS = 40
    Landscape_720P_15FPS = 50
    Landscape_720P_30FPS = 52
    Landscape_1080P_15FPS = 60
    Landscape_1080P_30FPS = 62
    Landscape_1440P_30FPS = 66
    Landscape_4K_30FPS = 70
    Portrait_120P_15FPS = 1000
    Portrait_180P_15FPS = 1010
    Portrait_240P_15FPS = 1020
    Portrait_360P_15FPS = 1030
    Portrait_480P_15FPS = 1040
    Portrait_720P_15FPS = 1050
    Portrait_720P_30FPS = 1052
    Portrait_1080P_15FPS = 1060
    Portrait_1080P_30FPS = 1062
    Portrait_1440P_30FPS = 1066
    Portrait_4K_30FPS = 1070
    Default = Landscape_360P_15FPS


class LogConfig():
    def __init__(self, logPath: str = 'AgoraSdk_log.log', logSizeInKB: int = 5120, logLevel: LogLevel = LogLevel.Info):
        self.logPath = logPath
        self.logSizeInKB = logSizeInKB
        self.logLevel = logLevel

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(logPath="{self.logPath}", logSizeInKB={self.logSizeInKB}, logLevel={self.logLevel})'

    __repr__ = __str__


class RtcEngineContext():
    def __init__(self, appId: str, logConfig: LogConfig = LogConfig(), channelProfile: ChannelProfile = ChannelProfile.LiveBroadcasting,
                 eventHandler: ctypes.c_void_p = ctypes.c_void_p(0), areaCode: AreaCode = AreaCode.GLOB,
                 audioScenario: AudioScenario = AudioScenario.HighDefinition, enableAudioDevice: bool = True):
        self.appId = appId
        self.areaCode = areaCode
        self.audioScenario = audioScenario
        self.channelProfile = channelProfile
        self.enableAudioDevice = enableAudioDevice
        self.eventHandler = eventHandler  # not used
        self.logConfig = logConfig

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(appId="{self.appId[:8]}...", channelProfile={self.channelProfile}, '   \
            f'audioScenario={self.audioScenario}, enableAudioDevice={self.enableAudioDevice})'

    __repr__ = __str__


class RtcConnection():
    def __init__(self, channelId: str = None, localUid: int = 0):
        self.channelId = channelId
        self.localUid = localUid

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(channelId="{self.channelId}", localUid={self.localUid})'

    __repr__ = __str__


class ChannelMediaOptions():
    def __init__(self, channelProfile: ChannelProfile = ChannelProfile.LiveBroadcasting,
                 clientRole: ClientRole = ClientRole.Broadcaster,
                 autoSubscribeAudio: bool = None,
                 autoSubscribeVideo: bool = None,
                 publishAudioTrack: bool = None,
                 publishCameraTrack: bool = None,
                 publishSecondaryCameraTrack: bool = None,
                 publishScreenTrack: bool = None,
                 publishSecondaryScreenTrack: bool = None,
                 publishCustomAudioTrack: bool = None,
                 publishCustomVideoTrack: bool = None):
        self.channelProfile = channelProfile
        self.clientRole = clientRole
        self.autoSubscribeAudio = autoSubscribeAudio
        self.autoSubscribeVideo = autoSubscribeVideo
        self.publishAudioTrack = publishAudioTrack
        self.publishCameraTrack = publishCameraTrack
        self.publishSecondaryCameraTrack = publishSecondaryCameraTrack
        self.publishScreenTrack = publishScreenTrack
        self.publishSecondaryScreenTrack = publishSecondaryScreenTrack
        self.publishCustomAudioTrack = publishCustomAudioTrack
        self.publishCustomVideoTrack = publishCustomVideoTrack

    def convertNone(self):
        for key in self.__dict__:
            if not key.startswith('__') and self.__dict__[key] is None:
                self.__dict__[key] = -1  # to c++ dll, -1 indicates c++ options is null

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(channelProfile={self.channelProfile}, clientRole={self.clientRole}, '    \
            f'autoSubscribeAudio={self.autoSubscribeAudio}, autoSubscribeVideo={self.autoSubscribeVideo}, ' \
            f'publishAudioTrack={self.publishAudioTrack}, '   \
            f'publishCameraTrack={self.publishCameraTrack}, publishSecondaryCameraTrack={self.publishSecondaryCameraTrack}, '   \
            f'publishScreenTrack={self.publishScreenTrack}, publishSecondaryScreenTrack={self.publishSecondaryScreenTrack}, '   \
            f'publishCustomAudioTrack={self.publishCustomAudioTrack}, publishCustomVideoTrack={self.publishCustomVideoTrack})'

    __repr__ = __str__


class CameraCapturerConfiguration():
    def __init__(self, deviceId: str = '', width: int = 640, height: int = 360, frameRate: int = 15):
        self.deviceId = deviceId
        self.width = width
        self.height = height
        self.frameRate = frameRate

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(deviceId="{self.deviceId}", width={self.width}, height={self.height}, frameRate={self.frameRate})'

    __repr__ = __str__


class VideoEncoderConfiguration():
    def __init__(self, width: int = 640, height: int = 360, frameRate: int = 15, bitrate: int = 0, codecType: VideoCodec = VideoCodec.H264,
                 degradationPreference: DegradationPreference = DegradationPreference.MaintainQuality, minBitrate: int = -1,
                 mirrorMode: VideoMirrorMode = VideoMirrorMode.Disabled, orientationMode: OrientationMode = OrientationMode.Adaptive):
        self.width = width
        self.height = height
        self.frameRate = frameRate
        self.bitrate = bitrate
        self.codecType = codecType
        self.degradationPreference = degradationPreference
        self.minBitrate = minBitrate
        self.mirrorMode = mirrorMode
        self.orientationMode = orientationMode

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(width={self.width}, height={self.height}, frameRate={self.frameRate}, '  \
               f'bitrate={self.bitrate}, codecType={self.codecType}, degradationPreference={self.degradationPreference}, '  \
               f'minBitrate={self.minBitrate}, mirrorMode={self.mirrorMode}, orientationMode={self.orientationMode})'

    __repr__ = __str__


class ViewSetupMode():
    Replace = 0
    Add = 1
    Remove = 2


class VideoCanvas():
    def __init__(self, uid: int, view: int, mirrorMode: VideoMirrorMode = VideoMirrorMode.Auto, renderMode: RenderMode = RenderMode.Fit,
                 sourceType: VideoSourceType = VideoSourceType.CameraPrimary, isScreenView: bool = False, setupMode: ViewSetupMode = -1):
        self.isScreenView = isScreenView
        self.mirrorMode = mirrorMode
        self.renderMode = renderMode
        self.sourceType = sourceType
        self.uid = uid
        self.view = view
        self.setupMode = setupMode

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(uid={self.uid}, view=0x{self.view:X}, mirrorMode={self.mirrorMode}, '    \
               f'renderMode={self.renderMode}, sourceType={self.sourceType}, setupMode={self.setupMode})'

    __repr__ = __str__


class BeautyOptions():
    def __init__(self, lighteningContrastLevel: LighteningContrastLevel = LighteningContrastLevel.Normal, lighteningLevel: float = 0,
                 rednessLevel: float = 0, sharpnessLevel: float = 0, smoothnessLevel: float = 0):
        self.lighteningContrastLevel = lighteningContrastLevel
        self.lighteningLevel = lighteningLevel
        self.rednessLevel = rednessLevel
        self.sharpnessLevel = sharpnessLevel
        self.smoothnessLevel = smoothnessLevel

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(lighteningContrastLevel={self.lighteningContrastLevel}, '    \
               f'lighteningLevel={self.lighteningLevel}, rednessLevel={self.rednessLevel}, '    \
               f'sharpnessLevel={self.sharpnessLevel}, smoothnessLevel={self.smoothnessLevel})'

    __repr__ = __str__


class Rectangle():
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(x={self.x}, y={self.y}, width={self.width}, height={self.height})'

    __repr__ = __str__


class ScreenCaptureParameters():
    def __init__(self, width: int, height: int, fps: int = 15, bitrate: int = 0, excludeWindowList: List[int] = None):
        self.width = width
        self.height = height
        self.fps = fps
        self.bitrate = bitrate
        self.excludeWindowList = excludeWindowList

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(width={self.width}, height={self.height},fps={self.fps}, bitrate={self.bitrate}'     \
               f', excludeWindowList={self.excludeWindowList})'

    __repr__ = __str__


class ScreenCaptureConfiguration():
    def __init__(self, isCaptureWindow: bool = False, windowId: int = 0, screenRect: Rectangle = None, regionRect: Rectangle = None, params: ScreenCaptureParameters = None):
        self.isCaptureWindow = isCaptureWindow
        self.windowId = windowId
        self.screenRect = screenRect
        self.regionRect = regionRect
        self.params = params

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(width={self.width}, height={self.height},fps={self.fps}, bitrate={self.bitrate}'     \
               f', excludeWindowList={self.excludeWindowList})'

    __repr__ = __str__


class BackgroundSourceType(MyIntEnum):
    Color = 1
    Image = 2
    Blur = 3


class BackgroundBlurDegree(MyIntEnum):
    Low = 1
    Medium = 2
    High = 3


class SegModelType(MyIntEnum):
    AgoraAIOne = 0
    AgoraGreen = 2


class VirtualBackgroundSource():
    def __init__(self, backgroundSourceType: BackgroundSourceType = BackgroundSourceType.Color,
                 color: int = 0xFFFFFF, source: str = None, blurDegree: BackgroundBlurDegree = BackgroundBlurDegree.High,
                 modelType: SegModelType = SegModelType.AgoraAIOne, preferVelocity: int = 1, greenCapacity: float = 0.5):
        self.backgroundSourceType = backgroundSourceType
        self.color = color
        self.source = source
        self.blurDegree = blurDegree
        self.modelType = modelType
        self.preferVelocity = preferVelocity
        self.greenCapacity = greenCapacity

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(backgroundSourceType={self.backgroundSourceType}, color={self.color}, '   \
            f'source={self.source}, blurDegree={self.blurDegree}, modelType={self.modelType}, '  \
            f'preferVelocity={self.preferVelocity}, greenCapacity={self.greenCapacity})'

    __repr__ = __str__


class SegmentationProperty():
    def __init__(self, modelType: SegModelType = SegModelType.AgoraAIOne, preferVelocity: int = 1, greenCapacity: float = 0.5):
        self.modelType = modelType
        self.preferVelocity = preferVelocity
        self.greenCapacity = greenCapacity

    def __str__(self) -> str:
        return f'{self.__class__.__name__}(modelType={self.modelType}, preferVelocity={self.preferVelocity}, greenCapacity={self.greenCapacity})'

    __repr__ = __str__


class _DllClient:
    _instance = None

    @classmethod
    def instance(cls) -> '_DllClient':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        os.environ["PATH"] = SdkBinDirFull + os.pathsep + os.environ["PATH"]
        if isPy38OrHigher() and os.path.exists(SdkBinDirFull):
            os.add_dll_directory(SdkBinDirFull)
        load = False
        try:
            self.dll = ctypes.cdll.AgoraPython
            load = True
        except Exception as ex:
            log.error(ex)
        if load:
            self.dll.createRtcEngine.restype = ctypes.c_void_p
            self.dll.getVersion.restype = ctypes.c_char_p
            self.dll.getSdkErrorDescription.restype = ctypes.c_char_p
            self.dll.createRtcEngineEventHandler.restype = ctypes.c_void_p
            if sys.platform == 'win32':
                self.dll.initializeGdiPlus()
        else:
            self.dll = None
            log.error(f'Can not load dll. path={SdkBinDirFull}')

    def __del__(self):
        if self.dll:
            pass


def chooseSdkBinDir(sdkBinDir: str):
    '''sdkBinDir: str, such as 'binx86_3.6.200.100' '''
    global SdkBinDir, SdkBinDirFull, SdkVerson
    SdkBinDir = sdkBinDir
    SdkVerson = SdkBinDir.split('_', 2)[-1]
    if ExeDir.endswith(SdkDir):  # for run agorasdk.py directlly
        SdkBinDirFull = os.path.join(ExeDir, SdkBinDir)
    else:
        SdkBinDirFull = os.path.join(ExeDir, SdkDir, SdkBinDir)
    print(f'SdkBinDir={SdkBinDir}, SdkVerson={SdkVerson}, SdkBinDirFull={SdkBinDirFull}')


RtcEngineEventCFuncCallback = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int64, ctypes.c_char_p, ctypes.c_char_p)


class RtcEngine:
    def __init__(self):
        self.dll = _DllClient.instance().dll
        self.callback = None
        self.printCallback = True
        self.eventHandlerUserData = {}  # Dict[int, str]
        self.rtcEngine = self.dll.createRtcEngine()
        self.pRtcEngine = ctypes.c_void_p(self.rtcEngine)
        self.rtcEngineEventHandler = self.dll.createRtcEngineEventHandler()
        self.pRtcEngienEventHandler = ctypes.c_void_p(self.rtcEngineEventHandler)
        self.rtcEngineEventHandlerEx = self.dll.createRtcEngineEventHandler()
        self.pRtcEngienEventHandlerEx = ctypes.c_void_p(self.rtcEngineEventHandlerEx)
        version, build = self.getVersion()
        lineLen = 60
        log.info('\n\n{0}\n|{1:^{middleLen}}|\n{0}\n'.format(
            '-' * lineLen, f'Agora SDK Version: {version}, Build: {build}', middleLen=lineLen - 2))

    def __del__(self):
        self.release(sync=True)

    def RtcEngineEventCFuncCallback(self, eventHandler: int, callbackTimeSinceEpoch: int, funcName: bytes, jsonStr: bytes) -> None:
        funcName = funcName.decode('utf-8')
        jsonStr = jsonStr.decode('utf-8')
        if self.printCallback:
            log.info(f'0x{eventHandler:X} {self.eventHandlerUserData.get(eventHandler, "Channel")} epoch: {callbackTimeSinceEpoch} {funcName} {jsonStr}')
        # if jsonStr:
            # jsonStr = json.loads(jsonStr)
        if self.callback:
            self.callback(self.eventHandlerUserData.get(eventHandler, "Channel"), callbackTimeSinceEpoch, funcName, jsonStr)

    @APITime
    def release(self, sync: bool = True) -> None:
        if self.rtcEngine:
            log.info(f'will release RtcEngine=0x{self.rtcEngine:X}')
            self.dll.release(self.pRtcEngine, int(sync))
            self.rtcEngine = 0
            self.pRtcEngine = None
        if self.rtcEngineEventHandler:
            self.dll.releaseRtcEngineEventHandler(self.pRtcEngienEventHandler)
            if self.rtcEngineEventHandler in self.eventHandlerUserData:
                del self.eventHandlerUserData[self.rtcEngineEventHandler]
            self.rtcEngineEventHandler = 0
            self.pRtcEngienEventHandler = None
        if self.rtcEngineEventHandlerEx:
            self.dll.releaseRtcEngineEventHandler(self.pRtcEngienEventHandlerEx)
            if self.rtcEngineEventHandlerEx in self.eventHandlerUserData:
                del self.eventHandlerUserData[self.rtcEngineEventHandlerEx]
            self.rtcEngineEventHandlerEx = 0
            self.pRtcEngienEventHandlerEx = None

    def getVersion(self) -> Tuple[str, int]:
        build = ctypes.c_int(0)
        version = self.dll.getVersion(self.pRtcEngine, ctypes.byref(build))
        return version.decode('utf-8'), build.value

    def getErrorDescription(self, error: int) -> str:
        errorDesc = self.dll.getSdkErrorDescription(error)
        return errorDesc.decode('utf-8')

    @APITime
    def initalize(self, context: RtcEngineContext, callback: Callable[[str, int, str, str], None], userData: str = 'Channel') -> int:
        self.callback = callback
        self.eventHandlerUserData[self.rtcEngineEventHandler] = userData
        self.eventCFuncCallback = RtcEngineEventCFuncCallback(self.RtcEngineEventCFuncCallback)
        self.dll.setRtcEngineEventCallback(self.pRtcEngienEventHandler, self.eventCFuncCallback)

        self.eventHandlerUserData[self.rtcEngineEventHandlerEx] = f'{userData}Ex'
        self.dll.setRtcEngineEventCallback(self.pRtcEngienEventHandlerEx, self.eventCFuncCallback)

        appId = context.appId.encode('utf-8')
        logPath = context.logConfig.logPath.encode('utf-8')
        ret = self.dll.initialize(self.pRtcEngine, ctypes.c_char_p(appId), context.areaCode, context.audioScenario,
                                  context.channelProfile, int(context.enableAudioDevice), self.pRtcEngienEventHandler,
                                  ctypes.c_char_p(logPath), context.logConfig.logSizeInKB, context.logConfig.logLevel)
        return ret

    @APITime
    def setChannelProfile(self, profile: ChannelProfile) -> int:
        ret = self.dll.setChannelProfile(self.pRtcEngine, profile)
        return ret

    @APITime
    def setClientRole(self, role: ClientRole) -> int:
        ret = self.dll.setClientRole(self.pRtcEngine, role)
        return ret

    @APITime
    def enableAudio(self) -> int:
        ret = self.dll.enableAudio(self.pRtcEngine)
        return ret

    @APITime
    def disableAudio(self) -> int:
        ret = self.dll.disableAudio(self.pRtcEngine)
        return ret

    @APITime
    def enableVideo(self) -> int:
        ret = self.dll.enableVideo(self.pRtcEngine)
        return ret

    @APITime
    def disableVideo(self) -> int:
        ret = self.dll.disableVideo(self.pRtcEngine)
        return ret

    @APITime
    def enableLocalAudio(self, enabled: bool) -> int:
        ret = self.dll.enableLocalAudio(self.pRtcEngine, int(enabled))
        return ret

    @APITime
    def enableLocalVideo(self, enabled: bool) -> int:
        ret = self.dll.enableLocalVideo(self.pRtcEngine, int(enabled))
        return ret

    @APITime
    def registerVideoFrameObserver(self) -> int:
        ret = self.dll.registerVideoFrameObserver(self.pRtcEngine)
        return ret

    def saveCaptureVideoFrame(self, save: bool, count: int) -> None:
        self.dll.saveCaptureVideoFrame(int(save), count)

    def resetCaptureVideoFrame(self) -> None:
        self.dll.resetCaptureVideoFrame()

    def saveSecondaryCaptureVideoFrame(self, save: bool, count: int) -> None:
        self.dll.saveSecondaryCaptureVideoFrame(int(save), count)

    def resetSecondaryCaptureVideoFrame(self) -> None:
        self.dll.resetSecondaryCaptureVideoFrame()

    def saveRenderVideoFrame(self, save: bool, count: int) -> None:
        self.dll.saveRenderVideoFrame(int(save), count)

    def resetRenderVideoFrame(self) -> None:
        self.dll.resetRenderVideoFrame()

    @APITime
    def setCameraCapturerConfiguration(self, cameraConfig: CameraCapturerConfiguration) -> int:
        if SdkVerson < '3.6.200':
            log.error(f'{SdkVerson} does not support this API')
            return -1
        deviceId = cameraConfig.deviceId.encode('utf-8')
        ret = self.dll.setCameraCapturerConfiguration(self.pRtcEngine, ctypes.c_char_p(deviceId),
                                                      cameraConfig.width, cameraConfig.height, cameraConfig.frameRate)
        return ret

    @APITime
    def setCameraDeviceOrientation(self, orientation: VideoOrientation, sourceType: VideoSourceType = VideoSourceType.CameraPrimary) -> int:
        ret = self.dll.setCameraDeviceOrientation(self.pRtcEngine, sourceType, orientation)
        return ret

    @APITime
    def startPrimaryCameraCapture(self, cameraConfig: CameraCapturerConfiguration) -> int:
        deviceId = cameraConfig.deviceId.encode('utf-8')
        ret = self.dll.startPrimaryCameraCapture(self.pRtcEngine, ctypes.c_char_p(deviceId),
                                                 cameraConfig.width, cameraConfig.height, cameraConfig.frameRate)
        return ret

    @APITime
    def stopPrimaryCameraCapture(self) -> int:
        ret = self.dll.stopPrimaryCameraCapture(self.pRtcEngine)
        return ret

    @APITime
    def startSecondaryCameraCapture(self, cameraConfig: CameraCapturerConfiguration) -> int:
        deviceId = cameraConfig.deviceId.encode('utf-8')
        ret = self.dll.startSecondaryCameraCapture(self.pRtcEngine, ctypes.c_char_p(deviceId),
                                                   cameraConfig.width, cameraConfig.height, cameraConfig.frameRate)
        return ret

    @APITime
    def stopSecondaryCameraCapture(self) -> int:
        ret = self.dll.stopSecondaryCameraCapture(self.pRtcEngine)
        return ret

    @APITime
    def setVideoEncoderConfiguration(self, videoConfig: VideoEncoderConfiguration, connectionId: int = DefaultConnectionId) -> int:
        ret = self.dll.setVideoEncoderConfiguration(self.pRtcEngine, connectionId, videoConfig.width, videoConfig.height,
                                                    videoConfig.frameRate, videoConfig.bitrate, videoConfig.codecType,
                                                    videoConfig.degradationPreference, videoConfig.minBitrate,
                                                    videoConfig.mirrorMode, videoConfig.orientationMode)
        return ret

    @APITime
    def setVideoEncoderConfigurationEx(self, videoConfig: VideoEncoderConfiguration, connection: RtcConnection = RtcConnection()) -> int:
        channelName = connection.channelId.encode('utf-8') if connection.channelId != None else 0
        ret = self.dll.setVideoEncoderConfigurationEx(self.pRtcEngine, ctypes.c_char_p(channelName), connection.localUid,
                                                      videoConfig.width, videoConfig.height, videoConfig.frameRate,
                                                      videoConfig.bitrate, videoConfig.codecType, videoConfig.degradationPreference,
                                                      videoConfig.minBitrate, videoConfig.mirrorMode, videoConfig.orientationMode)
        return ret

    @APITime
    def loadExtensionProvider(self, extensionLibPath: str) -> int:
        if SdkVerson < '3.6.200':
            log.error(f'{SdkVerson} does not support this API')
            return -1
        extensionLibPath = extensionLibPath.encode('utf-8')
        ret = self.dll.loadExtensionProvider(self.pRtcEngine, ctypes.c_char_p(extensionLibPath))
        return ret

    @APITime
    def enableExtension(self, providerName: str, extensionName: str, enabled: bool,
                        sourceType: MediaSourceType = MediaSourceType.PrimaryCameraSource) -> int:
        if SdkVerson < '3.6.200':
            log.error(f'{SdkVerson} does not support this API')
            return -1
        providerName = providerName.encode('utf-8')
        extensionName = extensionName.encode('utf-8')
        ret = self.dll.enableExtension(self.pRtcEngine, ctypes.c_char_p(providerName),
                                       ctypes.c_char_p(extensionName), int(enabled), sourceType)
        return ret

    @APITime
    def setExtensionProperty(self, providerName: str, extensionName: str, key: str, jsonValue: str,
                             sourceType: MediaSourceType = MediaSourceType.PrimaryCameraSource) -> int:
        providerName = providerName.encode('utf-8')
        extensionName = extensionName.encode('utf-8')
        key = key.encode('utf-8')
        jsonValue = jsonValue.encode('utf-8')
        ret = self.dll.setExtensionProperty(self.pRtcEngine, ctypes.c_char_p(providerName), ctypes.c_char_p(extensionName),
                                            ctypes.c_char_p(key), ctypes.c_char_p(jsonValue), sourceType)
        return ret

    @APITime
    def setBeautyEffectOptions(self, enabled: bool, beautyOptions: BeautyOptions = BeautyOptions(),
                               sourceType: MediaSourceType = MediaSourceType.PrimaryCameraSource) -> int:
        ret = self.dll.setBeautyEffectOptions(self.pRtcEngine, int(enabled), beautyOptions.lighteningContrastLevel,
                                              ctypes.c_float(beautyOptions.lighteningLevel), ctypes.c_float(beautyOptions.rednessLevel),
                                              ctypes.c_float(beautyOptions.sharpnessLevel), ctypes.c_float(beautyOptions.smoothnessLevel),
                                              sourceType)
        return ret

    @APITime
    def enableVirtualBackground(self, enabled: bool,
                                backgroundSource: VirtualBackgroundSource,
                                segProperty: SegmentationProperty,
                                sourceType: MediaSourceType = MediaSourceType.PrimaryCameraSource) -> int:
        source = backgroundSource.source.encode('utf-8') if backgroundSource.source else 0
        ret = self.dll.enableVirtualBackground(self.pRtcEngine, int(enabled),
                                               backgroundSource.backgroundSourceType, backgroundSource.color, ctypes.c_char_p(source),
                                               backgroundSource.blurDegree, backgroundSource.modelType,
                                               backgroundSource.preferVelocity, ctypes.c_float(backgroundSource.greenCapacity),
                                               segProperty.modelType, segProperty.preferVelocity, ctypes.c_float(segProperty.greenCapacity),
                                               sourceType)
        return ret

    @APITime
    def enableBrightnessCorrection(self, enabled: bool, mode: BrightnessCorrectionMode = BrightnessCorrectionMode.AutoMode,
                                   sourceType: VideoSourceType = VideoSourceType.CameraPrimary) -> int:
        log.info(f'enabled={enabled}, mode={mode}, sourceType={sourceType}')
        ret = self.dll.enableBrightnessCorrection(self.pRtcEngine, int(enabled), mode, sourceType)
        log.info(f'returns {ret}')
        return ret

    @APITime
    def applyBrightnessCorrectionToRemote(self, uid: int, enabled: bool, mode: BrightnessCorrectionMode = BrightnessCorrectionMode.AutoMode) -> int:
        log.info(f'uid={uid}, enabled={enabled}, mode={mode}')
        ret = self.dll.applyBrightnessCorrectionToRemote(self.pRtcEngine, uid, int(enabled), mode)
        log.info(f'returns {ret}')
        return ret

    @APITime
    def applyBrightnessCorrectionToRemoteEx(self, uid: int, enabled: bool, mode: BrightnessCorrectionMode = BrightnessCorrectionMode.AutoMode,
                                            connection: RtcConnection = RtcConnection()) -> int:
        channelName = connection.channelId.encode('utf-8') if connection.channelId != None else 0
        ret = self.dll.applyBrightnessCorrectionToRemoteEx(self.pRtcEngine, uid, int(enabled), mode,
                                                           ctypes.c_char_p(channelName), connection.localUid)
        return ret

    @APITime
    def enableLocalTrapezoidCorrection(self, enabled: bool, sourceType: VideoSourceType = VideoSourceType.CameraPrimary) -> int:
        ret = self.dll.enableLocalTrapezoidCorrection(self.pRtcEngine, int(enabled), sourceType)
        return ret

    @APITime
    def setLocalTrapezoidCorrectionOptions(self, options: Dict, sourceType: VideoSourceType = VideoSourceType.CameraPrimary) -> int:
        jsStr = json.dumps(options, indent=4, ensure_ascii=False, sort_keys=True)
        jsStr = jsStr.encode('utf-8')
        ret = self.dll.setLocalTrapezoidCorrectionOptions(self.pRtcEngine, ctypes.c_char_p(jsStr), sourceType)
        return ret

    @APITime
    def getLocalTrapezoidCorrectionOptions(self, sourceType: VideoSourceType = VideoSourceType.CameraPrimary) -> Tuple[Dict, int]:
        arrayType = ctypes.c_char * 1024
        charArray = arrayType()
        ret = self.dll.getLocalTrapezoidCorrectionOptions(self.pRtcEngine, charArray, len(charArray), sourceType)
        jsInfo = None
        if ret == 0:
            jsStr = charArray.value.decode('utf-8')
            if jsStr:
                jsInfo = json.loads(jsStr)
        return jsInfo, ret

    @APITime
    def enableRemoteTrapezoidCorrection(self, uid: int, enabled: bool) -> int:
        ret = self.dll.enableRemoteTrapezoidCorrection(self.pRtcEngine, uid, int(enabled))
        return ret

    @APITime
    def enableRemoteTrapezoidCorrectionEx(self, uid: int, enabled: bool, connection: RtcConnection = RtcConnection()) -> int:
        channelName = connection.channelId.encode('utf-8') if connection.channelId != None else 0
        ret = self.dll.enableRemoteTrapezoidCorrectionEx(self.pRtcEngine, uid, int(enabled),
                                                         ctypes.c_char_p(channelName), connection.localUid)
        return ret

    @APITime
    def setRemoteTrapezoidCorrectionOptions(self, uid: int, options: Dict) -> int:
        jsStr = json.dumps(options, indent=4, ensure_ascii=False, sort_keys=True)
        jsStr = jsStr.encode('utf-8')
        ret = self.dll.setRemoteTrapezoidCorrectionOptions(self.pRtcEngine, uid, ctypes.c_char_p(jsStr))
        return ret

    @APITime
    def setRemoteTrapezoidCorrectionOptionsEx(self, uid: int, options: Dict, connection: RtcConnection = RtcConnection()) -> int:
        channelName = connection.channelId.encode('utf-8') if connection.channelId != None else 0
        jsStr = json.dumps(options, indent=4, ensure_ascii=False, sort_keys=True)
        jsStr = jsStr.encode('utf-8')
        ret = self.dll.setRemoteTrapezoidCorrectionOptionsEx(self.pRtcEngine, uid, ctypes.c_char_p(jsStr),
                                                             ctypes.c_char_p(channelName), connection.localUid)
        return ret

    @APITime
    def getRemoteTrapezoidCorrectionOptions(self, uid: int) -> Tuple[Dict, int]:
        arrayType = ctypes.c_char * 1024
        charArray = arrayType()
        ret = self.dll.getRemoteTrapezoidCorrectionOptions(self.pRtcEngine, uid, charArray, len(charArray))
        jsInfo = None
        if ret == 0:
            jsStr = charArray.value.decode('utf-8')
            if jsStr:
                jsInfo = json.loads(jsStr)
        return jsInfo, ret

    @APITime
    def getRemoteTrapezoidCorrectionOptionsEx(self, uid: int, connection: RtcConnection = RtcConnection()) -> Tuple[Dict, int]:
        channelName = connection.channelId.encode('utf-8') if connection.channelId != None else 0
        arrayType = ctypes.c_char * 1024
        charArray = arrayType()
        ret = self.dll.getRemoteTrapezoidCorrectionOptionsEx(self.pRtcEngine, uid, charArray, len(charArray),
                                                             ctypes.c_char_p(channelName), connection.localUid)
        jsInfo = None
        if ret == 0:
            jsStr = charArray.value.decode('utf-8')
            if jsStr:
                jsInfo = json.loads(jsStr)
        return jsInfo, ret

    @APITime
    def applyTrapezoidCorrectionToRemote(self, uid: int, enabled: bool) -> int:
        ret = self.dll.applyTrapezoidCorrectionToRemote(self.pRtcEngine, uid, int(enabled))
        return ret

    @APITime
    def applyTrapezoidCorrectionToRemoteEx(self, uid: int, enabled: bool, connection: RtcConnection = RtcConnection()) -> int:
        channelName = connection.channelId.encode('utf-8') if connection.channelId != None else 0
        ret = self.dll.applyTrapezoidCorrectionToRemoteEx(self.pRtcEngine, uid, int(enabled),
                                                          ctypes.c_char_p(channelName), connection.localUid)
        return ret

    @APITime
    def applyVideoEncoderMirrorToRemote(self, uid: int, mirrorMode: VideoMirrorMode) -> int:
        ret = self.dll.applyVideoEncoderMirrorToRemote(self.pRtcEngine, uid, mirrorMode)
        return ret

    @APITime
    def applyVideoEncoderMirrorToRemoteEx(self, uid: int, mirrorMode: VideoMirrorMode, connection: RtcConnection = RtcConnection()) -> int:
        channelName = connection.channelId.encode('utf-8') if connection.channelId != None else 0
        ret = self.dll.applyVideoEncoderMirrorToRemoteEx(self.pRtcEngine, uid, mirrorMode,
                                                         ctypes.c_char_p(channelName), connection.localUid)
        return ret

    @APITime
    def applyVideoOrientationToRemote(self, uid: int, orientation: VideoOrientation) -> int:
        ret = self.dll.applyVideoOrientationToRemote(self.pRtcEngine, uid, orientation)
        return ret

    @APITime
    def applyVideoOrientationToRemoteEx(self, uid: int, orientation: VideoOrientation, connection: RtcConnection = RtcConnection()) -> int:
        channelName = connection.channelId.encode('utf-8') if connection.channelId != None else 0
        ret = self.dll.applyVideoOrientationToRemoteEx(self.pRtcEngine, uid, orientation,
                                                       ctypes.c_char_p(channelName), connection.localUid)
        return ret

    @APITime
    def setLocalVideoMirrorMode(self, mirrorMode: VideoMirrorMode) -> int:
        ret = self.dll.setLocalVideoMirrorMode(self.pRtcEngine, mirrorMode)
        return ret

    @APITime
    def setLocalRenderMode(self, renderMode: RenderMode, mirrorMode: VideoMirrorMode, sourceType: VideoSourceType = VideoSourceType.CameraPrimary) -> int:
        if supportTrapzezoidCorrection():
            ret = self.dll.setLocalRenderMode(self.pRtcEngine, renderMode, mirrorMode, sourceType)
        else:
            ret = self.dll.setLocalRenderMode(self.pRtcEngine, renderMode, mirrorMode)
        return ret

    @APITime
    def setRemoteRenderMode(self, uid: int, renderMode: RenderMode, mirrorMode: VideoMirrorMode) -> int:
        ret = self.dll.setRemoteRenderMode(self.pRtcEngine, uid, renderMode, mirrorMode)
        return ret

    @APITime
    def setupLocalVideo(self, videoCanvas: VideoCanvas) -> int:
        ret = self.dll.setupLocalVideo(self.pRtcEngine, videoCanvas.uid, ctypes.c_void_p(videoCanvas.view), videoCanvas.mirrorMode,
                                       videoCanvas.renderMode, videoCanvas.sourceType, int(videoCanvas.isScreenView), videoCanvas.setupMode)
        return ret

    @APITime
    def setupRemoteVideo(self, videoCanvas: VideoCanvas, connectionId: int = DefaultConnectionId) -> int:
        ret = self.dll.setupRemoteVideo(self.pRtcEngine, videoCanvas.uid, ctypes.c_void_p(videoCanvas.view), videoCanvas.mirrorMode,
                                        videoCanvas.renderMode, videoCanvas.sourceType, int(videoCanvas.isScreenView), connectionId)
        return ret

    @APITime
    def setupRemoteVideoEx(self, videoCanvas: VideoCanvas, connection: RtcConnection) -> int:
        if SdkVerson < '3.6.200':
            log.error(f'{SdkVerson} does not support this API')
            return -1
        channelName = connection.channelId.encode('utf-8')
        ret = self.dll.setupRemoteVideoEx(self.pRtcEngine, videoCanvas.uid, ctypes.c_void_p(videoCanvas.view), videoCanvas.mirrorMode,
                                          videoCanvas.renderMode, ctypes.c_char_p(channelName), connection.localUid)
        return ret

    @APITime
    def startPreview(self, sourceType: VideoSourceType = None) -> int:
        if sourceType is not None and SdkVerson >= '3.6.200':
            ret = self.dll.startPreview2(self.pRtcEngine, sourceType)
        else:
            ret = self.dll.startPreview(self.pRtcEngine)
        return ret

    @APITime
    def stopPreview(self, sourceType: VideoSourceType = None) -> int:
        if sourceType is not None and SdkVerson >= '3.6.200':
            ret = self.dll.stopPreview2(self.pRtcEngine, sourceType)
        else:
            ret = self.dll.stopPreview(self.pRtcEngine)
        return ret

    @APITime
    def takeSnapshot(self, channel: str, uid: int, filePath: str, rect: Tuple[float, float, float, float] = None) -> int:
        if SdkVerson.startswith('3.6.200.10'):
            channel = channel.encode('utf-8')
            filePath = filePath.encode('utf-8')
            ret = self.dll.takeSnapshot(self.pRtcEngine, ctypes.c_char_p(channel), uid, ctypes.c_char_p(filePath),
                                        ctypes.c_float(rect[0]), ctypes.c_float(rect[1]), ctypes.c_float(rect[2]), ctypes.c_float(rect[3]),
                                        self.pRtcEngienEventHandler)
            return ret

        if SdkVerson < '3.7.200':
            log.error(f'{SdkVerson} does not support this API')
            return -1
        channel = channel.encode('utf-8')
        filePath = filePath.encode('utf-8')
        ret = self.dll.takeSnapshot(self.pRtcEngine, ctypes.c_char_p(channel), uid, ctypes.c_char_p(filePath), self.pRtcEngienEventHandler)
        return ret

    @APITime
    def startServerSuperResolution(self, token: str, imagePath: str, scale: float, timeoutSeconds: int) -> int:
        if not SdkVerson.startswith('3.6.200.10'):
            log.error(f'{SdkVerson} does not support this API')
        token = token.encode('utf-8')
        imagePath = imagePath.encode('utf-8')
        ret = self.dll.startServerSuperResolution(self.pRtcEngine, ctypes.c_char_p(token), ctypes.c_char_p(imagePath), ctypes.c_float(scale), timeoutSeconds)
        return ret

    @APITime
    def setContentInspect(self, enable: bool, cloudWork: bool) -> int:
        if SdkVerson < '3.7.200':
            log.error(f'{SdkVerson} does not support this API')
            return -1
        ret = self.dll.setContentInspect(self.pRtcEngine, int(enable), int(cloudWork))
        return ret

    @APITime
    def startScreenCaptureByScreenRect(self, screenRect: Rectangle, regionRect: Rectangle, params: ScreenCaptureParameters) -> int:
        excludeWindowList = 0
        excludeWindowCount = 0
        if params.excludeWindowList:
            arrayType = ctypes.c_size_t * len(params.excludeWindowList)
            excludeWindowList = arrayType(*params.excludeWindowList)
            excludeWindowCount = len(params.excludeWindowList)
        ret = self.dll.startScreenCaptureByScreenRect(self.pRtcEngine, screenRect.x, screenRect.y, screenRect.width, screenRect.height,
                                                      regionRect.x, regionRect.y, regionRect.width, regionRect.height,
                                                      params.width, params.height, params.fps, params.bitrate,
                                                      excludeWindowList, excludeWindowCount)
        return ret

    @APITime
    def startPrimaryScreenCapture(self, screenRect: Rectangle, regionRect: Rectangle, params: ScreenCaptureParameters) -> int:
        excludeWindowList = 0
        excludeWindowCount = 0
        if params.excludeWindowList:
            arrayType = ctypes.c_size_t * len(params.excludeWindowList)
            excludeWindowList = arrayType(*params.excludeWindowList)
            excludeWindowCount = len(params.excludeWindowList)
        ret = self.dll.startPrimaryScreenCapture(self.pRtcEngine, screenRect.x, screenRect.y, screenRect.width, screenRect.height,
                                                 regionRect.x, regionRect.y, regionRect.width, regionRect.height,
                                                 params.width, params.height, params.fps, params.bitrate,
                                                 excludeWindowList, excludeWindowCount)
        return ret

    @APITime
    def startSecondaryScreenCapture(self, screenRect: Rectangle, regionRect: Rectangle, params: ScreenCaptureParameters) -> int:
        excludeWindowList = 0
        excludeWindowCount = 0
        if params.excludeWindowList:
            arrayType = ctypes.c_size_t * len(params.excludeWindowList)
            excludeWindowList = arrayType(*params.excludeWindowList)
            excludeWindowCount = len(params.excludeWindowList)
        ret = self.dll.startSecondaryScreenCapture(self.pRtcEngine, screenRect.x, screenRect.y, screenRect.width, screenRect.height,
                                                   regionRect.x, regionRect.y, regionRect.width, regionRect.height,
                                                   params.width, params.height, params.fps, params.bitrate,
                                                   excludeWindowList, excludeWindowCount)
        return ret

    @APITime
    def startScreenCaptureByWindowId(self, view: int, regionRect: Rectangle, params: ScreenCaptureParameters) -> int:
        ret = self.dll.startScreenCaptureByWindowId(self.pRtcEngine, ctypes.c_void_p(view),
                                                    regionRect.x, regionRect.y, regionRect.width, regionRect.height,
                                                    params.width, params.height, params.fps, params.bitrate)
        return ret

    @APITime
    def stopScreenCapture(self) -> int:
        ret = self.dll.stopScreenCapture(self.pRtcEngine)
        return ret

    @APITime
    def registerLocalUserAccount(self, appId: str, userAccount: str) -> int:
        appId = appId.encode('utf-8')
        userAccount = userAccount.encode('utf-8')
        ret = self.dll.registerLocalUserAccount(self.pRtcEngine, ctypes.c_char_p(appId), ctypes.c_char_p(userAccount))
        return ret

    @APITime
    def setExternalVideoSource(self, enable: bool) -> int:
        ret = self.dll.setExternalVideoSource(self.pRtcEngine, int(enable))
        return ret

    def pushVideoFrame(self, rawData: ctypes.c_void_p, videoFormat: VideoPixelFormat, width: int, height: int) -> int:
        ret = self.dll.pushVideoFrame(self.pRtcEngine, rawData, videoFormat, width, height)
        return ret

    def pushVideoFrameEx(self, rawData: ctypes.c_void_p, videoFormat: VideoPixelFormat, width: int, height: int, connection: RtcConnection) -> int:
        channelName = connection.channelId.encode('utf-8') if connection.channelId != None else 0
        ret = self.dll.pushVideoFrameEx(self.pRtcEngine, rawData, videoFormat, width, height, ctypes.c_char_p(channelName), connection.localUid)
        return ret

    @APITime
    def joinChannel(self, channelName: str, uid: int = 0, token: str = '', info: str = '') -> int:
        channelName = channelName.encode('utf-8')
        token = token.encode('utf-8')
        info = info.encode('utf-8')
        ret = self.dll.joinChannel(self.pRtcEngine, ctypes.c_char_p(channelName), uid, ctypes.c_char_p(token), ctypes.c_char_p(info))
        return ret

    @APITime
    def joinChannelWithOptions(self, channelName: str, uid: int = 0, token: str = '', options: ChannelMediaOptions = ChannelMediaOptions()) -> int:
        channelName = channelName.encode('utf-8')
        token = token.encode('utf-8')
        options.convertNone()
        ret = self.dll.joinChannelWithOptions(self.pRtcEngine,
                                              ctypes.c_char_p(channelName),
                                              uid, ctypes.c_char_p(token),
                                              options.channelProfile,
                                              options.clientRole,
                                              options.autoSubscribeAudio,
                                              options.autoSubscribeVideo,
                                              options.publishAudioTrack,
                                              options.publishCameraTrack,
                                              options.publishSecondaryCameraTrack,
                                              options.publishScreenTrack,
                                              options.publishSecondaryScreenTrack,
                                              options.publishCustomAudioTrack,
                                              options.publishCustomVideoTrack)
        return ret

    @APITime
    def updateChannelMediaOptions(self, options: ChannelMediaOptions) -> int:
        options.convertNone()
        ret = self.dll.updateChannelMediaOptions(self.pRtcEngine,
                                                 options.channelProfile,
                                                 options.clientRole,
                                                 options.autoSubscribeAudio,
                                                 options.autoSubscribeVideo,
                                                 options.publishAudioTrack,
                                                 options.publishCameraTrack,
                                                 options.publishSecondaryCameraTrack,
                                                 options.publishScreenTrack,
                                                 options.publishSecondaryScreenTrack,
                                                 options.publishCustomAudioTrack,
                                                 options.publishCustomVideoTrack)
        return ret

    @APITime
    def joinChannelWithUserAccount(self, channelName: str, userAccount: str, token: str = '', options: ChannelMediaOptions = None) -> int:
        channelName = channelName.encode('utf-8')
        userAccount = userAccount.encode('utf-8')
        token = token.encode('utf-8')
        if options is None:
            ret = self.dll.joinChannelWithUserAccount(self.pRtcEngine, ctypes.c_char_p(channelName),
                                                      ctypes.c_char_p(userAccount), ctypes.c_char_p(token))
        else:
            options.convertNone()
            ret = self.dll.joinChannelWithUserAccount2(self.pRtcEngine,
                                                       ctypes.c_char_p(channelName),
                                                       ctypes.c_char_p(userAccount),
                                                       ctypes.c_char_p(token),
                                                       options.channelProfile,
                                                       options.clientRole,
                                                       options.autoSubscribeAudio,
                                                       options.autoSubscribeVideo,
                                                       options.publishAudioTrack,
                                                       options.publishCameraTrack,
                                                       options.publishSecondaryCameraTrack,
                                                       options.publishScreenTrack,
                                                       options.publishSecondaryScreenTrack,
                                                       options.publishCustomAudioTrack,
                                                       options.publishCustomVideoTrack)
        return ret

    @APITime
    def leaveChannel(self) -> int:
        ret = self.dll.leaveChannel(self.pRtcEngine)
        return ret

    @APITime
    def joinChannelEx(self, connection: RtcConnection, token: str = '', options: ChannelMediaOptions = ChannelMediaOptions()) -> int:
        channelName = connection.channelId.encode('utf-8') if connection.channelId != None else 0
        token = token.encode('utf-8')
        options.convertNone()
        ret = self.dll.joinChannelEx(self.pRtcEngine,
                                     ctypes.c_char_p(channelName),
                                     connection.localUid,
                                     ctypes.c_char_p(token),
                                     self.pRtcEngienEventHandlerEx,
                                     options.channelProfile,
                                     options.clientRole,
                                     options.autoSubscribeAudio,
                                     options.autoSubscribeVideo,
                                     options.publishAudioTrack,
                                     options.publishCameraTrack,
                                     options.publishSecondaryCameraTrack,
                                     options.publishScreenTrack,
                                     options.publishSecondaryScreenTrack,
                                     options.publishCustomAudioTrack,
                                     options.publishCustomVideoTrack)
        return ret

    @APITime
    def updateChannelMediaOptionsEx(self, connection: RtcConnection, options: ChannelMediaOptions) -> int:
        channelName = connection.channelId.encode('utf-8') if connection.channelId != None else 0
        options.convertNone()
        ret = self.dll.updateChannelMediaOptionsEx(self.pRtcEngine,
                                                   ctypes.c_char_p(channelName),
                                                   connection.localUid,
                                                   options.channelProfile,
                                                   options.clientRole,
                                                   options.autoSubscribeAudio,
                                                   options.autoSubscribeVideo,
                                                   options.publishAudioTrack,
                                                   options.publishCameraTrack,
                                                   options.publishSecondaryCameraTrack,
                                                   options.publishScreenTrack,
                                                   options.publishSecondaryScreenTrack,
                                                   options.publishCustomAudioTrack,
                                                   options.publishCustomVideoTrack)
        return ret

    @APITime
    def leaveChannelEx(self, connection: RtcConnection) -> int:
        channelName = connection.channelId.encode('utf-8')
        ret = self.dll.leaveChannelEx(self.pRtcEngine, ctypes.c_char_p(channelName), connection.localUid)
        return ret

    @APITime
    def muteLocalAudioStream(self, mute: bool) -> int:
        ret = self.dll.muteLocalAudioStream(self.pRtcEngine, int(mute))
        return ret

    @APITime
    def muteLocalVideoStream(self, mute: bool) -> int:
        ret = self.dll.muteLocalVideoStream(self.pRtcEngine, int(mute))
        return ret

    @APITime
    def muteRemoteAudioStream(self, uid: int, mute: bool, connectionId: int = DefaultConnectionId) -> int:
        ret = self.dll.muteRemoteAudioStream(self.pRtcEngine, uid, int(mute), connectionId)
        return ret

    @APITime
    def muteRemoteVideoStream(self, uid: int, mute: bool, connectionId: int = DefaultConnectionId) -> int:
        ret = self.dll.muteRemoteVideoStream(self.pRtcEngine, uid, int(mute), connectionId)
        return ret

    @APITime
    def createDataStream(self, reliable: bool = True, ordered: bool = True, connectionId: int = DefaultConnectionId) -> Tuple[int, int]:
        streamId = ctypes.c_int(0)
        ret = self.dll.createDataStream(self.pRtcEngine, ctypes.byref(streamId), int(reliable), int(ordered), connectionId)
        return (ret, streamId.value)

    @APITime
    def sendStreamMessage(self, streamId: int, data: str, connectionId: int = DefaultConnectionId) -> int:
        data = data.encode('utf-8')
        ret = self.dll.sendStreamMessage(self.pRtcEngine, streamId, ctypes.c_char_p(data), len(data), connectionId)
        return ret

    @APITime
    def getVideoDeviceId(self) -> str:
        arrayType = ctypes.c_char * 512
        charArray = arrayType()
        ret = self.dll.getVideoDeviceId(self.pRtcEngine, charArray, len(charArray))
        deviceId = ''
        if ret == 0:
            deviceId = charArray.value.decode('utf-8')
        return deviceId

    @APITime
    def setVideoDeviceId(self, deviceId: str) -> int:
        deviceId = deviceId.encode('utf-8')
        ret = self.dll.setVideoDeviceId(self.pRtcEngine, ctypes.c_char_p(deviceId))
        return ret

    @APITime
    def getVideoDevices(self) -> List[Tuple[str, str]]:
        arrayType = ctypes.c_char * 5210
        charArray = arrayType()
        ret = self.dll.getVideoDevices(self.pRtcEngine, charArray, len(charArray))
        devices = []
        if ret == 0 and charArray.value:
            formatedStr = charArray.value.decode('utf-8')
            parts = formatedStr.split('||')
            log.info(f'device count {len(parts)}')
            for part in parts:
                deviceParts = part.split('%%')
                #log.info(f'device {deviceParts}')  #name, id
                devices.append((deviceParts[0], deviceParts[1]))
        return devices

    @APITime
    def getVideoDeviceNumberOfCapabilities(self, deviceId: str) -> int:
        deviceId = deviceId.encode('utf-8')
        return self.dll.getVideoDeviceNumberOfCapabilities(self.pRtcEngine, ctypes.c_char_p(deviceId))

    @APITime
    def getVideoDeviceCapabilities(self, deviceId: str) -> List[Tuple[int, int, int]]:
        deviceId = deviceId.encode('utf-8')
        arrayType = ctypes.c_char * 5210
        charArray = arrayType()
        ret = self.dll.getVideoDeviceCapabilities(self.pRtcEngine, ctypes.c_char_p(deviceId), charArray, len(charArray))
        capabilities = []
        if ret == 0 and charArray.value:
            formatedStr = charArray.value.decode('utf-8')
            parts = formatedStr.split('||')
            log.info(f'capabilities count {len(parts)}')
            for part in parts:
                capParts = part.split('|')
                #log.info(f'device {deviceParts}')  # width, height, fps
                capabilities.append((capParts[0], capParts[1], capParts[2]))
        return capabilities

    @APITime
    def setParameters(self, params: str) -> int:
        params = params.encode('utf-8')
        ret = self.dll.setParameters(self.pRtcEngine, ctypes.c_char_p(params))
        return ret

    @APITime
    def getStringParameter(self, params: str, maxLen: int = 128) -> Tuple[int, str]:
        params = params.encode('utf-8')
        arrayType = ctypes.c_char * maxLen
        charArray = arrayType()
        ret = self.dll.getStringParameter(self.pRtcEngine, ctypes.c_char_p(params), charArray, len(charArray))
        return ret, charArray.value.decode('utf-8')

    @APITime
    def getObjectParameter(self, params: str, maxLen: int = 512) -> Tuple[int, str]:
        params = params.encode('utf-8')
        arrayType = ctypes.c_char * maxLen
        charArray = arrayType()
        ret = self.dll.getObjectParameter(self.pRtcEngine, ctypes.c_char_p(params), charArray, len(charArray))
        return ret, charArray.value.decode('utf-8')

    @APITime
    def getBoolParameter(self, params: str) -> Tuple[int, bool]:
        params = params.encode('utf-8')
        cValue = ctypes.c_int32(0)
        ret = self.dll.getBoolParameter(self.pRtcEngine, ctypes.c_char_p(params), ctypes.byref(cValue))
        return ret, bool(cValue.value)

    @APITime
    def getIntParameter(self, params: str) -> Tuple[int, int]:
        params = params.encode('utf-8')
        cValue = ctypes.c_int32(0)
        ret = self.dll.getIntParameter(self.pRtcEngine, ctypes.c_char_p(params), ctypes.byref(cValue))
        return ret, cValue.value

    @APITime
    def getNumberParameter(self, params: str) -> Tuple[int, float]:
        params = params.encode('utf-8')
        cValue = ctypes.c_double(0.0)
        ret = self.dll.getNumberParameter(self.pRtcEngine, ctypes.c_char_p(params), ctypes.byref(cValue))
        return ret, cValue.value


if __name__ == '__main__':
    chooseSdkBinDir('binx86_3.6.200.100')
    rtcEngine = RtcEngine()
    log.info(rtcEngine.getVersion())
    appId = 'aab8b8f5a8cd4469a63042fcfafe7063'
    context = RtcEngineContext(appId)
    localView = 0x808E8
    remoteView = 0x970D7A

    def EventCallback(userData: str, epochTime: int, funcName: str, json: str):
        log.info(f'{userData}, {funcName}, {json}')

    rtcEngine.initalize(context, EventCallback)
    rtcEngine.setChannelProfile(ChannelProfile.LiveBroadcasting)
    rtcEngine.setClientRole(ClientRole.Broadcaster)
    ret = rtcEngine.loadExtensionProvider('libagora_video_process.dll')
    print('\n------------loadExtensionProvider returns', ret)
    rtcEngine.enableVideo()
    # rtcEngine.enableLocalVideo(True)
    videoConfig = VideoEncoderConfiguration(width=1280, height=720, frameRate=15)
    rtcEngine.setVideoEncoderConfiguration(videoConfig=videoConfig, connectionId=DefaultConnectionId)
    input('paused')
    rtcEngine.setupLocalVideo(videoCanvas=VideoCanvas(uid=0, view=localView))
    rtcEngine.startPreview()
    # rtcEngine.setParameters('{"rtc.debug.enable": true}')
    rtcEngine.joinChannel(channelName='ykstest', uid=222)
    # print('get rtc.debug.enable', rtcEngine.getBoolParameter('rtc.debug.enable'))
    time.sleep(1)
    rtcEngine.setupRemoteVideo(videoCanvas=VideoCanvas(uid=111, view=remoteView))
    input('paused')
    rtcEngine.leaveChannel()
    rtcEngine.stopPreview()
    rtcEngine.release(sync=True)
    if sys.platform == 'win32':
        ctypes.windll.user32.ShowWindow(ctypes.c_void_p(localView), 5)  # Show=5
        ctypes.windll.user32.ShowWindow(ctypes.c_void_p(remoteView), 5)


