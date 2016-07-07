## LoginUCASNetwork

登录校园网用的小程序

## 功能

* 随机从一个账号列表中选择剩余流量充足的账号进行登录
* 使用配置文件中的账号进行登录
* 保持在线模式，也就是说每隔一段时间检查一次当前是否在线，如果不在线就登录

## 解决的一些问题

### 前辈们的馈赠

UCAS 里的校园网是不花钱的，用完了自己账号中的10G 流量之后，可以用“前辈”们的嘛。

学校会把已经离校的前辈们的校园网密码重置为 `ucas`，所以每个月可以有用不完的流量。

### 自动登录

这是学校给大家放的福利，但是每次用完了还要换账号很麻烦的！又要登录好几个账号看看还有没有流量（这是只用前辈们的账号，不改密码的好同学），或者挨个试验找能用没有被改密码的账号，然后登录浏览器记住密码账号，每次开机弹出浏览器登录。。。

本程序可以让你自动从一堆前辈们的账号中自动找还有剩余流量的账号进行登录。

### 偶尔的掉线问题

但是前辈们的账号经常会出现过一段时间自动就下线的情况。本程序有个保持在线模式，会自动检查下线情况，然后自动再次登录。就不用担心晚上电脑开机下东西会掉线啦。

## 测试环境

| 程序或库   | 版本   |
| ------ | ---- |
| Python | 3.5  |

不依赖第三方 Python 库。

## 安装

现在只提供 Python 脚本文件，过几天忙完考试我会发布 Windows 下独立的可执行文件(.exe)和 Mac 下独立的可执行文件。

## 使用说明

```shell
Usage: LoginUCASNetwork.py [options]

Options:
  -h, --help            show this help message and exit
  -m MODE, --mode=MODE  登录模式：random 随机账号登录，config 配置信息中的账号登录，filter 筛选可用的账号
  -s, --stayon          保持在线
  --checktime=CHECKTIME
                        检查在线状态的时间间隔
  --accountdatafile=ACCOUNTDATAFILE
                        指定账号数据文件，默认是 UCASAccounts.data
  --configfile=CONFIGFILE
                        指定账号数据文件，默认是 Config.json
```

## 示例

### 使用账号文件中的账号随机登录

```shell
$ python LoginUCASNetwork.py
```

上面的命令会从文件 UCASAccounts.data 中随机选择一个剩余流量充足的账号进行登录

### 使用配置文件中的账号进行登录

```shell
$ python LoginUCASNetwork.py -m config
```

上面的命令会自动用配置文件中的账号和密码进行登录。
如果没有配置文件，该操作会弹窗让你输入账号和密码。

### 保持在线模式

保持在线，也就是说每隔一段时间检查一次当前是否在线，如果不在线就登录

```shell
$ pythonw LoginUCASNetwork.py -s
```

该操作运行完不会立即退出，所以推荐用 pythonw 运行脚本。

## 账号列表的制作方法

本程序中附带了一些前辈们的账号，在此感谢前辈们的付出。

这些账号是从 UCAS 官网的通知中的奖学金公示目录中截取的。然后把它们一行一个账号存放到 UCASAccounts.data 中，然后执行下面的命令进行筛选，把密码不是`ucas`的账号剔除出去：

```shell
$ pythonw LoginUCASNetwork.py -a filter
```

## 声明

使用本程序的同学们，为了大家都能愉快的上网，请不要修改账号列表中的密码。谢谢！