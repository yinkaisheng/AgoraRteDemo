backgroundSource = agsdk.VirtualBackgroundSource()
backgroundSource.backgroundSourceType = 1 # 1, 2, 3
backgroundSource.color = 0xFFFFFF
backgroundSource.source = r'd:/test.jpg'
backgroundSource.blurDegree = 3 # 1, 2, 3
backgroundSource.modelType = 0 # 0, 2
backgroundSource.preferVelocity = 1
backgroundSource.greenCapacity = 0.5
segProperty = agorasdk.SegmentationProperty()
segProperty.modelType = 0 # 0, 2
segProperty.preferVelocity = 1
segProperty.greenCapacity = 0.5
ret = self.rtcEngine.enableVirtualBackground(True, backgroundSource, segProperty, sourceType=2)
self.checkSDKResult(ret)