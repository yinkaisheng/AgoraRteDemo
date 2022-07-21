self.pushTextCount = 0
self.exampleText = '自采集测试\n' + '\nAre you OK? Are you OK?' * 3
def funnyPushText(self):
    self.pushTextCount += 1
    self.pushText = self.exampleText[:self.pushTextCount]
    if self.pushTextCount == len(self.exampleText):
        self.pushTextCount = -1
    if self.joined:
        self.delayCall(timeMs=100, func=self.funnyPushText)
    else:
        self.pushTextCount = 0
MainWindow.funnyPushText = funnyPushText
if self.joined:
    self.delayCall(timeMs=1000, func=self.funnyPushText)