#! /usr/bin/env python3

import datetime
import os
import logging
import re
import time
import json
from logging import debug as d
import collections
from multiprocessing.dummy import Pool

import requests
from bs4 import BeautifulSoup

# logging.basicConfig(filename='UCAS.log', level=logging.DEBUG)

BeautifulSoupDefaultParser = 'lxml'

# 链接信息
LinkInfo = collections.namedtuple('LinkInfo', 'name url')
# 文件信息
FileInfo = collections.namedtuple('FileInfo', 'name url size')
# 下载任务
DownloadTask = collections.namedtuple('DownloadTask', 'url localFile')
# 作业信息
HomeworkInfo = collections.namedtuple('HomeworkInfo', 'name status openDate dueDate content attachment')


class Course:

    def __init__(self, session, courseName, courseUrl):
        self.__session = session
        self.__courseUrl = courseUrl
        self.__courseToolUrls = None
        self.__courseName = courseName
        self.__students = None
        self.__homework = None

    @property
    def session(self):
        return self.__session

    @property
    def name(self):
        return self.__courseName

    @property
    def url(self):
        return self.__courseUrl

    @property
    def courseToolUrls(self):
        """获取课程的工具链接"""
        if not self.__courseToolUrls:
            self.__courseToolUrls = UCAS.getToolListUrls(self.session, self.session.get(self.url).text)
        return self.__courseToolUrls

    @property
    def resourceList(self):
        """获取课件列表"""
        courseId = self.url.split('/')[-1]
        resUrl = "http://course.ucas.ac.cn/access/content/group/{0}/".format(courseId)
        return self.__getCourseResourceList(resUrl, directory=self.name)

    @property
    def students(self):
        """获取所有上课学生"""
        if not self.__students:
            url = self.courseToolUrls['应用统计']
            html = self.session.get(url).text
            table = BeautifulSoup(html, BeautifulSoupDefaultParser)('table')[1]

            rList = []
            for row in table('tr'):
                tds = row('td')
                if len(tds):
                    rList.append((tds[1].text.strip(), tds[2].text.strip()))
            self.__students = rList
        return self.__students

    @property
    def homework(self):
        if not self.__homework:
            url = self.courseToolUrls['课堂作业']
            html = self.session.get(url).text
            table = BeautifulSoup(html, BeautifulSoupDefaultParser).table

            rList = []
            if table:
                for row in table('tr'):
                    tds = row('td')
                    if len(tds):
                        status = tds[2].text.strip()
                        openDate = tds[3].text.strip()
                        dueDate = tds[4].text.strip()
                        url = tds[1].a['href']
                        detail = BeautifulSoup(self.session.get(url).text, BeautifulSoupDefaultParser)
                        name = detail.find('table').td.text.strip()
                        content = detail.find('div', class_='textPanel')
                        content = content and content.text.strip()
                        attachments = detail.find(class_='attachList') if '作业的附加资源' in detail.text else None
                        attachments = attachments and [FileInfo(
                            name=self.handleFileName(e.text.strip(), e['href']),
                            url=e['href'],
                            size=int(self.session.head(e['href']).headers.get('Content-Length'))
                        ) for e in attachments('a')]

                        rList.append(HomeworkInfo(name=name, status=status, openDate=openDate, dueDate=dueDate,
                                                  content=content, attachment=attachments))
            self.__homework = rList
        return self.__homework

    @staticmethod
    def handleFileName(name, url):
        """处理文件名"""
        s = name
        if not name:
            name = os.path.split(url)[1]
        s = s.replace(':', '：')
        s = s.replace('?', '？')
        s = s.replace('*', '_')
        s = s.replace('"', "'")
        s = s.replace(':', '：')
        s = s.replace('<', '(')
        s = s.replace('>', ')')
        s = s.replace('|', '_')
        s = s.replace('/', '_')
        s = s.replace('\\', '_')
        urlExt = os.path.splitext(url)[1]
        fileExt = os.path.splitext(name)[1]
        if urlExt and urlExt != fileExt:
            s += urlExt
        return s

    def __getCourseResourceList(self, resUrl, directory=None):
        """获取课件列表

        args:
            resUrl:
                eg:
                    http://course.ucas.ac.cn/access/content/group/117418/
                    http://course.ucas.ac.cn/access/content/group/117418/%E8%AF%BE%E4%BB%B6/
        """

        # 列表第一项为当前目录名
        fileList = [directory if directory else resUrl.split('/')[-1]]

        html = self.session.get(resUrl).text
        table = BeautifulSoup(html, BeautifulSoupDefaultParser).table

        # 处理单个文件
        resList = [LinkInfo(name=e.text.strip(), url=e['href']) for e in table('a') if not e['href'].endswith('/')]

        # resList = list(set(resList))
        files = []
        for m in resList:
            url = resUrl + m.url
            r = self.session.head(url)
            size = r.headers.get('Content-Length')
            # 过滤文件名中的特殊字符： '\/:*?",.|'
            name = self.handleFileName(m.name, m.url)
            files.append(FileInfo(name=name, url=url, size=int(size)))

        fileList += files

        # resList = [x[:-1] if x.endswith(";") else x for x in resList]
        # d(resList)

        # 处理文件夹
        folderList = [LinkInfo(name=e.text.strip(), url=e['href']) for e in table('a') if e['href'].endswith('/')]

        # 删除 ..
        folderList = [x for x in folderList if not x.url.startswith("..")]

        for folder in folderList:
            fl = self.__getCourseResourceList(resUrl + folder.url, directory=folder.name)
            fileList.append(fl)
        return fileList

    def __walk(self, fileList, root=None):
        """遍历文件列表，使用方法同 os.walk()"""
        dirName = fileList[0]
        root = os.path.join(root, dirName) if root else dirName
        files = []
        dirs = []
        for f in fileList[1:]:
            if not isinstance(f, list):
                files.append(f)
            else:
                dirs.append(f)
        yield (root, dirs, files)
        for d in dirs:
            yield next(self.__walk(d, root))

    def getSyncResourceList(self, localDir, blackList=None):
        """获取需要同步的课件列表"""
        fileList = self.resourceList
        rList = []
        for root, dirs, files in self.__walk(fileList):
            root = os.path.join(localDir, root)
            for file in files:
                localFile = os.path.join(root, file.name)
                if not os.path.isfile(localFile) or os.path.getsize(localFile) != file.size:
                    rList.append(DownloadTask(url=file.url, localFile=localFile))
        if blackList:
            blackList = list(map(re.compile, blackList))
            rList = [x for x in rList if all([not b.search(os.path.split(x.localFile)[1]) for b in blackList])]

        return rList

    @staticmethod
    def getSyncResourceListOfCourses(courses, localDir, resourceBlackList=None, threadCount=4):
        """获取课程列表的同步课件列表"""
        pool = Pool(threadCount)
        rList = pool.map(lambda c: (c.name, c.getSyncResourceList(localDir, resourceBlackList)),
                         courses)
        pool.close()
        pool.join()

        rList = list(filter(lambda m: m[1], rList))
        return rList

    def getMatchedStudents(self, idPattern=None, namePattern=None):
        """获取匹配学号模式和姓名模式的学生"""
        idPattern = idPattern and re.compile(idPattern)
        namePattern = namePattern and re.compile(namePattern)
        return [s for s in self.students if (not idPattern or idPattern.search(s[0])) and
                (not namePattern or namePattern.search(s[1]))]


