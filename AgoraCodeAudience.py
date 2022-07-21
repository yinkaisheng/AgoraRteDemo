def audienceTest(self) -> None:
    channelName = '0623-15'
    uid = 3334
    token = ''
    info = ''
    self.autoSubscribeVideoEx = False # ex channel don't call setupRemoteVideo

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

    ret = self.rtcEngine.setClientRole(agsdk.ClientRole.Audience)
    self.checkSDKResult(ret)
    if ret != 0:
        return

    ret = self.rtcEngine.registerVideoFrameObserver()
    self.checkSDKResult(ret)

    ret = self.rtcEngine.setParameters('{"engine.video.enable_hw_encoder": true}')
    ret = self.rtcEngine.setParameters('{"engine.video.enable_hw_decoder": true}')

    ret = self.rtcEngine.enableVideo()
    self.checkSDKResult(ret)
    if ret != 0:
        return

    self.channelName = channelName
    self.channelNameEdit.setText(channelName)
    self.uidEdit.setText(str(uid))

    ret = self.rtcEngine.joinChannel(channelName, uid, token, info)

MainWindow.audienceTest = audienceTest
self.audienceTest()