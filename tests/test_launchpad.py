#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2017 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, 51 Franklin Street, Fifth Floor, Boston, MA 02110-1335, USA.
#
# Authors:
#     Valerio Cosentino <valcos@bitergia.com>
#

import datetime
import httpretty
import json
import os
import pkg_resources
import requests
import shutil
import sys
import tempfile
import unittest

# Hack to make sure that tests import the right packages
# due to setuptools behaviour
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
pkg_resources.declare_namespace('perceval.backends')

from perceval.backend import BackendCommandArgumentParser
from perceval.backends.core.launchpad import (Launchpad,
                                              LaunchpadClient,
                                              LaunchpadCommand)
from perceval.cache import Cache
from perceval.errors import CacheError
from perceval.utils import DEFAULT_DATETIME


LAUNCHPAD_API_URL = "https://api.launchpad.net/1.0"
CONSUMER_KEY = "myapp"
OAUTH_TOKEN = 'GFVlv1PzWjGrMLcD90V5'

LAUNCHPAD_PACKAGE_PROJECT_URL = LAUNCHPAD_API_URL + "/mydistribution/+source/mypackage"
LAUNCHPAD_DISTRIBUTION_PROJECT_URL = LAUNCHPAD_API_URL + "/mydistribution"


def read_file(filename, mode='r'):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), filename), mode) as f:
        content = f.read()
    return content


