# -*- coding: utf-8 -*-
# reference: https://github.com/jwlin/ptt-web-crawler/tree/master/PttWebCrawler

# self: the instance of the class in which the method is being executed

from __future__ import absolute_import
from __future__ import print_function

import os
import re
import sys
import json
import requests
import argparse
import time
import codecs
from bs4 import BeautifulSoup
from six import u

__version__ = '1.0'

# if python 2, disable verify flag in requests.get()
VERIFY = True
if sys.version_info[0] < 3:
    VERIFY = False
    requests.packages.urllib3.disable_warnings()


class PttWebCrawler(object):
    # inherits from object
    # In Python 3, inheriting from object is not necessary since it's the default behavior

    PTT_URL = 'https://www.ptt.cc'
    # class-level constant

    """docstring for PttWebCrawler"""  
    # print(PttWebCrawler.__doc__)

    def __init__(self, cmdline=None, as_lib=False):
        """docstring for __inti__"""
        # print(PttWebCrawler.__init__.__doc__)

        parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='''
            A crawler for the web version of PTT, the largest online community in Taiwan.
            Input: board name and page indices (or articla ID)
            Output: BOARD_NAME-START_INDEX-END_INDEX.json (or BOARD_NAME-ID.json)
        ''')
        # ArgumentParser: responsible for handling the parsing of command-line arguments
        # RawDescriptionHelpFormatter: allows the use of raw formatting for the description, 
        #                              meaning that newlines and whitespace in the description string will be preserved when printed. 
        #                              Without this, the description would be automatically reformatted, 
        #                              potentially losing custom indentation or formatting

        parser.add_argument('-b', metavar='BOARD_NAME', help='Board name', required=True)
        # -b: defines the short option for the command-line argument
        # metavar: displayed in the help message when users run the script with the -h or --help flag, 
        #          e.g., -b BOARD_NAME   Board name

        group = parser.add_mutually_exclusive_group(required=True)
        #  mutually exclusive: user can only provide one of these options at a time
        # user must choose at least one of the mutually exclusive options
        
        group.add_argument('-i', metavar=('START_INDEX', 'END_INDEX'), type=int, nargs=2, help="Start and end index")
        # the argument -i takes two integer values (START_INDEX and END_INDEX)

        group.add_argument('-a', metavar='ARTICLE_ID', help="Article ID")
        parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)
        # action='version':  tells argparse to print the version information and exit
        # %(prog)s: program name

        if not as_lib:
            # as_lib: a flag that determines whether the script is being used as a standalone script 
            #         or as a library/module

            if cmdline:
                args = parser.parse_args(cmdline)
                # if cmdline is provided, the script will use it to parse the arguments
            else:
                args = parser.parse_args()
                # use the system's command-line input (sys.argv)
                
            board = args.b
            # board name or some other entity (possibly passed with a -b argument

            if args.i:
                # passed via the -i argument (2 integers: start and end)

                start = args.i[0]
                if args.i[1] == -1:
                    # e.g., python script.py -b example_board -i 1 -1
                    #       start from index 1 and go to the last page
                    end = self.getLastPage(board)
                else:
                    end = args.i[1]
                self.parse_articles(start, end, board)

            else:  # args.a: represents an article ID (likely passed via the -a argument)
                article_id = args.a
                self.parse_article(article_id, board)

    def parse_articles(self, start, end, board, path='.', timeout=3):
            filename = board + '-' + str(start) + '-' + str(end) + '.json'
            filename = os.path.join(path, filename)
            self.store(filename, u'{"articles": [', 'w')
            # u: Unicode string
            #    (denoted by the u prefix in Python 2.x, but it's not necessary in Python 3.x, where all strings are Unicode by default)
            # {"articles": [: JSON-like structure

            for i in range(end-start+1):
                index = start + i
                print('Processing index:', str(index))
                resp = requests.get(
                    url = self.PTT_URL + '/bbs/' + board + '/index' + str(index) + '.html',
                    cookies={'over18': '1'}, verify=VERIFY, timeout=timeout
                )
                if resp.status_code != 200:
                    print('invalid url:', resp.url)
                    continue
                soup = BeautifulSoup(resp.text, 'html.parser')
                # resp.text: raw HTML content retrieved from an HTTP request

                divs = soup.find_all("div", "r-ent")
                # finds all <div> elements in the parsed HTML that have the class r-ent
                # r-ent class: a website-defined class and not a standard HTML element

                for div in divs:
                    try:
                        # ex. link would be <a href="/bbs/PublicServan/M.1127742013.A.240.html">Re: [問題] 職等</a>
                        href = div.find('a')['href']
                        link = self.PTT_URL + href
                        article_id = re.sub('\.html', '', href.split('/')[-1])
                        # re (pyhton's regular expressions): extract and process the article ID from a URL
                        # href.split('/'): returns a list of segments in the URL
                        # href: "https://example.com/articles/article1.html"
                        # href.split('/'): ['https:', '', 'example.com', 'articles', 'article1.html']
                        # href.split('/')[-1]: "article1.html"

                        if div == divs[-1] and i == end-start:  # last div of last page
                            self.store(filename, self.parse(link, article_id, board), 'a')
                        else:
                            self.store(filename, self.parse(link, article_id, board) + ',\n', 'a')
                            # a: file should be opened in "append" mode
                    except:
                        pass
                time.sleep(0.1)
            self.store(filename, u']}', 'a')
            return filename

    def parse_article(self, article_id, board, path='.'):
        link = self.PTT_URL + '/bbs/' + board + '/' + article_id + '.html'
        filename = board + '-' + article_id + '.json'
        filename = os.path.join(path, filename)
        self.store(filename, self.parse(link, article_id, board), 'w')
        return filename

    @staticmethod
    # a method does not depend on the instance of the class in which it is defined
    # doesn't receive the self parameter and can't access the instance or class attributes unless they're passed explicitly
    # could be called 
    #   1. via class: MyClass.static_method()
    #   2. via instance: instance = MyClass() instance.static_method()
    # 
    # a non-staticmethod could only be called via instance           
    # 
    def parse(link, article_id, board, timeout=3):
        print('Processing article:', article_id)
        resp = requests.get(url=link, cookies={'over18': '1'}, verify=VERIFY, timeout=timeout)
        # get raw html data (what written in .html)
        
        if resp.status_code != 200:
            print('invalid url:', resp.url)
            return json.dumps({"error": "invalid url"}, sort_keys=True, ensure_ascii=False)
        soup = BeautifulSoup(resp.text, 'html.parser')
        main_content = soup.find(id="main-content")
        metas = main_content.select('div.article-metaline')
        author = ''
        title = ''
        date = ''
        if metas:
            author = metas[0].select('span.article-meta-value')[0].string if metas[0].select('span.article-meta-value')[0] else author
            # selects the first <span> element with the class article-meta-value
            title = metas[1].select('span.article-meta-value')[0].string if metas[1].select('span.article-meta-value')[0] else title
            date = metas[2].select('span.article-meta-value')[0].string if metas[2].select('span.article-meta-value')[0] else date

            # remove meta nodes
            for meta in metas:
                meta.extract()
            for meta in main_content.select('div.article-metaline-right'):
                meta.extract()

        # remove and keep push nodes
        pushes = main_content.find_all('div', class_='push')
        for push in pushes:
            push.extract()
        # remove an element from the parse tree. in this case, remove push from main_content
        # re.compile(): compiles the pattern u'※ 發信站:' into a regular expression object. 
        #               this allows for more flexible matching 
        #               e.g., handle slight variations in the string like extra spaces
        #               f the string contains additional characters (e.g., "※ 發信站: IP address info"), it would still find the match

        try:
            ip = main_content.find(string=re.compile(u'※ 發信站:'))
            # Python 2: strings were by default byte strings, and the u prefix was used to indicate a Unicode string
            # Python 3: strings are Unicode by default, so the u prefix is no longer necessary

            ip = re.search('[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*', ip).group()
            # [0-9]*: matches any sequence of digits
        
        except:
            ip = "None"

        # 移除 '※ 發信站:' (starts with u'\u203b'), '◆ From:' (starts with u'\u25c6'), 空行及多餘空白
        # 保留英數字, 中文及中文標點, 網址, 部分特殊符號
        filtered = [ v for v in main_content.stripped_strings if v[0] not in [u'※', u'◆'] and v[:2] not in [u'--'] ]
        # stripped_strings: an iterator that yields the text of the elements in main_content, with leading and trailing whitespace removed
        # v[:2]: the first 2 characters

        expr = re.compile(u(r'[^\u4e00-\u9fa5\u3002\uff1b\uff0c\uff1a\u201c\u201d\uff08\uff09\u3001\uff1f\u300a\u300b\s\w:/-_.?~%()]'))
        # r: raw data
        # ^: match any character
        # \u4e00-\u9fa5: represents the range of Chinese characters
        # \u3002: 。
        # \uff1b: ；
        # \uff1a: :
        # \u201c\u201d: ""
        # \uff08\uff09: ，
        # \u3001:、
        # \uff1f: ?
        # \u300a\u300b: 《》
        # \s: any whitespace character.
        # \w: any word character (letters, digits, or underscores).
        # :/\-_.?~%(): These are literal characters that you want to allow (e.g., :, /, -, _, ., ?, ~, %, ()).
        
        for i in range(len(filtered)):
            filtered[i] = re.sub(expr, '', filtered[i])
            # search expr for filtered[i] and each expr matching filtered[i] will be replaced w/ ''

        filtered = [_f for _f in filtered if _f]  # remove empty strings
        filtered = [x for x in filtered if article_id not in x]  # remove last line containing the url of the article
        content = ' '.join(filtered)
        content = re.sub(r'(\s)+', ' ', content)
        # (\s)+: matches any whitespace character (spaces, tabs, newlines)

        # push messages
        p, b, n = 0, 0, 0
        messages = []
        for push in pushes:
            if not push.find('span', 'push-tag'):
                continue
            push_tag = push.find('span', 'push-tag').string.strip(' \t\n\r')
            push_userid = push.find('span', 'push-userid').string.strip(' \t\n\r')
            # if find is None: find().strings -> list -> ' '.join; else the current way
            push_content = push.find('span', 'push-content').strings
            push_content = ' '.join(push_content)[1:].strip(' \t\n\r')  # remove ':'
            push_ipdatetime = push.find('span', 'push-ipdatetime').string.strip(' \t\n\r')
            messages.append( {'push_tag': push_tag, 'push_userid': push_userid, 'push_content': push_content, 'push_ipdatetime': push_ipdatetime} )
            if push_tag == u'推':
                p += 1
            elif push_tag == u'噓':
                b += 1
            else:
                n += 1

        # count: 推噓文相抵後的數量; all: 推文總數
        message_count = {'all': p+b+n, 'count': p-b, 'push': p, 'boo': b, "neutral": n}

        # print 'msgs', messages
        # print 'mscounts', message_count

        # json data
        data = {
            'url': link,
            'board': board,
            'article_id': article_id,
            'article_title': title,
            'author': author,
            'date': date,
            'content': content,
            'ip': ip,
            'message_count': message_count,
            'messages': messages
        }
        # print 'original:', d
        return json.dumps(data, sort_keys=True, ensure_ascii=False)

    @staticmethod
    def getLastPage(board, timeout=3):
        content = requests.get(
            url= 'https://www.ptt.cc/bbs/' + board + '/index.html',
            cookies={'over18': '1'}, timeout=timeout
        ).content.decode('utf-8')
        first_page = re.search(r'href="/bbs/' + board + '/index(\d+).html">&lsaquo;', content)
        if first_page is None:
            return 1
        return int(first_page.group(1)) + 1

    @staticmethod
    def store(filename, data, mode):
        with codecs.open(filename, mode, encoding='utf-8') as f:
            f.write(data)

    @staticmethod
    def get(filename, mode='r'):
        with codecs.open(filename, mode, encoding='utf-8') as f:
            return json.load(f)

if __name__ == '__main__':
    c = PttWebCrawler()