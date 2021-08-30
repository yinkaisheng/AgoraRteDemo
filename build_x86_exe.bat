
d:\Python38\python.exe -m nuitka --mingw64 --follow-imports --show-progress --show-memory --output-dir=out AgoraRteDemo.py

REM C:\Python38\python.exe -m nuitka --mingw64 --show-progress --show-memory --output-dir=out --follow-import-to agorasdk --follow-import-to pyqt5AsyncTask --follow-import-to transformAppId --follow-import-to util --follow-import-to=site-packages AgoraRteDemo.py

REM D:\Python38\python.exe -m nuitka --mingw64 --follow-imports --output-dir=out AgoraRteDemo.py

REM nuitka --mingw64 --standalone --follow-imports --show-progress --show-memory --plugin-enable=qt-plugins --include-qt-plugins=sensible,styles --output-dir=out AgoraRteDemo.py

REM --windows-disable-console
REM --nofollow-import-to