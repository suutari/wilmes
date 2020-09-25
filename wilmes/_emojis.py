# -*- coding: utf-8 -*-

import re

from bs4.element import Tag

EMOJI_MAP = {
    'regular_smile': '🙂',  # smiley
    'sad_smile': '🙁',  # sad
    'wink_smile': '😉',  # wink
    'teeth_smile': '😀',  # laugh
    'confused_smile': '😕',  # frown
    'tongue_smile': '😛',  # cheeky
    'embarrassed_smile': '😳',  # blush
    'omg_smile': '😯',  # surprise
    'whatchutalkingabout_smile': '😐',  # indecision
    'angry_smile': '😡',  # angry
    'angel_smile': '😇',  # angel
    'shades_smile': '😎',  # cool
    'devil_smile': '😈',  # devil
    'cry_smile': '😢',  # crying
    'lightbulb': '💡',  # enlightened
    'thumbs_down': '👎',  # no
    'thumbs_up': '👍',  # yes
    'heart': '❤️',  # heart
    'broken_heart': '💔',  # broken heart
    'kiss': '💋',  # kiss
    'envelope': '✉️',  # mail
    'alien': '👽',  # alien
    'blink': '🤪',  # blink
    'cheerful': '😃',  # cheerful
    'dizzy': '🥴',  # dizzy
    'ermm': '🙄',  # ermm
    'getlost': '😒',  # getlost
    'ninja': '🥷',  # ninja
    'pinch': '😣',  # pinch
    'sick': '🤢',  # sick
    'sideways': '😏',  # sideways
    'silly': '🙃',  # silly
    'sleeping': '😴',  # sleeping
    'unsure': '🤔',  # unsure
    'wassat': '🤨',  # wassat
    'whistling': '😗🎵',  # whistling
    'w00t': '😲',  # w00t
}

EMOJI_IMG_SRC_RX = re.compile(r'.*/smiley/images/([^/]*).png')


def replace_emoji_imgs(element: Tag) -> None:
    for img in element.find_all('img'):
        match = EMOJI_IMG_SRC_RX.match(img.get('src', ''))
        if match:
            emoji = EMOJI_MAP.get(match.group(1))
            if emoji:
                img.replace_with(emoji)
