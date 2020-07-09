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

# Require at least 2 characters
_MINIMUM_LEN = 2
_LIST_PAGE_ENDINGS = [
    '列表',
    '对照表',
]
_LOG_EVERY = 1000

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
PATTERN_RIME_DICT_ITEM = re.compile(r'^(?P<word>\w+)\t(?P<pinyin>[a-z ]+)(\t(?P<percent>[\d]+)%)?$')


def load_luna_dict():
    single_dict = {}
    phrases_dict = {}
    with open('./luna_pinyin.dict.yaml', mode='r') as f:
        for line in f:
            match = PATTERN_RIME_DICT_ITEM.match(line)
            if match:
                groups = match.groupdict()
                word = groups['word']
                pinyin = groups['pinyin']
                percent = float(groups['percent']) if groups['percent'] is not None else 100
                if percent < 5:
                    # Exclude low frequency words
                    continue
                if len(word) == 1:
                    codePoint = ord(word)
                    if single_dict.get(codePoint) is None:
                        single_dict[codePoint] = pinyin
                    else:
                        single_dict[codePoint] = f'{single_dict[codePoint]},{pinyin}'
                else:
                    w = pinyin.split(' ')
                    if phrases_dict.get(word) is None:
                        phrases_dict[word] = [[it] for it in w]
                    elif len(phrases_dict[word]) == len(w):
                        for i in range(len(w)):
                            phrases_dict[word][i].append(w[i])
                    else:
                        logging.warn(f'invalid pinyin: {groups}')

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
    main()
