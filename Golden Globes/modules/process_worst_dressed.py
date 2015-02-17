# Processes tweets to find the best/worst dressed.
# TODO: Find a way to display pictures (URL-based?)
# Tried the above. Turns out that the media_url is not included in this JSON,
# so trying to just find most popular names instead
# This wouldn't have been great without a GUI anyway.
# TODO: Fix the Keira Knightley issue

from __future__ import division
import operator
import nltk


import regex
from util import vprint
import util
import urllib2


def run(db, target):
    vprint('Processing Worst Dressed...')
    worst = {}
    tweets = db.collection.find({'text': regex.worst_dressed})
    for tweet in tweets:
        text = tweet['text']
        tokens = nltk.word_tokenize(text)
        bg = nltk.bigrams(tokens)
        for name in bg:
            if name[0] in util.bad_names or name[1] in util.bad_names:
                continue
            if name[0][0].isupper() and name[1][0].isupper():
                if name in worst:
                    worst[name] += 1
                else:
                    worst[name] = 1
    most_popular = None
    sorted_worst = sorted(worst.items(), key=operator.itemgetter(1), reverse=True)
    for name, popularity in sorted_worst:
        if not most_popular:
            most_popular = popularity
        percent_popularity = popularity / most_popular
        if percent_popularity > 0.5:
            target.worst_dressed.append(name)
        else:
            break
    return