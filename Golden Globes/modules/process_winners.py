# Processes tweets to find the winners
# TODO: Write a function that takes our bins and collapses them by looking up twitter handles, hashtags, etc
# TODO: Write a function that tales the collapsed bins and uses statistical analysis to find the real winners
    # TODO: (possibly using hamming distance)


import datetime
from dateutil import tz
import twitter

import regex
from util import vprint
import util


def run(db, target, event):
    event.wait()  # Wait for start_time to be set
    vprint('Received start time. Finding winners...')
    raw_winners = read_winners(db, target)
    vprint('Processing winners...')
    processed_winners = consolidate_winners(raw_winners)
    vprint('Sorting winners...')
    sorted_winners = sorted(processed_winners.items(), key=sort_winners, reverse=True)
    vprint('Getting top winners...')
    top_winners = get_top_winners(sorted_winners)
    consolidated_winners = super_consolidate(top_winners)
    target.winner_bins = sorted(consolidated_winners.items(), key=sort_winners, reverse=True)

def sort_winners(key):
    return len(key[1])


def consolidate_winners(winner_bins):
    winners = {}
    for winner_name, awards in winner_bins.items():
        if winner_name:
            if winner_name in util.common_words:
                continue
            if winner_name[0] == '@':
                winner_name = handle_lookup(winner_name)
            elif winner_name[0] == '#':
                winner_name = split_hashtag(winner_name)
            winner_name = winner_name.lower()
            if winner_name in winners.keys():
                winners[winner_name].extend(awards)
            else:
                winners[winner_name] = awards
    return winners


def get_top_winners(winner_bins):
    total = 0
    so_far = 0
    result = []
    for winner, value in winner_bins:
        total += len(value)
    thresh = total * util.winner_threshold
    for winner, value in winner_bins:
        if so_far > thresh:
            break
        result.append((winner, value))
        so_far += len(value)
    return result


def super_consolidate(winner_bins):
    result = {}
    # ref_dict = {name: None for name, value in winner_bins}
    ref_dict = {}
    for i in range(len(winner_bins)):
        for j in range(len(winner_bins)):
            if i == j:
                continue
            if winner_bins[i][0] in winner_bins[j][0]:
                print winner_bins[i][0], "in", winner_bins[j][0]
                if i > j:
                    # ref_dict[winner_bins[j][0]] = winner_bins[j][0]
                    ref_dict[winner_bins[i][0]] = winner_bins[j][0]
                else:
                    ref_dict[winner_bins[j][0]] = winner_bins[i][0]
                    # ref_dict[winner_bins[i][0]] = winner_bins[i][0]
    for name, value in winner_bins:
        if name in ref_dict:
            simplified_name = ref_dict[name]
        else:
            simplified_name = name
        if simplified_name in result:
            result[simplified_name].extend(value)
        else:
            result[simplified_name] = value
    return result


def handle_lookup(winner_name):
    result = winner_name
    match = regex.twitter_handel.search(winner_name)
    if match:
        try:
            result = util.twitter_api.users.show(screen_name=match.group(1))['name']
        except twitter.api.TwitterHTTPError:
            pass
    return result


def split_hashtag(hashtag):
    result = ''
    for letter in hashtag:
        if letter == '#':
            continue
        if letter.islower():
            result += letter
        elif result:
            result += ' ' + letter
        else:
            result += letter
    return result


def read_winners(db, target):
    cursor = db.collection.find({"text": regex.winners, 'retweeted_status': {'$exists': False}})
    winner_bins = {}
    for tweet in cursor:
        tweet_time = datetime.datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y')\
            .replace(tzinfo=tz.gettz('UTC'))
        if weed_out(tweet, target, tweet_time):
            continue
        parsed_tweet = None
        model_num = 0
        for winner_model in regex.winner_models:
            match = winner_model.search(tweet['text'])
            if match:
                parsed_tweet = match
                break
            model_num += 1
        if not parsed_tweet:
            continue
        winner = parsed_tweet.group(1)
        award = parsed_tweet.group(2)
        if winner in winner_bins.keys():
            winner_bins[winner].append((award, tweet_time))
        else:
            winner_bins[winner] = [(award, tweet_time)]
    return winner_bins


def weed_out(tweet, target, tweet_time):
    # Check for subjunctive
    if regex.subjunctive.search(tweet['text']):
        return True
    # Check if tweet occurs before event starts
    if tweet_time < target.start_time:
        return True
    return False