class TestLaunchpadBackend(unittest.TestCase):
    """Launchpad backend tests"""

    def test_initialization(self):
        """Test whether attributes are initializated"""

        launchpad = Launchpad('mydistribution', tag='test')
        self.assertEqual(launchpad.distribution, 'mydistribution')
        self.assertEqual(launchpad.package, None)
        self.assertEqual(launchpad.origin, 'https://launchpad.net/mydistribution')
        self.assertEqual(launchpad.tag, 'test')

        launchpad = Launchpad('mydistribution', consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN, tag='test', package="mypackage")
        self.assertEqual(launchpad.distribution, 'mydistribution')
        self.assertEqual(launchpad.package, 'mypackage')
        self.assertEqual(launchpad.origin, 'https://launchpad.net/mydistribution')
        self.assertEqual(launchpad.tag, 'test')

        # When tag is empty or None it will be set to
        # the value in origin
        launchpad = Launchpad('mydistribution', consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN, tag=None)
        self.assertEqual(launchpad.distribution, 'mydistribution')
        self.assertEqual(launchpad.origin, 'https://launchpad.net/mydistribution')
        self.assertEqual(launchpad.tag, 'https://launchpad.net/mydistribution')

        launchpad = Launchpad('mydistribution', consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN, tag='')
        self.assertEqual(launchpad.distribution, 'mydistribution')
        self.assertEqual(launchpad.origin, 'https://launchpad.net/mydistribution')
        self.assertEqual(launchpad.tag, 'https://launchpad.net/mydistribution')

    def test_has_caching(self):
        """Test if it returns True when has_caching is called"""

        self.assertEqual(Launchpad.has_caching(), True)

    def test_has_resuming(self):
        """Test if it returns True when has_resuming is called"""

        self.assertEqual(Launchpad.has_resuming(), True)

    @httpretty.activate
    def test_fetch(self):
        """Test whether a list of issues is returned"""

        issues_page_1 = read_file('data/launchpad/launchpad_issues_page_1')
        issues_page_2 = read_file('data/launchpad/launchpad_issues_page_2')
        issues_page_3 = read_file('data/launchpad/launchpad_issues_page_3')

        issue_1 = read_file('data/launchpad/launchpad_issue_1')
        issue_2 = read_file('data/launchpad/launchpad_issue_2')
        issue_3 = read_file('data/launchpad/launchpad_issue_3')

        issue_1_comments = read_file('data/launchpad/launchpad_issue_1_comments')
        issue_1_attachments = read_file('data/launchpad/launchpad_issue_1_attachments')
        issue_1_activities = read_file('data/launchpad/launchpad_issue_1_activities')

        issue_2_activities = read_file('data/launchpad/launchpad_issue_2_activities')
        issue_2_comments = read_file('data/launchpad/launchpad_issue_2_comments')

        user_1 = read_file('data/launchpad/launchpad_user_1')

        empty_issue_comments = read_file('data/launchpad/launchpad_empty_issue_comments')
        empty_issue_attachments = read_file('data/launchpad/launchpad_empty_issue_attachments')
        empty_issue_activities = read_file('data/launchpad/launchpad_empty_issue_activities')

        issue_1_expected = read_file('data/launchpad/launchpad_issue_1_expected')
        issue_2_expected = read_file('data/launchpad/launchpad_issue_2_expected')
        issue_3_expected = read_file('data/launchpad/launchpad_issue_3_expected')

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1&memo=2&ws.start=2",
                               body=issues_page_3,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1&memo=1&ws.start=1",
                               body=issues_page_2,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1",
                               body=issues_page_1,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1",
                               body=issue_1,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/2",
                               body=issue_2,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/3",
                               body=issue_3,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/messages",
                               body=issue_1_comments,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/2/messages",
                               body=issue_2_comments,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/3/messages",
                               body=empty_issue_comments,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/attachments",
                               body=issue_1_attachments,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/2/attachments",
                               body=empty_issue_attachments,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/3/attachments",
                               body=empty_issue_attachments,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/activity",
                               body=issue_1_activities,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/2/activity",
                               body=issue_2_activities,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/3/activity",
                               body=empty_issue_activities,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/~user",
                               body=user_1,
                               status=200)

        launchpad = Launchpad('mydistribution', package="mypackage",
                              items_per_page=2)
        issues = [issues for issues in launchpad.fetch()]

        issue_1_expected = json.loads(issue_1_expected)
        issue_2_expected = json.loads(issue_2_expected)
        issue_3_expected = json.loads(issue_3_expected)

        self.assertEqual(len(issues), 3)
        self.assertEqual(len(issues[0]['data']['activity_data']), 1)
        self.assertEqual(len(issues[0]['data']['messages_data']), 2)
        self.assertDictEqual(issues[0]['data']['assignee_data'], issue_1_expected['assignee_data'])
        self.assertDictEqual(issues[0]['data']['owner_data'], issue_1_expected['owner_data'])
        self.assertListEqual(issues[0]['data']['activity_data'], issue_1_expected['activity_data'])
        self.assertListEqual(issues[0]['data']['messages_data'], issue_1_expected['messages_data'])
        self.assertDictEqual(issues[0]['data'], issue_1_expected)

        self.assertDictEqual(issues[1]['data']['assignee_data'], issue_2_expected['assignee_data'])
        self.assertDictEqual(issues[1]['data']['owner_data'], issue_2_expected['owner_data'])
        self.assertEqual(len(issues[1]['data']['activity_data']), 1)
        self.assertEqual(len(issues[1]['data']['messages_data']), 1)
        self.assertListEqual(issues[1]['data']['activity_data'], issue_2_expected['activity_data'])
        self.assertListEqual(issues[1]['data']['messages_data'], issue_2_expected['messages_data'])
        self.assertDictEqual(issues[1]['data'], issue_2_expected)

        self.assertDictEqual(issues[2]['data']['assignee_data'], issue_3_expected['assignee_data'])
        self.assertDictEqual(issues[2]['data']['owner_data'], issue_3_expected['owner_data'])
        self.assertEqual(len(issues[2]['data']['activity_data']), 0)
        self.assertEqual(len(issues[2]['data']['messages_data']), 0)
        self.assertListEqual(issues[2]['data']['activity_data'], issue_3_expected['activity_data'])
        self.assertListEqual(issues[2]['data']['messages_data'], issue_3_expected['messages_data'])
        self.assertDictEqual(issues[2]['data'], issue_3_expected)

    @httpretty.activate
    def test_fetch_from_date(self):
        """Test when return from date"""

        issues_page_1 = read_file('data/launchpad/launchpad_issues_page_1_no_next')
        issue_1 = read_file('data/launchpad/launchpad_issue_1')
        issue_1_comments = read_file('data/launchpad/launchpad_issue_1_comments')
        issue_1_attachments = read_file('data/launchpad/launchpad_issue_1_attachments')
        issue_1_activities = read_file('data/launchpad/launchpad_issue_1_activities')
        user_1 = read_file('data/launchpad/launchpad_user_1')
        issue_1_expected = read_file('data/launchpad/launchpad_issue_1_expected')

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1",
                               body=issues_page_1,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1",
                               body=issue_1,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/messages",
                               body=issue_1_comments,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/attachments",
                               body=issue_1_attachments,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/activity",
                               body=issue_1_activities,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/~user",
                               body=user_1,
                               status=200)

        launchpad = Launchpad('mydistribution', consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN, package="mypackage",
                              items_per_page=2)
        from_date = datetime.datetime(2018, 8, 21, 16, 0, 0)
        issues = [issues for issues in launchpad.fetch(from_date=from_date)]
        issue_1_expected = json.loads(issue_1_expected)

        self.assertEqual(len(issues), 1)
        self.assertDictEqual(issues[0]['data'], issue_1_expected)

    @httpretty.activate
    def test_fetch_empty(self):
        """Test when return empty"""

        empty_issues = read_file('data/launchpad/launchpad_empty_issues')
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1&ws.start=0",
                               body=empty_issues,
                               status=200)

        launchpad = Launchpad('mydistribution', consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN, package="mypackage",
                              items_per_page=2)
        issues = [issues for issues in launchpad.fetch()]

        self.assertListEqual(issues, [])

    @httpretty.activate
    def test_fetch_empty_no_package(self):
        """Test when no issues are available"""

        empty_issues = read_file('data/launchpad/launchpad_empty_issues')
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_DISTRIBUTION_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1&ws.start=0",
                               body=empty_issues,
                               status=200)

        launchpad = Launchpad('mydistribution', consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN, items_per_page=2)
        issues = [issues for issues in launchpad.fetch()]

        self.assertListEqual(issues, [])

    @httpretty.activate
    def test_fetch_no_entries(self):
        """Test when activities, attachments and messages contain no JSON-like data"""

        issues_page_1 = read_file('data/launchpad/launchpad_issues_page_1_no_entries')
        issue_1 = read_file('data/launchpad/launchpad_issue_1_no_entries')
        issue_1_comments = read_file('data/launchpad/launchpad_issue_1_comments_no_entries')
        issue_1_attachments = read_file('data/launchpad/launchpad_issue_1_attachments_no_entries')
        issue_1_activities = read_file('data/launchpad/launchpad_issue_1_activities_no_entries')
        issue_1_expected = read_file('data/launchpad/launchpad_issue_1_expected_no_entries')

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1",
                               body=issues_page_1,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1",
                               body=issue_1,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/messages",
                               body=issue_1_comments,
                               status=410)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/attachments",
                               body=issue_1_attachments,
                               status=410)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/activity",
                               body=issue_1_activities,
                               status=410)

        issue_1_expected = json.loads(issue_1_expected)

        launchpad = Launchpad("mydistribution", consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN, package='mypackage',
                              items_per_page=2)
        issues = [issues for issues in launchpad.fetch()]

        self.assertDictEqual(issues[0]['data'], issue_1_expected)


