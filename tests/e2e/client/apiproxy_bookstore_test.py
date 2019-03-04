#!/usr/bin/env python

# Copyright 2019 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import httplib
import utils
import json
import ssl
import sys
from utils import ApiProxyClientTest

class C:
    pass
FLAGS = C

class ApiProxyBookstoreTest(ApiProxyClientTest):
    """End to end integration test of bookstore application with deployed
    APIPROXY at VM.  It will call bookstore API according its Swagger spec to
    1) wipe out bookstore clean,
    2) create 2 shelves,
    3) add 2 books into the first shelf.
    4) remove books one by one,
    5) remove shelves one by one.
    """

    def __init__(self):
        ApiProxyClientTest.__init__(self, FLAGS.host,
                               FLAGS.allow_unverified_cert,
                               FLAGS.verbose)

    def _send_request(self, path, api_key=None,
                      auth=None, data=None, method=None):
        """High level sending request test.
        Do Negative tests if endpoints is enabled.
        If auth is required, send it without, verify 401 response.
        If api_key is required, send it without, verify 401 response.
        """
        if FLAGS.endpoints:
            if auth:
                print 'Negative test: remove auth.'
                r = self._call_http(path, api_key, None, data, method)
                self.assertEqual(r.status_code, 401)
                self.assertEqual(
                    r.text,
                    'Jwt is missing')
                print 'Completed Negative test.'
            if api_key:
                print 'Negative test: remove api_key.'
                r = self._call_http(path, None, auth, data, method)
                self.assertEqual(r.status_code, 401)
                self.assertEqual(
                    r.text,
                    ('Method doesn\'t allow unregistered callers (callers without '
                     'established identity). Please use API Key or other form of '
                     'API consumer identity to call this API.'))
                print 'Completed Negative test.'
            return self._call_http(path, api_key, auth, data, method)
        else:
            return self._call_http(path, method=method)

    def clear(self):
        print 'Clear existing shelves.'
        # list shelves: no api_key, no auth
        response = self._send_request('/shelves')
        self.assertEqual(response.status_code, 200)
        json_ret = response.json()
        for shelf in json_ret.get('shelves', []):
            self.delete_shelf(shelf['name'])

    def create_shelf(self, shelf):
        print 'Create shelf: %s' % str(shelf)
        # create shelves: auth.
        response = self._send_request(
            '/shelves', api_key=FLAGS.api_key, auth=FLAGS.auth_token, data=shelf)
        self.assertEqual(response.status_code, 200)
        # shelf name generated in server, not the same as required.
        json_ret = response.json()
        self.assertEqual(json_ret.get('theme', ''), shelf['theme'])
        return json_ret

    def verify_shelf(self, shelf):
        print 'Verify shelf: %s' % shelf['name']
        # Get shelf: auth.
        r = self._send_request('/' + shelf['name'], auth=FLAGS.auth_token)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), shelf)

    def delete_shelf(self, shelf_name):
        print 'Remove shelf: %s' % shelf_name
        # delete shelf: api_key
        print 'API_KEY: %s' % FLAGS.api_key
        r = self._send_request(
            '/' + shelf_name, api_key=FLAGS.api_key, method='DELETE')
        self.assertEqual(r.status_code, 204)

    def verify_list_shelves(self, shelves):
        # list shelves: no api_key, no auth
        response = self._send_request('/shelves')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.json().get('shelves', []), shelves)

    def create_book(self, shelf, book):
        print 'Create book in shelf: %s, book: %s' % (shelf, str(book))
        # Create book: api_key
        response = self._send_request(
            '/%s/books' % shelf, api_key=FLAGS.api_key, data=book)
        self.assertEqual(response.status_code, 200)
        # book name is generated in server, not the same as required.
        json_ret = response.json()
        self.assertEqual(json_ret.get('author', ''), book['author'])
        self.assertEqual(json_ret.get('title', ''), book['title'])
        return json_ret

    def verify_book(self, book):
        print 'Remove book: /%s' % book['name']
        # Get book: api_key, auth
        r = self._send_request(
            '/' + book['name'], api_key=FLAGS.api_key, auth=FLAGS.auth_token)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), book)

    def delete_book(self, book_name):
        print 'Remove book: /%s' % book_name
        # Delete book: api_key
        r = self._send_request(
            '/' + book_name, api_key=FLAGS.api_key, method='DELETE')
        self.assertEqual(r.status_code, 204)

    def verify_list_books(self, shelf, books):
        # List book: api_key
        response = self._send_request(
            '/%s/books' % shelf, api_key=FLAGS.api_key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('books', []), books)

    def run_all_tests(self):
        self.clear()
        self.verify_list_shelves([])

        shelf1 = {
            'name': 'shelves/100',
            'theme': 'Text books'
        }
        shelf1 = self.create_shelf(shelf1)

        self.verify_list_shelves([shelf1])
        shelf2 = {
            'name': 'shelves/200',
            'theme': 'Fiction'
        }
        shelf2 = self.create_shelf(shelf2)
        self.verify_list_shelves([shelf1, shelf2])

        self.verify_shelf(shelf1)
        self.verify_shelf(shelf2)

        book11 = {
            'name': 'books/1000',
            'author': 'Graham Doggett',
            'title': 'Maths for Chemist'
        }
        book11 = self.create_book(shelf1['name'], book11)
        self.verify_list_books(shelf1['name'], [book11])

        book12 = {
            'name': 'books/2000',
            'author': 'George C. Comstock',
            'title': 'A Text-Book of Astronomy'
        }
        book12 = self.create_book(shelf1['name'], book12)
        self.verify_list_books(shelf1['name'], [book11, book12])

        self.verify_book(book11)
        self.verify_book(book12)

        # shelf2 is empty
        self.verify_list_books(shelf2['name'], [])

        self.delete_book(book12['name'])
        self.verify_list_books(shelf1['name'], [book11])

        self.delete_book(book11['name'])
        self.verify_list_books(shelf1['name'], [])

        self.delete_shelf(shelf2['name'])
        self.delete_shelf(shelf1['name'])
        self.verify_list_shelves([])
        if self._failed_tests:
            sys.exit(utils.red('%d tests passed, %d tests failed.' % (
                self._passed_tests, self._failed_tests)))
        else:
            print utils.green('All %d tests passed' % self._passed_tests)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', type=bool, help='Turn on/off verbosity.')
    parser.add_argument('--api_key', help='Project api_key to access service.')
    parser.add_argument('--host', help='Deployed application host name.')
    parser.add_argument('--auth_token', help='Auth token.')
    parser.add_argument('--endpoints', type=bool,
            default=True, help='Is endpoints enabled on the backend?')
    parser.add_argument('--allow_unverified_cert', type=bool,
            default=False, help='used for testing self-signed ssl cert.')
    flags = parser.parse_args(namespace=FLAGS)

    apiproxy_test = ApiProxyBookstoreTest()
    try:
        apiproxy_test.run_all_tests()
    except KeyError as e:
        sys.exit(utils.red('Test failed.'))