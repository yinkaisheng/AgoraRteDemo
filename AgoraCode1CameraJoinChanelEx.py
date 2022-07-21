def joinChannelExTest(self) -> None:
    channelName = 'sdktest'
    uidCount = 1
    self.localUids = []
    for i in range(uidCount):
        self.localUids.append(random.randint(10000, 100000) + random.randint(1000, 10000) + random.randint(100, 1000) + random.randint(10, 100))
    token = ''
    info = ''
    self.autoSubscribeVideoEx = True
    viewIndex = 0

    if self.rtcEngine is None:
        self.rtcEngine = agsdk.RtcEngine()
    version, build = self.rtcEngine.getVersion()
    self.setWindowTitle(f'{DemoTile} Version={version}, Build={build}, SdkDir={agsdk.agorasdk.SdkBinDir}')
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

    # self.rtcEngine.setParameters('{"rtc.video.playout_delay_min": 0}')
    # self.rtcEngine.setParameters('{"rtc.video.playout_delay_max": 500}')

    ret = self.rtcEngine.registerVideoFrameObserver()
    self.checkSDKResult(ret)

    ret = self.rtcEngine.enableVideo()
    self.checkSDKResult(ret)
    if ret != 0:
        return

    #primary camera
    uid = self.localUids[viewIndex]

    sourceType = agsdk.VideoSourceType.CameraPrimary
    videoCanvas = agsdk.VideoCanvas(uid=0, view=0)
    videoCanvas.view = int(self.videoLabels[viewIndex].winId())
    videoCanvas.sourceType = sourceType
    videoCanvas.mirrorMode = agsdk.VideoMirrorMode.Disabled
    videoCanvas.renderMode = agsdk.RenderMode.Fit
    videoCanvas.isScreenView = False
    if agsdk.agorasdk.SdkVersion >= '3.8.200':
        videoCanvas.setupMode = agsdk.ViewSetupMode.Add
    self.rtcEngine.setupLocalVideo(videoCanvas)
    self.checkSDKResult(ret)

    self.rtcEngine.startPreview(sourceType)
    self.checkSDKResult(ret)

    options = agsdk.ChannelMediaOptions()
    options.channelProfile = agsdk.ChannelProfile.LiveBroadcasting
    options.clientRoleType = agsdk.ClientRole.Broadcaster
    options.autoSubscribeAudio = True
    options.autoSubscribeVideo = True
    options.publishAudioTrack = True
    options.publishCameraTrack = True
    options.publishSecondaryCameraTrack = False

    self.channelNameEdit.setText(channelName)
    self.uidExEdit.setText(str(uid))
    self.channelNameEx = channelName
    self.channelExOptions = options
    self.rtcConnection = agsdk.RtcConnection(channelName, uid)
    ret = self.rtcEngine.joinChannelEx(self.rtcConnection, token, options)
    self.checkSDKResult(ret)
    self.joinedEx = True

    self.viewUsingIndex.add(viewIndex)
    self.viewIndex2EncoderMirrorMode[viewIndex] = videoCanvas.mirrorMode

    # self.rtcEngine.startPreview(sourceType)
    # self.checkSDKResult(ret)


MainWindow.joinChannelExTest = joinChannelExTest
self.joinChannelExTest()