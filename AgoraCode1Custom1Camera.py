
def custom1Camera1Test(self) -> None:
    channelName = 'sdktest'
    self.localUids = [1000, 1001, 1002, 1003]
    token = ''
    info = ''
    self.autoSubscribeVideoEx = False # ex channel don't call setupRemoteVideo
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
        appId = transformAppId(appId)
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

    ret = self.rtcEngine.enableVideo()
    self.checkSDKResult(ret)
    if ret != 0:
        return

    # custom
    uid = self.localUids[viewIndex]
    token = ''

    sourceType = agsdk.VideoSourceType.Custom
    videoCanvas = agsdk.VideoCanvas(uid=0, view=0)
    videoCanvas.view = int(self.videoLabels[viewIndex].winId())
    videoCanvas.sourceType = sourceType
    videoCanvas.mirrorMode = agsdk.VideoMirrorMode.Disabled
    videoCanvas.renderMode = agsdk.RenderMode.Fit
    videoCanvas.isScreenView = False
    self.rtcEngine.setupLocalVideo(videoCanvas)
    self.checkSDKResult(ret)

    self.rtcEngine.setExternalVideoSource(True)
    self.isPushEx = False
    fps = 15
    self.pushTimer.start(1000 // fps)
    self.pushUid = uid

    options = agsdk.ChannelMediaOptions()
    options.autoSubscribeAudio = False
    options.autoSubscribeVideo = False
    options.publishAudioTrack = False
    options.publishCameraTrack = False
    options.publishCustomVideoTrack = True

    self.channelName = channelName
    self.channelNameEdit.setText(channelName)
    self.uidEdit.setText(str(uid))

    self.channelOptions = options
    self.channelName = channelName
    ret = self.rtcEngine.joinChannelWithOptions(channelName, uid, token, options)
    self.checkSDKResult(ret)
    self.joined = True

    for remoteUid in self.localUids:
        ret = self.rtcEngine.muteRemoteAudioStream(remoteUid, True)
        ret = self.rtcEngine.muteRemoteVideoStream(remoteUid, True)

    self.rtcEngine.startPreview(sourceType)
    self.checkSDKResult(ret)

    self.viewUsingIndex.add(viewIndex)

    #cameras
    devices = self.rtcEngine.getVideoDevices()

    if len(devices) < 2:
        agsdk.log.warn('video devices count < 2')
        return
    #primary camera
    viewIndex += 1
    uid = self.localUids[viewIndex]

    sourceType = agsdk.VideoSourceType.CameraPrimary
    videoCanvas = agsdk.VideoCanvas(uid=0, view=0)
    videoCanvas.view = int(self.videoLabels[viewIndex].winId())
    videoCanvas.sourceType = sourceType
    videoCanvas.mirrorMode = agsdk.VideoMirrorMode.Disabled
    videoCanvas.renderMode = agsdk.RenderMode.Fit
    videoCanvas.isScreenView = False
    self.rtcEngine.setupLocalVideo(videoCanvas)
    self.checkSDKResult(ret)

    #for deviceName, deviceId in devices:
        #pass
    deviceId = devices[0][1]
    cameraConfig = agsdk.CameraCapturerConfiguration()
    cameraConfig.deviceId = deviceId
    cameraConfig.width = 640
    cameraConfig.height = 360
    cameraConfig.frameRate = 15
    ret = self.rtcEngine.startPrimaryCameraCapture(cameraConfig)
    self.checkSDKResult(ret)

    self.rtcEngine.startPreview(sourceType)
    self.checkSDKResult(ret)

    options = agsdk.ChannelMediaOptions()
    options.autoSubscribeAudio = False
    options.autoSubscribeVideo = False
    options.publishAudioTrack = False
    options.publishCameraTrack = True

    self.uidExEdit.setText(str(uid))
    self.channelNameEx = channelName
    self.channelExOptions = options
    self.rtcConnection = agsdk.RtcConnection(channelName, uid)
    ret = self.rtcEngine.joinChannelEx(self.rtcConnection, token, options)
    self.checkSDKResult(ret)
    self.joinedEx = True

    self.viewUsingIndex.add(viewIndex)
    self.viewIndex2EncoderMirrorMode[viewIndex] = videoCanvas.mirrorMode


MainWindow.custom1Camera1Test = custom1Camera1Test
self.custom1Camera1Test()