class TestLaunchpadBackendCache(unittest.TestCase):
    """Launchpad backend tests using a cache"""

    def setUp(self):
        self.tmp_path = tempfile.mkdtemp(prefix='perceval_')

    def tearDown(self):
        shutil.rmtree(self.tmp_path)

    @httpretty.activate
    def test_fetch_from_cache(self):
        """Test whether a list of issues is returned from cache"""

        issues_page_1 = read_file('data/launchpad/launchpad_issues_page_1')
        issues_page_2 = read_file('data/launchpad/launchpad_issues_page_2')
        issues_page_3 = read_file('data/launchpad/launchpad_issues_page_3')

        issue_1 = read_file('data/launchpad/launchpad_issue_1')
        issue_2 = read_file('data/launchpad/launchpad_issue_2')
        issue_3 = read_file('data/launchpad/launchpad_issue_3')

        issue_1_activities_next_1 = read_file('data/launchpad/launchpad_issue_1_activities_next_1')
        issue_1_activities_next_2 = read_file('data/launchpad/launchpad_issue_1_activities_next_2')

        issue_1_comments_next_1 = read_file('data/launchpad/launchpad_issue_1_comments_next_1')
        issue_1_comments_next_2 = read_file('data/launchpad/launchpad_issue_1_comments_next_2')

        issue_1_attachments_next_1 = \
            read_file('data/launchpad/launchpad_issue_1_attachments_next_1')
        issue_1_attachments_next_2 = \
            read_file('data/launchpad/launchpad_issue_1_attachments_next_2')

        issue_2_activities = read_file('data/launchpad/launchpad_issue_2_activities')
        issue_2_comments = read_file('data/launchpad/launchpad_issue_2_comments')

        user_1 = read_file('data/launchpad/launchpad_user_1')

        empty_issue_comments = read_file('data/launchpad/launchpad_empty_issue_comments')
        empty_issue_attachments = read_file('data/launchpad/launchpad_empty_issue_attachments')
        empty_issue_activities = read_file('data/launchpad/launchpad_empty_issue_activities')

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1&memo=2&ws.start=2",
                               body=issues_page_3,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1&memo=1&ws.start=1",
                               body=issues_page_2,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1&ws.start=0",
                               body=issues_page_1,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1",
                               body=issue_1,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/2",
                               body=issue_2,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/3",
                               body=issue_3,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/messages",
                               body=issue_1_comments_next_2,
                               params={'ws.size': 2, 'memo': 2, 'ws.start': 2},
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/messages",
                               body=issue_1_comments_next_1,
                               params={'ws.size': 2, 'orderby': '-datecreated', 'ws.start': 0},
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/2/messages",
                               body=issue_2_comments,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/3/messages",
                               body=empty_issue_comments,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/attachments",
                               body=issue_1_attachments_next_2,
                               params={'orderby': '-datecreated', 'ws.size': 2, 'memo': 2, 'ws.start': 2},
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/attachments",
                               body=issue_1_attachments_next_1,
                               params={'orderby': '-datecreated', 'ws.size': 2, 'ws.start': 0},
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/2/attachments",
                               body=empty_issue_attachments,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/3/attachments",
                               body=empty_issue_attachments,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/activity",
                               body=issue_1_activities_next_2,
                               params={'orderby': '-datecreated', 'ws.size': 2, 'memo': 2, 'ws.start': 2},
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/activity",
                               body=issue_1_activities_next_1,
                               params={'orderby': '-datecreated', 'ws.size': 2, 'ws.start': 0},
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/2/activity",
                               body=issue_2_activities,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/3/activity",
                               body=empty_issue_activities,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/~user",
                               body=user_1,
                               status=200)

        # First, we fetch the bugs from the server and store them in a cache
        cache = Cache(self.tmp_path)
        launchpad = Launchpad('mydistribution', consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN, package="mypackage",
                              cache=cache, items_per_page=2)
        issues = [issues for issues in launchpad.fetch()]

        # Now, we get the bugs from the cache.
        cache_issues = [cache_issues for cache_issues in launchpad.fetch_from_cache()]

        del issues[0]['timestamp']
        del cache_issues[0]['timestamp']
        del issues[1]['timestamp']
        del cache_issues[1]['timestamp']
        del issues[2]['timestamp']
        del cache_issues[2]['timestamp']

        self.assertEqual(len(issues), len(cache_issues))
        self.assertDictEqual(issues[0], cache_issues[0])
        self.assertDictEqual(issues[1], cache_issues[1])
        self.assertDictEqual(issues[2], cache_issues[2])

    def test_fetch_from_empty_cache(self):
        """Test if there are not any issues returned when the cache is empty"""

        cache = Cache(self.tmp_path)
        launchpad = Launchpad('mydistribution', consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN, package="mypackage",
                              cache=cache)

        cache_issues = [cache_issues for cache_issues in launchpad.fetch_from_cache()]

        self.assertEqual(len(cache_issues), 0)

    def test_fetch_from_non_set_cache(self):
        """Test if a error is raised when the cache was not set"""

        launchpad = Launchpad('mydistribution', consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN, package="mypackage")

        with self.assertRaises(CacheError):
            _ = [cache_issues for cache_issues in launchpad.fetch_from_cache()]

    @httpretty.activate
    def test_fetch_from_cache_no_entries(self):
        """Test when activities, attachments and messages contain no JSON-like data"""

        issues_page_1 = read_file('data/launchpad/launchpad_issues_page_1_no_entries')
        issue_1 = read_file('data/launchpad/launchpad_issue_1_no_entries')
        issue_1_comments = read_file('data/launchpad/launchpad_issue_1_comments_no_entries')
        issue_1_attachments = read_file('data/launchpad/launchpad_issue_1_attachments_no_entries')
        issue_1_activities = read_file('data/launchpad/launchpad_issue_1_activities_no_entries')

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1",
                               body=issues_page_1,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1",
                               body=issue_1,
                               status=200)

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/messages",
                               body=issue_1_comments,
                               status=410)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/attachments",
                               body=issue_1_attachments,
                               status=410)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/bugs/1/activity",
                               body=issue_1_activities,
                               status=410)

        cache = Cache(self.tmp_path)
        launchpad = Launchpad('mydistribution', consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN, package='mypackage',
                              items_per_page=2, cache=cache)
        issues = [issues for issues in launchpad.fetch()]

        issues_from_cache = [issues for issues in launchpad.fetch_from_cache()]

        self.assertDictEqual(issues[0]['data'], issues_from_cache[0]['data'])