class UCAS:

    def __init__(self):
        self.__session = requests.Session()
        # 课程网站 工具链接
        self.__courseSiteToolListUrls = None
        self.__courses = None
        self.__userInfo = None

    def login(self, username, password):
        """登录UCAS"""

        hostUrl = 'http://sep.ucas.ac.cn'
        loginUrl = 'http://sep.ucas.ac.cn/slogin'

        self.session.get(hostUrl)
        data = {'userName': username,
                'pwd': password,
                'sb': 'sb'}
        result = self.session.post(loginUrl, data=data)
        rr = BeautifulSoup(result.text, BeautifulSoupDefaultParser).find('div', class_='alert alert-error')
        return (False, rr.text) if rr else (True, None)

    @property
    def session(self):
        return self.__session

    @property
    def userInfo(self):
        if not self.__userInfo:

            url = self.courseSiteToolListUrls['我的信息']
            html = self.session.get(url).text
            pattern = re.compile(r'当前登录用户：([^(]+)\((\d+)\)')
            matched = pattern.search(html)
            self.__userInfo = (matched.group(1), matched.group(2))
        return self.__userInfo

    @property
    def courseSiteToolListUrls(self):
        if not self.__courseSiteToolListUrls:
            self.__courseSiteToolListUrls = self.__getCourseSiteToolListUrls()
        return self.__courseSiteToolListUrls

    @property
    def courses(self):
        if not self.__courses:
            self.__courses = [Course(self.session, c.name, c.url) for c in self.__getCourseListUrls()]
        return self.__courses

    @staticmethod
    def getIFrameRealSrc(session, url):
        """获取 iframe 标签的真实地址"""
        try:
            html = session.get(url).text
            url = BeautifulSoup(html, BeautifulSoupDefaultParser).iframe['src']
        except:
            pass
        return url

    @staticmethod
    def getToolListUrls(session, html):
        """获取网站左边的那个工具栏中的工具"""

        aList = BeautifulSoup(html, BeautifulSoupDefaultParser)('a', class_=re.compile('icon-sakai-.+'))
        rToolList = {entry.text.strip(): UCAS.getIFrameRealSrc(session, entry['href']) for entry in aList}
        return rToolList

    def __getCourseSiteToolListUrls(self):
        """获取"课程网站"的工具链接"""

        baseUrl = "http://course.ucas.ac.cn"
        courseIdentityUrl = 'http://sep.ucas.ac.cn/portal/site/16/801'

        html = self.session.get(courseIdentityUrl).text
        r = BeautifulSoup(html, BeautifulSoupDefaultParser).find('a', href=re.compile('Identity='))['href']
        html = self.session.get(r).text
        r = BeautifulSoup(html, BeautifulSoupDefaultParser).find('frame', title='mainFrame')['src']
        url = baseUrl + r
        html = self.session.get(url).text
        toolList = UCAS.getToolListUrls(self.session, html)
        toolList['我的信息'] = baseUrl + UCAS.getIFrameRealSrc(self.session, BeautifulSoup(html, BeautifulSoupDefaultParser).find('iframe', title='我的空间信息 ')['src'])
        return toolList

    def __getCourseListUrls(self):
        """获取所有课程链接"""
        # myCourseUrl = self.courseSiteToolListUrls[0]
        myCourseUrl = self.courseSiteToolListUrls['我的课程']
        html = self.session.get(myCourseUrl).text
        return [LinkInfo(name=e.text.strip(), url=e['href']) for e in
                BeautifulSoup(html, BeautifulSoupDefaultParser).table('a', href=re.compile(r'http://course.ucas.ac.cn/portal/site/\d+'))]

    def getMatchedCourses(self, *namePatterns):
        """获取匹配条件的课程"""
        namePatterns = list(map(re.compile, namePatterns))
        return [course for course in self.courses
                if any(map(lambda namePattern:namePattern.search(course.name), namePatterns))]

    def getCoursesOfCurrentTerm(self):
        """智能同步该学期所有课程课件"""
        now = datetime.datetime.now()
        month = now.month
        curYear = str(now.year % 2000)
        curSeason = '秋季' if 9 <= month <= 12 or 1 <= month <= 2 else '[春夏]季'
        namePattern = r'%s[-\d{2}]?%s' % (curYear, curSeason)
        return self.getMatchedCourses(namePattern)


