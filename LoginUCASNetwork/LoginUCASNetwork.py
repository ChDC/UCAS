#!/usr/bin/env python3

import json
import os
import time
import random
import logging
from os import path
from urllib.request import urlopen
from datetime import datetime
from logging import debug as d

logging.basicConfig(level=logging.DEBUG)

# *************************** Helper ****************************


def writeConfig(fileName, data):
    """写配置文件"""
    with open(fileName, 'w', encoding='utf8') as fh:
        fh.write(json.dumps(data, indent=4))


def readConfig(fileName):
    """读取配置文件"""
    if path.isfile(fileName):
        with open(fileName, encoding='utf8') as fh:
            return json.loads(fh.read())


def showMessageWithTk(title, msg):
    import tkinter
    tk = tkinter.Tk()
    tkinter.Label(text=msg).pack()
    tk.title(title)
    tk.attributes('-toolwindow', True)
    tk.resizable(False, False)
    tk.after(3000, lambda: tk.destroy())
    tk.mainloop()


def showMessage(title, msg):
    """显示消息"""
    try:
        showMessageWithTk(title, msg)
    except:
        print(title)
        print(msg)


def askUserInfo():
    """弹窗让用户填写账号信息"""
    import tkinter
    import tkinter.messagebox
    tk = tkinter.Tk()

    userId, password = None, None
    tkinter.Label(tk, text='账号：').grid(row=0, column=0)
    txtUserId = tkinter.Entry(tk)
    txtUserId.grid(row=0, column=1)
    txtUserId.focus_set()

    tkinter.Label(tk, text='密码：').grid(row=1, column=0)
    txtPassword = tkinter.Entry(tk, show='*')
    txtPassword.grid(row=1, column=1)

    def btnOkClick():
        if not txtUserId.get() or not txtPassword.get():
            tkinter.messagebox.showerror('错误', '账号或密码不能为空！')
        else:
            nonlocal userId, password
            userId, password = txtUserId.get(), txtPassword.get()
            tk.destroy()

    tkinter.Button(tk, text="确定", command=btnOkClick).grid(row=2, column=1)
    tkinter.Button(tk, text="取消", command=tk.destroy).grid(row=2, column=0)

    tk.title('输入账号和密码')
    tk.attributes('-toolwindow', True)
    tk.resizable(False, False)
    tk.mainloop()
    return userId, password

# *************************** Helper End ****************************

# *************************** AuthInterface ****************************


def login(userId, password):
    """登录UCAS"""
    userId = userId.strip()
    passsword = password.strip()
    loginUrl = str.format('http://210.77.16.21/eportal/InterFace.do?method=login&userId={userId}&password={password}&service=&queryString=1&operatorPwd=&validcode=',
                          **locals())
    # d(loginUrl)
    try:
        fh = urlopen(loginUrl)
        # 不加下面的这句会出错
        time.sleep(0.1)
        html = fh.read().decode("utf8")
        result = json.loads(html)
        if result['result'] != 'success':
            for errout, errin in errorMessage:
                if errin in result['message']:
                    return False, errout, (userId, passsword)
            return False, result['message'], (userId, passsword)
        return True, result['userIndex'], (userId, passsword)
    except Exception as e:
        return False, e, (userId, passsword)


def getOnlineUserInfo(userIndex):
    """获取套餐信息"""
    try:
        success_url = str.format("http://210.77.16.21/eportal/InterFace.do?method=getOnlineUserInfo&userIndex={userIndex}",
                                 **locals())
        result = urlopen(success_url).read().decode('utf8')
        if not result:
            return None
        result = json.loads(result)

        userName = result['userName']
        offlineurl = result['offlineurl']
        ballInfo = result['ballInfo']

        ballInfo = json.loads(ballInfo)
        flow = ballInfo[1]['value'] if ballInfo[1]['id'] == 'flow' else 0
        flow_with_mb = float(flow) / 1024 / 1024
        flow_info = ''
        if flow_with_mb > 1024:
            flow_info = str.format('{:.2f} GB', flow_with_mb / 1024)
        else:
            flow_info = str.format('{:.2f} MB', flow_with_mb)
        onlinedevice = ballInfo[2]['value'] if ballInfo[2]['id'] == 'onlinedevice' else 0

        info = {}
        info['flow_info'] = flow_info
        info['flow'] = flow
        info['onlinedevice'] = onlinedevice

        info['userId'] = result['userId']
        info['userName'] = userName
        # d(info)
        return info
    except Exception as e:
        return None


