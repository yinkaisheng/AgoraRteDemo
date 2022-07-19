#!python3
# -*- coding: utf-8 -*-
# author: yinkaisheng@foxmail.com
import string


def decodeAppId(appId: str) -> str:
    '''
    decode the AppId gotten from the config file
    if you don't want to put AppId plaintext in config file
    you can put encoded AppId in config file and implement this function to decode it
    '''
    return appId