def download(session, downloadTask, reportProgress=None):
    """下载文件"""

    # 检查目录是否存在
    directory = os.path.split(downloadTask.localFile)[0]
    if not os.path.isdir(directory):
        try:
            os.makedirs(directory)
        except:
            pass

    with session.get(downloadTask.url, stream=True).raw as infh, open(downloadTask.localFile, 'wb') as outfh:
        try:
            fileSize = int(infh.headers.get('Content-Length'))
        except:
            fileSize = 0
        hasRead = 0
        bufferSize = 102400
        curTime = time.time()
        while True:
            content = infh.read(bufferSize)
            outfh.write(content)
            if reportProgress:
                lContent = len(content)
                hasRead += lContent
                nct = time.time()
                speed = lContent / (nct - curTime + 0.0001)
                # cutTime=nct
                reportProgress(downloadTask.localFile, fileSize, hasRead, speed)
            if not content:
                break


def downloadAll(session, downloadTasks, reportProgress=None, threadCount=4):
    """多线程下载文件"""
    ds = []
    for m in downloadTasks:
        ds += m[1]

    pool = Pool(threadCount)
    pool.map(lambda dd: download(session, dd, reportProgress), ds)
    pool.close()
    pool.join()


def reportDownloadProgress(localFile, fileSize, hasRead, speed):
    """用于输出下载信息的函数"""
    print('{}({}%): {}KB/{}KB {}KB/s'.format(os.path.split(localFile)[1],
                                             int(hasRead / fileSize * 100), int(hasRead / 1024), int(fileSize / 1024),
                                             int(speed / 1024)))


