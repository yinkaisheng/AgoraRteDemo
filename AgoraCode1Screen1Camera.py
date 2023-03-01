def screen1Camera1Test(self) -> None:
    channelName = 'sdktest'
    token = ''
    uidCount = 2
    self.localUids = []
    for i in range(uidCount):
        self.localUids.append(random.randint(10000, 100000) + random.randint(1000, 10000) + random.randint(100, 1000) + random.randint(10, 100))
    token = ''
    info = ''
    self.autoSubscribeVideoEx = False # ex channel don't call setupRemoteVideo
    viewIndex = 0

    if self.rtcEngine is None:
        self.rtcEngine = agsdk.RtcEngine()
    version, build = self.rtcEngine.getVersion()
    self.setWindowTitle(f'{DemoTile} Version={version}, Build={build}, SdkDir={agsdk.agorasdk.SdkBinDir}, pid={os.getpid()}')
    appName = self.configJson['appNameList'][self.appNameComBox.currentIndex()]['appName']
    appId = self.configJson['appNameList'][self.appNameComBox.currentIndex()]['appId']
    if appId == '00000000000000000000000000000000':
        QMessageBox.warning(None, 'Error', f'You need to set a valid AppId in the config file:\n{self.configPath}')
        return
    elif appName.startswith('Agora'):
        appId = decodeAppId(appId)
    self.appId = appId
    context = agsdk.RtcEngineContext(appId)
    context.channelProfile = agsdk.ChannelProfile.LiveBroadcasting
    context.logConfig.logPath = os.path.join(agsdk.LogDir, 'AgoraSdk_log.log')
    ret = self.rtcEngine.initalize(context, self.onRtcEngineCallbackInThread)
    self.checkSDKResult(ret)
    if ret != 0:
        return
    self.inited = True

    ret = self.rtcEngine.setClientRole(agsdk.ClientRole.Broadcaster)
    self.checkSDKResult(ret)
    if ret != 0:
        return

    ret = self.rtcEngine.registerVideoFrameObserver()
    self.checkSDKResult(ret)

    # self.rtcEngine.setParameters('{"rtc.video.playout_delay_min": 0}')
    # self.rtcEngine.setParameters('{"rtc.video.playout_delay_max": 500}')

    ret = self.rtcEngine.enableVideo()
    self.checkSDKResult(ret)
    if ret != 0:
        return

    #primary screen
    uid = self.localUids[viewIndex]

    screenRect = agsdk.Rectangle(0, 0, 1920, 1080)
    regionRect = agsdk.Rectangle(0, 0, 0, 0)
    excludeWindows = []
    captureParams = agsdk.ScreenCaptureParameters(screenRect.width, screenRect.height, fps=15, bitrate=0, excludeWindowList=excludeWindows)
    ret = self.rtcEngine.startPrimaryScreenCapture(screenRect, regionRect, captureParams)
    self.checkSDKResult(ret)

    sourceType = agsdk.VideoSourceType.Screen
    videoCanvas = agsdk.VideoCanvas(uid=0, view=0)
    videoCanvas.view = int(self.videoLabels[viewIndex].winId())
    videoCanvas.sourceType = sourceType
    videoCanvas.mirrorMode = agsdk.VideoMirrorMode.Disabled
    videoCanvas.renderMode = agsdk.RenderMode.Fit
    videoCanvas.isScreenView = True
    self.rtcEngine.setupLocalVideo(videoCanvas)
    self.checkSDKResult(ret)

    ret = self.rtcEngine.startPreview(sourceType)
    self.checkSDKResult(ret)

    # videoConfig = agsdk.VideoEncoderConfiguration(width=640, height=360, frameRate=15, bitrate=0, codecType=agsdk.VideoCodec.H264,
                                                  # degradationPreference=agsdk.DegradationPreference.MaintainQuality,
                                                  # minBitrate=-1, mirrorMode=agsdk.VideoMirrorMode.Disabled,
                                                  # orientationMode=agsdk.OrientationMode.Adaptive)
    # ret = self.rtcEngine.setVideoEncoderConfiguration(videoConfig)
    # self.checkSDKResult(ret)

    options = agsdk.ChannelMediaOptions()
    options.channelProfile = agsdk.ChannelProfile.LiveBroadcasting
    options.clientRoleType = agsdk.ClientRole.Broadcaster
    options.autoSubscribeAudio = True
    options.autoSubscribeVideo = True
    options.publishAudioTrack = True
    options.publishScreenTrack = True
    options.publishCameraTrack = False # need this? todo
    # options.publishSecondaryCameraTrack = None
    # options.publishSecondaryScreenTrack = None
    # options.publishCustomAudioTrack = None
    # options.publishCustomVideoTrack = None
    # options.publishCustomAudioTrackEnableAec = None
    # options.publishEncodedVideoTrack = None
    # options.publishMediaPlayerAudioTrack = None
    # options.publishMediaPlayerVideoTrack = None
    # options.publishTrancodedVideoTrack = None
    # options.enableAudioRecordingOrPlayout = None
    # options.publishMediaPlayerId = None
    # options.audioDelayMs = None
    # options.audienceLatencyLevel = None
    # options.defaultVideoStreamType = None

    self.channelNameEdit.setText(channelName)
    self.uidEdit.setText(str(uid))
    self.channelOptions = options
    ret = self.rtcEngine.joinChannelWithOptions(channelName, uid, token='', options=options)
    self.checkSDKResult(ret)

    self.joined = True
    self.viewUsingIndex.add(viewIndex)
    self.viewIndex2EncoderMirrorMode[viewIndex] = videoCanvas.mirrorMode

    for remoteUid in self.localUids:
        ret = self.rtcEngine.muteRemoteAudioStream(remoteUid, True)
        ret = self.rtcEngine.muteRemoteVideoStream(remoteUid, True)

    # primary camera
    viewIndex += 1
    uid = self.localUids[viewIndex]

    devices = self.rtcEngine.enumerateVideoDevices()

    if len(devices) < 1:
        agsdk.log.warn('video devices count < 1')
        return
    #print('deviceName', devices[0][0])
    #print('deviceId', devices[0][1])
    deviceId = devices[0][1]
    cameraConfig = agsdk.CameraCapturerConfiguration()
    cameraConfig.deviceId = deviceId
    cameraConfig.width = 640
    cameraConfig.height = 360
    cameraConfig.frameRate = 15
    ret = self.rtcEngine.startPrimaryCameraCapture(cameraConfig)
    self.checkSDKResult(ret)

    sourceType = agsdk.VideoSourceType.CameraPrimary
    videoCanvas = agsdk.VideoCanvas(uid=0, view=0)
    videoCanvas.view = int(self.videoLabels[viewIndex].winId())
    videoCanvas.sourceType = sourceType
    videoCanvas.mirrorMode = agsdk.VideoMirrorMode.Disabled
    videoCanvas.renderMode = agsdk.RenderMode.Fit
    videoCanvas.isScreenView = False
    self.rtcEngine.setupLocalVideo(videoCanvas)
    self.checkSDKResult(ret)

    self.rtcEngine.startPreview(sourceType)
    self.checkSDKResult(ret)

    self.channelNameEx = channelName
    self.uidExEdit.setText(str(uid))
    self.rtcConnection = agsdk.RtcConnection(channelName, uid)

    options = agsdk.ChannelMediaOptions()
    options.channelProfile = agsdk.ChannelProfile.LiveBroadcasting
    options.clientRoleType = agsdk.ClientRole.Broadcaster
    options.autoSubscribeAudio = False
    options.autoSubscribeVideo = False
    options.publishAudioTrack = False
    options.publishCameraTrack = True
    self.channelExOptions = options

    ret = self.rtcEngine.joinChannelEx(self.rtcConnection, token, options)
    self.checkSDKResult(ret)
    self.joinedEx = True
    self.viewUsingIndex.add(viewIndex)
    self.viewIndex2EncoderMirrorMode[viewIndex] = videoCanvas.mirrorMode

    #videoConfig = agsdk.VideoEncoderConfiguration(width=640, height=360, frameRate=15, bitrate=0, codecType=agsdk.VideoCodec.H264,
                                                  #degradationPreference=agsdk.DegradationPreference.MaintainQuality,
                                                  #minBitrate=-1, mirrorMode=agsdk.VideoMirrorMode.Disabled,
                                                  #orientationMode=agsdk.OrientationMode.Adaptive)
    #ret = self.rtcEngine.setVideoEncoderConfiguration(videoConfig)
    #self.checkSDKResult(ret)

MainWindow.screen1Camera1Test = screen1Camera1Test
self.screen1Camera1Test()