def logout(userIndex=None):
    """注销"""
    if not userIndex:
        userIndex = getCurUserIndex()
    if not userIndex:
        return
    url = r'http://210.77.16.21/eportal/InterFace.do?method=logout&userIndex={}'.format(userIndex)
    # d(url)
    try:
        urlopen(url)
    except:
        pass


def logoutByUserIdAndPass(userId, password):
    """使用用户名密码下线所有用户"""
    url = r'http://210.77.16.21/eportal/InterFace.do?method=logoutByUserIdAndPass&userId={}&pass={password}'.format(
        userId, password)
    d(url)
    try:
        urlopen(url)
    except:
        pass


def getCurUserIndex():
    """获取当前账号的UserIndex"""
    result, info, aInfo = login('123456', '123456')
    if result:
        return info
    return None

errorMessage = (
    ("NoUser", "用户不存在"),
    ("NoUser", "用户未确认网络协议书"),
    ("NoPassword", "密码不匹配"),
    ("NoFlow", "无可用剩余流量")
)

# *************************** AuthInterface End ****************************


def isOnline():
    """检查当前是否在线"""
    patternString = "location.href='http://210.77.16.21:80"
    checkUrl = 'http://www.baidu.com'
    with urlopen(checkUrl) as fh:
        data = fh.read().decode()
    if len(data) < 500 or patternString in data:
        return False
    else:
        return True


def getInfoString(info):
    """获取需要打印的用户信息"""
    return str.format('名字:{userName}\n账号：{userId}\n剩余流量：{flow_info}\n在线设备：{onlinedevice}', **info)


def filterUsableAccount(accountFileName, outputFile, defaultPassword='ucas', minFlowWithGB=0, onlineDevice=0, resultAmount=None):
    """把数据文件中的可用账号筛选进文件中"""
    curAmount = 0
    # 下线当前账号
    logout()
    tmpFile = outputFile + '.tmp'
    with open(tmpFile, 'w', encoding='utf8') as of, open(accountFileName, encoding='utf8') as fh:
        for line in fh:
            result, info, *ignore = meet(line, defaultPassword, minFlowWithGB, onlineDevice)
            if result or info not in ('NoUser', 'NoPassword'):
                of.write(line)
                curAmount += 1
                if resultAmount and curAmount >= resultAmount:
                    break
    os.remove(outputFile)
    os.rename(tmpFile, outputFile)


def meet(account, defaultPassword='ucas', minFlowWithGB=0, onlineDevice=0):
    """判断账号是否满足条件"""
    minFlowWithGB *= (2**30)
    account = account.strip()
    loginSuccess, info, aInfo = login(account, defaultPassword)
    msg = info
    meetCondition = False
    userInfo = None
    if loginSuccess:
        if not minFlowWithGB and not onlineDevice:
            meetCondition = True
        else:
            userInfo = getOnlineUserInfo(info)
            # d(userInfo)
            if userInfo:
                flowCheckResult = minFlowWithGB <= 0 or 'flow' in userInfo and float(
                    userInfo['flow']) >= minFlowWithGB
                onlineDeviceCheckResult = onlineDevice <= 0 or 'onlinedevice' in userInfo and int(
                    userInfo['onlinedevice']) <= onlineDevice

                if not flowCheckResult:
                    msg = "NoMeetFlow"
                elif not onlineDeviceCheckResult:
                    msg = "NoMeetOnlineDevice"
                else:
                    meetCondition = True
        logout(info)
    # d(msg)
    return meetCondition, msg, loginSuccess, userInfo


def loginWithConfileFile(configFile):
    """使用配置文件登录"""
    config = readConfig(configFile)
    if config:
        logoff()
        return login(config['userId'], config['password'])
    else:
        userId, password = askUserInfo()
        if userId and password:
            writeConfig(configFile, {'userId': userId, 'password': password})
            return login(userId, password)


def getCurrentMonthConfigFile(filePrefix):
    """获取本月的账号配置信息文件"""
    dateStr = datetime.now().strftime('%Y%m')
    return '{}.{}.config'.format(filePrefix, dateStr)


