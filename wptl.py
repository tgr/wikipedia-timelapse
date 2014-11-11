#!/usr/bin/python
# -*- coding: utf-8 -*-

# requires Python 2.7+ due to argparse and timedelta.total_seconds.

import os
import sys
import yaml
import argparse
from datetime import timedelta
from dateutil.parser import parse as parse_date
from wikitools import wiki
from wikitools import api

title = None

def get_config():
    script_dir = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    try:
        config_file = open(script_dir + '/config.yaml', 'r') 
    except IOError:
        config_file = open(script_dir + '/config.yaml.dist', 'r')
    return yaml.load(config_file)

def get_endpoint(params, config):
    return config['api_endpoint'] % {'lang': params.lang or config['default_language']}

def get_article_url(oldid, params, config):
    global title
    title = title or api.urlencode({'_': params.page})[2:]
    return config['article_url'] % {'lang': params.lang or config['default_language'], 'title': title, 'oldid': oldid}

def yield_revisions(params, config):
    site = wiki.Wiki(get_endpoint(params, config))
    query = {'action': 'query', 'prop': 'revisions', 'rvprop': 'ids', 'rvdir': 'newer', 'rvlimit': 500}
    query['titles'] = params.page

    start = params.start
    end = params.end
    if start and end:
        diff = end - start
        start = start - timedelta(seconds = diff.total_seconds() * config['date_buffer_pre'])
        end = end + timedelta(seconds = diff.total_seconds() * config['date_buffer_post'])
    if start:
        query['rvstart'] = start.isoformat()
    if end:
        query['rvend'] = end.isoformat()

    request = api.APIRequest(site, query)
    result = request.query(querycontinue=True)

    page_data = result['query']['pages'].itervalues().next()
    if 'missing' in page_data:
        print 'No such page!'
        sys.exit(5)
    try:
        revision_list = page_data['revisions']
    except KeyError:
        print 'No matching revisions!'
        sys.exit(5)
    for revision_data in revision_list:
        yield revision_data['revid']

def yield_old_urls(revisions, params, config):
    for revision in sorted(revisions):
        yield get_article_url(revision, params, config)

def get_params(config):
    parser = argparse.ArgumentParser(description = 'list URLs to old revisions of a page')
    parser.add_argument('page', help = 'title of the wiki page')
    parser.add_argument('--from', type = parse_date, dest = 'start', metavar = 'TIMESTAMP', help = 'date to list revisions from (any standard time format is understood)')
    parser.add_argument('--to', type = parse_date, dest = 'end', metavar = 'TIMESTAMP', help = 'date to list revisions to')
    parser.add_argument('--lang', metavar = 'LANGUAGE', default = config['default_language'], help = 'language / wiki version')
    return parser.parse_args()

def main():
    config = get_config()
    params = get_params(config)
    revisions = yield_revisions(params, config)
    for url in yield_old_urls(revisions, params, config):
        print url

main()