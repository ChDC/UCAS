# UCASCourse

和 UCAS 教务操作相关的程序

## 功能

* 同步课件
  * 支持指定模糊课程名
  * 支持同步单独某个课程或者满足条件的某个课程
  * 默认智能同步本学期（秋季、春季、夏季）的课程
  * 支持课件黑名单，如指定不同步 mp4 文件
* 查看和你一起上课的学生名单
  * 可以只显示和你一个班的同学
* 查看作业
  * 显示课程的作业列表
  * 下载作业中的附件

## 解决的一些问题

###  同步课件

### 课件名错乱问题

比如你在浏览器中看到的课件名字是“附件16：课程总结”，下载下来的文件名却是“NLP-Summary.pdf”。

本程序会自动把课件名改为正确的名字。也就是将课件名字改为“附件16：课程总结.pdf”。

### 课件的指纹标记

本程序使用课件的大小和文件名作为文件的指纹标记对教务和本地的文件进行比较。

这样确保了如果老师修改了课件的内容也能同步成功。

### 查看和你上同一个课的同班同学

老师布置的大作业需要组队的时候可以用该功能看看你班里谁也选了这课。

或者你没去上课想问问班里同学老师布置没布置作业等。

## 测试环境

| 程序或库          | 版本    |
| ------------- | ----- |
| Python        | 3.5   |
| BeautifulSoup | 4.4.1 |
| requests      | 2.9.1 |

## 安装

现在只提供 Python 脚本文件，过几天忙完考试我会发布 Windows 下独立的可执行文件(.exe)和 Mac 下独立的可执行文件。

## 使用说明

```shell
Usage: UCASCourse.py [options] courseNamePattern1 courseNamePattern2 ...

Options:
  -h, --help            show this help message and exit
  -a ACTION, --action=ACTION
                        指定进行的操作。sync:同步课件; student:学生列表 homework:作业信息
  -y, --yes             对所有询问回答"是"
  -d DIR, --dir=DIR     指定课件存放的目录
  -b BLACKLIST, --blacklist=BLACKLIST
                        指定不进行同步的课件黑名单, 可使用正则表达式指定(如"\.mp4"指定不下载视频)
  -c, --classmate       只显示同班同学的学生列表
```

## 示例

### 同步课件

#### 一次同步一个课程

```shell
$ python UCASCourse.py -d F:\Sync 自然语言
```

上面的命令会同步课程“自然语言处理”（假如你选了这课）的课件并下载到`F:\Sync`中。

它会将教务上的课件与目录`F:\Sync` 中存在的课件一一进行对比，只下载教务中新添加的课件。

#### 一次同步多个课程

```shell
$ python UCASCourse.py -d F:\Sync 自然语言 软件工程 分布式
```

上面的名字会同步三个课程：自然语言处理、高级软件工程、分布式计算。

#### 一次同步一个学期的课程

```shell
$ python UCASCourse.py -d F:\Sync
```

#### 一次同步指定学期的课程

```shell
$ python UCASCourse.py -d F:\Sync 秋季
```

#### 一次同步一年的课程

```shell
$ python UCASCourse.py -d F:\Sync 2016
```

#### 课件黑名单

```shell
$ python UCASCourse.py -d F:\Sync 2016 -b '\.mp4'
```

### 查看和你一起上课的学生名单

#### 显示所有学生名单

```shell
$ python UCASCourse.py -a student 软件工程
```

#### 只显示和你一个班的同学

```shell
$ python UCASCourse.py -a student -c 软件工程 自然语言
```

###  查看作业

```shell
$ python UCASCourse.py -a homework -c 软件工程 自然语言
```