def loginWithRandom(accountFileName, defaultPassword='ucas', minFlowWithGB=0, onlineDevice=0):
    """使用配置文件中的账号随机登录"""
    logout()

    configChanged = False
    config = None
    noFlowAccounts = []
    noMeetFlowAccounts = []
    try:
        curMonthConfig = getCurrentMonthConfigFile(accountFileName)
        config = readConfig(curMonthConfig) if path.isfile(curMonthConfig) else None
        if config:
            noFlowAccounts = config.get('NoFlow', [])
            noMeetFlowAccounts = config.get(str(minFlowWithGB), [])
    except Exception as e:
        print("错误", e, '结束')

    try:
        # read all accounts
        with open(accountFileName, encoding='utf8') as fh:
            accountSet = set(fh.read().splitlines())
            accounts = list(accountSet - set(noFlowAccounts) - set(noMeetFlowAccounts))
        # d(accounts)
        modifyAccounysSet = False
        logined = []
        lResult, lMsg, aInfo = None, None, None
        while len(accounts) > 0:
            i = random.randint(0, len(accounts) - 1)
            account = accounts.pop(i)
            meetCondition, msg, loginSuccess, userInfo = meet(
                account, defaultPassword, minFlowWithGB, onlineDevice)
            if meetCondition:
                lResult, lMsg, aInfo = login(account, defaultPassword)
                break
            else:

                if loginSuccess and userInfo:
                    noMeetFlowAccounts.append(account)
                    configChanged = True
                    logined.append((account, float(userInfo['flow'])))
                    d('添加了不满足流量账号' + account)
                elif msg in ('NoUser', 'NoPassword'):
                    d("密码被修改：" + account)
                    accountSet.discard(account)
                    modifyAccounysSet = True
                elif msg == 'NoFlow':
                    configChanged = True
                    d('添加了无流量账号')
                    noFlowAccounts.append(account)
        else:
            # 没有一个满足条件的
            # 从登录成功的账号中和挑选一个登录
            d('矬子里面拔将军')
            d(logined)
            for account in noMeetFlowAccounts:
                loginSuccess, info, aInfo = login(account, defaultPassword)
                if loginSuccess:
                    userInfo = getOnlineUserInfo(info)
                    if userInfo and 'flow' in userInfo:
                        logined.append((account, float(userInfo['flow'])))
                    logout(info)
            if len(logined):
                d(logined)
                logined.sort(key=lambda x: x[1], reverse=True)
                account = logined[0][0]
                lResult, lMsg, aInfo = login(account, defaultPassword)

        # 从原文件中剔除被修改了密码的账号
        if modifyAccounysSet:
            d('有被修改了密码的存在')
            with open(accountFileName, 'w', encoding='utf8') as fh:
                for a in accountSet:
                    fh.write(a + '\n')

        # 把这个月没流量的和不满足流量要求的账号记录下来
        if configChanged:
            config = config or {}
            config['NoFlow'] = list(set(noFlowAccounts))
            config[minFlowWithGB] = list(set(noMeetFlowAccounts))
            writeConfig(curMonthConfig, config)
        return lResult, lMsg, aInfo
    except Exception as e:
        print(e)


def main():
    # 解析命令行选项
    import optparse
    parser = optparse.OptionParser()
    parser.add_option('-m', '--mode', dest='mode', default='random',
                      help='登录模式：random 随机账号登录，config 配置信息中的账号登录，filter 筛选可用的账号')
    parser.add_option('-s', '--stayon', dest='stayon',
                      action='store_true', default=False,
                      help='保持在线')
    parser.add_option('--checktime', dest='checktime',
                      type='int', default=3,
                      help='检查在线状态的时间间隔')
    parser.add_option('--accountdatafile', dest='accountdatafile',
                      default='UCASAccounts.data',
                      help='指定账号数据文件，默认是 %default')
    parser.add_option('--configfile', dest='configfile',
                      default='Config.json',
                      help='指定账号数据文件，默认是 %default')
    opts, args = parser.parse_args()

    accountDataFile = opts.accountdatafile
    configFile = opts.configfile
    mode = opts.mode.lower()

    if mode == 'random':
        result, info, aInfo = loginWithRandom(accountDataFile, minFlowWithGB=5, onlineDevice=1)
    elif mode == 'config':
        result, info, aInfo = loginWithConfileFile(configFile)
    elif mode == 'filter':
        filterUsableAccount(accountDataFile, accountDataFile)

    if mode in ('random', 'config'):
        userInfo = getOnlineUserInfo(info)
        print(userInfo)
        msg = getInfoString(userInfo) if result else ''
        title = '登陆成功' if result else '登陆失败'
        showMessage(title, msg)
        if opts.stayon:
            while(True):
                try:
                    if not isOnline():
                        result, info, *ignore = login(*aInfo)
                        d((result, info))
                    time.sleep(opts.checktime)
                except Exception as e:
                    logging.error(e)


def test():
    runApp('Login UCAS Network')

if __name__ == "__main__":
    oldCd = os.getcwd()
    os.chdir(path.dirname(path.abspath(__file__)))
    try:
        main()
    except Exception as e:
        showMessage('出错', '错误信息：' + str(e))
    os.chdir(oldCd)
