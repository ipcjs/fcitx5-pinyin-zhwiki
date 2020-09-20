#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Usage:
#   convert.py input_filename
# input_filename is a file of Wikipedia article titles, one title per line.

import logging
import re
import sys

import opencc
from pypinyin import lazy_pinyin, pinyin, Style, load_single_dict, load_phrases_dict
from pypinyin.core import PHRASES_DICT, PINYIN_DICT
# Require at least 3 characters
_MINIMUM_LEN = 3
_LIST_PAGE_ENDINGS = [
    '列表',
    '对照表',
]
_LOG_EVERY = 100000

_PINYIN_SEPARATOR = '\''
_HANZI_RE = re.compile('^[\u4e00-\u9fa5]+$')
_TO_SIMPLIFIED_CHINESE = opencc.OpenCC('t2s.json')

logging.basicConfig(level=logging.INFO)


def is_good_title(title, previous_title=None):
    if not _HANZI_RE.match(title):
        return False

    # Skip single character & too long pages
    if len(title) < _MINIMUM_LEN:
        return False

    # Skip list pages
    if title.endswith(tuple(_LIST_PAGE_ENDINGS)):
        return False

    if previous_title and \
            len(previous_title) >= 4 and \
            title.startswith(previous_title):
        return False

    return True


def log_count(count):
    logging.info(f'{count} words generated')


def process(convert_title, title_to_lines):
    previous_title = None
    result_count = 0
    with open(sys.argv[1]) as f:
        for line in f:
            title = convert_title(line.strip())
            if is_good_title(title, previous_title):
                line = title_to_lines(title)
                if line is not None:
                    print(line)
                result_count += 1
                if result_count % _LOG_EVERY == 0:
                    log_count(result_count)
                previous_title = title
    log_count(result_count)


def flat_phrases(phrases):
    """
    @see https://zhuanlan.zhihu.com/p/66930500
    """
    lines = []

    def process(arr, index=0):
        if index >= len(phrases):
            lines.append(arr.copy())
            return
        for it in phrases[index]:
            arr.append(it)
            process(arr, index+1)
            arr.pop()

    process([])
    return [' '.join(line) for line in lines]


def main():
    if sys.argv[2] == '--rime':
        load_luna_dict()

        def title_to_lines(title):
            phrases = pinyin(title, style=Style.NORMAL, heteronym=True)
            return '\n'.join((f'{title}\t{phrase}' for phrase in flat_phrases(phrases)))

        process(
            convert_title=lambda it: it,
            title_to_lines=title_to_lines
        )
    else:
        def title_to_lines(title):
            pinyin = _PINYIN_SEPARATOR.join(lazy_pinyin(title))
            if pinyin == title:
                logging.info(
                    f'Failed to convert to Pinyin. Ignoring: {pinyin}')
                return None
            return '\t'.join([title, pinyin, '0'])
        process(
            convert_title=lambda it: _TO_SIMPLIFIED_CHINESE.convert(it),
            title_to_lines=title_to_lines
        )


# example:
# 於	wu	0%
PATTERN_RIME_DICT_ITEM = re.compile(r'^(?P<word>\w+)\t(?P<pinyin>[a-z ]+)(\t(?P<percent>[\d.]+)%)?$')


class Dict(dict):
    def __setattr__(self, key, value):
        self[key] = value

    def __getattr__(self, key):
        return self[key]


def load_luna_dict():
    single_dict = {}
    phrases_dict = {}
    # 朙月拼音是专为繁体字设计的字典, 里面的简体字被看成"被大陸簡化字借用字形的傳承字"标注的是"古音"
    # 直接用来处理带简体字的zhwiki效果惨不忍睹(-_-#), 这里使用opencc尝试规避该问题
    luna_dict = {}
    luna_dict_simple = {}
    with open('./rime-luna-pinyin/luna_pinyin.dict.yaml', mode='r') as f:
        for line in f:
            match = PATTERN_RIME_DICT_ITEM.match(line)
            if match:
                item = Dict(match.groupdict())
                # item中的words字段进用来debug时追踪item的来源
                word = item['word']
                item.pop('word')
                item.words = word
                item.percent = float(item.percent) if item.percent is not None else 100

                if luna_dict.get(word) is None:
                    luna_dict[word] = [item]
                else:
                    # 多音字
                    luna_dict[word].append(item)

                word_simple = _TO_SIMPLIFIED_CHINESE.convert(word)
                if word != word_simple:
                    item_simple = Dict(item)
                    if luna_dict_simple.get(word_simple) is None:
                        luna_dict_simple[word_simple] = [item_simple]
                    else:
                        # 多繁转一简后同音的情况, 此时应该将词频累加
                        for exist_item in luna_dict_simple[word_simple]:
                            if exist_item.pinyin == item_simple.pinyin:
                                exist_item.percent += item_simple.percent
                                exist_item.words += item_simple.words
                                # logging.info(f'exist_item: {exist_item}')
                                break
                        else:
                            luna_dict_simple[word_simple].append(item_simple)
    # 使用简体字的注音覆盖繁体字的注音, 则那些"被大陸簡化字借用字形的傳承字"的注音大多会被覆盖掉...
    luna_dict.update(luna_dict_simple)
    for (word, items) in luna_dict.items():
        for item in items:
            if item.percent < 5:
                # 排除低频词
                continue
            if len(word) == 1:
                codePoint = ord(word)
                if single_dict.get(codePoint) is None:
                    single_dict[codePoint] = item.pinyin
                else:
                    single_dict[codePoint] = f'{single_dict[codePoint]},{item.pinyin}'
            else:
                w = item.pinyin.split(' ')
                if phrases_dict.get(word) is None:
                    phrases_dict[word] = [[it] for it in w]
                elif len(phrases_dict[word]) == len(w):
                    for i in range(len(w)):
                        phrases_dict[word][i].append(w[i])
                else:
                    logging.warn(f'invalid pinyin: {word} -> {item}')

    # 移除内置单字词典的多音字
    for (word, pinyins) in PINYIN_DICT.items():
        pinyin_list = pinyins.split(',')
        if len(pinyin_list) > 1:
            PINYIN_DICT[word] = pinyin_list[0]
    # 移除内置词组的多音字
    for (word, phrases) in PHRASES_DICT.items():
        for p in phrases:
            while(len(p) > 1):
                p.pop()
    # 加载luna词典
    load_single_dict(single_dict)
    load_phrases_dict(phrases_dict)


def test_load_luna_dict():
    load_luna_dict()
    print(lazy_pinyin('長月達平'))
    print(pinyin('長月達平', style=Style.NORMAL, heteronym=True))


def test_flat_phrases():
    print(flat_phrases([
        ['a', 'b', 'c'],
        ['1', '2', '3'],
        ['fuck', 'you'],
    ]))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main()
    else:
        test_load_luna_dict()