def main():

    # 解析命令行选项
    import optparse
    usage = "usage: %prog [options] courseNamePattern1 courseNamePattern2 ..."
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-a', '--action', dest='action', default='sync',
                      help='指定进行的操作。sync:同步课件;\nstudent:学生列表\nhomework:作业信息')
    parser.add_option('-y', '--yes', action='store_true', default=False, dest='yes',
                      help='对所有询问回答"是"')
    parser.add_option('-d', '--dir', dest='dir', default=None,
                      help='指定课件存放的目录')
    parser.add_option('-b', '--blacklist', dest='blacklist', default=None,
                      help='指定不进行同步的课件黑名单, 可使用正则表达式指定(如"\.mp4"指定不下载视频)')
    parser.add_option('-c', '--classmate', dest='classmate', action='store_true', default=False,
                      help='只显示同班同学的学生列表')

    opts, args = parser.parse_args()  # (['-d', '/Volumes/Buffer/Course/Sync', '自然语言处理', '夏季'])

    # print(opts)

    # 读配置文件
    configFile = os.path.splitext(__file__)[0] + '.config'
    if os.path.isfile(configFile):
        with open(configFile) as fh:
            data = fh.read()
            config = json.loads(data)
    else:
        raise NoConfigFileException
    username, password = config['username'], config['password']
    syncDir = opts.dir or config.get('dir', None) or '.'

    # work
    ucas = UCAS()
    r, error = ucas.login(username, password)
    if not r:
        raise Exception(error)
    courseList = ucas.getMatchedCourses(*args) if len(args) > 0 else ucas.getCoursesOfCurrentTerm()
    if opts.action == 'sync':
        downloadList = Course.getSyncResourceListOfCourses(courseList, syncDir,
                                                           opts.blacklist.splits() if opts.blacklist else None)
        if len(downloadList) > 0:
            print('需要下载的资源列表如下：')
            for c, rs in downloadList:
                print('课程: %s' % (c,))
                for r in rs:
                    print(r.localFile)

            if not opts.yes:
                i = input('是否下载? (y/n)')
                if i.lower() != 'y':
                    return

            print('开始下载...')
            downloadAll(ucas.session, downloadList, reportDownloadProgress)
        print('同步完成')

    elif opts.action == 'student':
        for c in courseList:
            print('课程: %s' % (c.name,))

            if not opts.classmate:
                ss = c.students
            else:
                userId = ucas.userInfo[1]
                patterned = ''.join((userId[0:4], '[2e]', userId[5:12]))
                ss = c.getMatchedStudents(patterned)
            print(*ss, sep='\n')

    elif opts.action == 'homework':
        for c in courseList:
            print('课程: %s' % (c.name,))
            ss = c.homework
            print(*ss)


class NoConfigFileException(Exception):
    def __str__(self):
        return '配置文件不存在！'


def test():
    ucas = UCAS()
    r, error = ucas.login('chendacai@qq.com', 'wenWEN6813')
    c = ucas.getMatchedCourses('图像处理')[0]
    ss = c.getMatchedStudents('2015[e2]80133', '陈')

    ss = ucas.userInfo
    # ss = c.homework
    from pprint import pprint as pp
    pp(ss)

if __name__ == '__main__':

    main()
    # test()