class TestLaunchpadClient(unittest.TestCase):
    """Launchpad API client tests"""

    @httpretty.activate
    def test_issues_from_date(self):
        """Test issues from date API call"""

        # this method cannot be tested, because the next page is encoded
        # in the HTTP response (and not in the query string)
        issues_page_1 = read_file('data/launchpad/launchpad_issues_page_1_no_next')
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=2017-08-21T16%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1&ws.start=0",
                               body=issues_page_1,
                               status=200)

        client = LaunchpadClient("mydistribution", consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN,
                                 package='mypackage', items_per_page=2)
        from_date = datetime.datetime(2018, 8, 21, 16, 0, 0)
        issues = [issues for issues in client.issues(start=from_date)]

        self.assertEqual(len(issues), 1)

    @httpretty.activate
    def test_issues(self):
        """Test issues API call"""

        issues_page_1 = read_file('data/launchpad/launchpad_issues_page_1')
        issues_page_2 = read_file('data/launchpad/launchpad_issues_page_2')
        issues_page_3 = read_file('data/launchpad/launchpad_issues_page_3')

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1&memo=2&ws.start=2",
                               body=issues_page_3,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1&memo=1&ws.start=1",
                               body=issues_page_2,
                               status=200)
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1&ws.start=0",
                               body=issues_page_1,
                               status=200)

        client = LaunchpadClient("mydistribution", consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN,
                                 package="mypackage", items_per_page=2)
        issues = [issues for issues in client.issues()]

        self.assertEqual(len(issues), 3)

    @httpretty.activate
    def test_issues_empty(self):
        """Test when issue is empty API call"""

        empty_issues = read_file('data/launchpad/launchpad_empty_issues')
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_PACKAGE_PROJECT_URL +
                               "?modified_since=1970-01-01T00%3A00%3A00%2B00%3A00&ws.op=searchTasks"
                               "&omit_duplicates=false&order_by=date_last_updated&status=Confirmed&status=Expired"
                               "&status=Fix+Committed&status=Fix+Released"
                               "&status=In+Progress&status=Incomplete&status=Incomplete+%28with+response%29"
                               "&status=Incomplete+%28without+response%29"
                               "&status=Invalid&status=New&status=Opinion&status=Triaged"
                               "&status=Won%27t+Fix"
                               "&ws.size=1&ws.start=0",
                               body=empty_issues,
                               status=200)

        client = LaunchpadClient("mydistribution", consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN,
                                 package="mypackage")
        issues = [issues for issues in client.issues()]

        self.assertDictEqual(json.loads(issues[0]), json.loads(empty_issues))

    @httpretty.activate
    def test_user(self):
        """Test user API call"""

        user = read_file('data/launchpad/launchpad_user_1')
        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/~user",
                               body=user,
                               status=200)

        client = LaunchpadClient("mydistribution", consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN,
                                 package="mypackage")
        user_retrieved = client.user("user")

        self.assertDictEqual(json.loads(user_retrieved), json.loads(user))

    @httpretty.activate
    def test_user_not_retrieved(self):
        """Test user API call"""

        httpretty.register_uri(httpretty.GET,
                               LAUNCHPAD_API_URL + "/~user-not",
                               body="",
                               status=404)

        client = LaunchpadClient("mydistribution", consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN,
                                 package="mypackage")

        user_retrieved = client.user("user-not")
        self.assertEqual(user_retrieved, "{}")

    @httpretty.activate
    def test_http_wrong_status_issue_collection(self):
        """Test if an empty collection is returned when the http status is not 200"""

        client = LaunchpadClient("mydistribution", consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN,
                                 package="mypackage")
        with self.assertRaises(requests.exceptions.HTTPError):
            _ = next(client.issue_collection("100", "attachments"))

    @httpretty.activate
    def test_http_wrong_status_user(self):
        """Test if an empty user is returned when the http status is not 200"""

        client = LaunchpadClient("mydistribution", consumer_key=CONSUMER_KEY, api_token=OAUTH_TOKEN,
                                 package="mypackage")
        with self.assertRaises(requests.exceptions.HTTPError):
            _ = client.user("user1")


class TestLaunchpadCommand(unittest.TestCase):
    """LaunchpadCommand unit tests"""

    def test_backend_class(self):
        """Test if the backend class is Launchpad"""

        self.assertIs(LaunchpadCommand.BACKEND, Launchpad)

    def test_setup_cmd_parser(self):
        """Test if it parser object is correctly initialized"""

        parser = LaunchpadCommand.setup_cmd_parser()
        self.assertIsInstance(parser, BackendCommandArgumentParser)

        args = ['--tag', 'test', '--no-cache',
                '--from-date', '1970-01-01',
                '--items-per-page', '75',
                '--sleep-time', '600',
                'mydistribution']

        parsed_args = parser.parse(*args)
        self.assertEqual(parsed_args.distribution, 'mydistribution')
        self.assertEqual(parsed_args.tag, 'test')
        self.assertEqual(parsed_args.from_date, DEFAULT_DATETIME)
        self.assertEqual(parsed_args.no_cache, True)
        self.assertEqual(parsed_args.items_per_page, '75')
        self.assertEqual(parsed_args.sleep_time, '600')


if __name__ == "__main__":
    unittest.main(warnings='ignore')
