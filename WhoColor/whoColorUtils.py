# -*- coding: utf-8 -*-
"""

:Authors:
    Kenan Erdogan
"""
import requests
import hashlib
from dateutil import parser
from datetime import datetime


class WikipediaRevText(object):
    """
    Example usage:
        wp_rev_text_obj = WikipediaRevText(page_title='Cologne', page_id=6187)
        # to get rev wiki text from wp api
        rev_data = wp_rev_text_obj.get_rev_wiki_text()
        # to convert (extended) wiki text into html by using wp api
        rev_extended_html = wp_rev_text_obj.convert_wiki_text_to_html(wiki_text=rev_data['rev_text'])
    """

    def __init__(self, page_title=None, page_id=None, rev_id=None, language='en'):
        """
        :param page_title: Title of an article.
        :param page_id: ID of an article
        :param rev_id: Revision id to get wiki text.
        :param language: Language of the page.
        """
        self.page_id = page_id
        self.page_title = page_title
        self.rev_id = rev_id
        self.language = language

    def _prepare_request(self, wiki_text=None):
        data = {'url': 'https://{}.wikipedia.org/w/api.php'.format(self.language)}
        if wiki_text is None:
            params = {'action': 'query', 'prop': 'revisions',
                      'rvprop': 'content|ids', 'rvlimit': '1', 'format': 'json'}
            if self.page_id:
                params.update({'pageids': self.page_id})
            elif self.page_title:
                params.update({'titles': self.page_title})
            if self.rev_id is not None:
                params.update({'rvstartid': self.rev_id})  # , 'rvendid': rev_id})
        else:
            params = {'action': 'parse', 'title': self.page_title,
                      'format': 'json', 'text': wiki_text, 'prop': 'text'}
        data['data'] = params
        return data

    def _make_request(self, data):
        response = requests.post(**data).json()
        return response

    def get_rev_wiki_text(self):
        """
        If no rev id is given, text of latest revision is returned.
        If both article id and title are given, id is used in query.
        """
        if self.page_id is None and self.page_title is None:
            raise Exception('Please provide id or title of the article.')

        data = self._prepare_request()
        response = self._make_request(data)

        if 'error' in response:
            return response
        pages = response['query']['pages']
        if '-1' in pages:
            return pages
        for page_id, page in response['query']['pages'].items():
            namespace = page['ns']
            revisions = page.get('revisions')
            if revisions is None:
                return None
            else:
                return {
                    'page_id': int(page_id),
                    'namespace': namespace,
                    'rev_id': revisions[0]['revid'],
                    'rev_text': revisions[0]['*']
                }

    def convert_wiki_text_to_html(self, wiki_text):
        """
        Title of the article is required.
        """
        if self.page_title is None:
            raise Exception('Please provide title of the article.')

        data = self._prepare_request(wiki_text)
        response = self._make_request(data)

        if 'error' in response:
            return response

        return response['parse']['text']['*']


class WikipediaUser(object):
    """
    Example usage to get names of given editor ids:
        editor_ids = set(('30764272', '1465', '5959'))
        wp_user_obj = WikipediaUser()
        editors = wp_user_obj.get_editor_names(editor_ids)
    """
    def __init__(self, language='en'):
        self.language = language

    def _prepare_request(self, editor_ids):
        params = {'action': 'query', 'list': 'users',
                  'format': 'json', 'ususerids': '|'.join(editor_ids)}
        return {
            'url': 'https://{}.wikipedia.org/w/api.php'.format(self.language),
            'data': params
        }

    def _make_request(self, data):
        response = requests.post(**data).json()
        return response

    def get_editor_names(self, editor_ids, batch_size=50):
        """
        :param editor_ids: list of editor ids
        :param batch_size: number of editor ids (ususerids) in the query. WP allows 50 if not logged in.
        :return: a dict {editor_id: editor_name}
        """
        editor_ids = list(editor_ids)
        editor_names = {}  # {editor_id: editor_name, ..}
        editors_len = len(editor_ids)

        c = 1
        while True:
            data = self._prepare_request(editor_ids[batch_size*(c-1):batch_size*c])
            response = self._make_request(data)

            if 'error' in response:
                return response
            users = response['query']['users']
            if '-1' in users:
                return users

            for user in users:
                editor_names[str(user['userid'])] = user.get('name', None)

            if batch_size*c >= editors_len:
                break
            c += 1
        return editor_names


class WikiWhoRevContent(object):
    """
    Example usage:
        ww_rev_content_obj = WikiWhoRevContent(page_id=6187)
        wikiwho_data = ww_rev_content_obj.get_revisions_and_tokens()
    """
    def __init__(self, page_id=None, page_title=None, rev_id=None, language='en'):
        self.page_id = page_id
        self.page_title = page_title
        self.rev_id = rev_id
        self.language = language

    def _prepare_request(self, rev_ids=False):
        ww_api_url = 'https://www.wikiwho.net/{}/api/v1.0.0-beta'.format(self.language)
        if rev_ids:
            if self.page_id:
                url_params = 'page_id/{}'.format(self.page_id)
            elif self.page_title:
                url_params = '{}'.format(self.page_title)
            return {'url': '{}/rev_ids/{}/'.format(ww_api_url, url_params),
                    'params': {'editor': 'true', 'timestamp': 'true'}}
        else:
            if self.page_id:
                url_params = 'page_id/{}'.format(self.page_id)
            elif self.rev_id:
                url_params = '{}/{}'.format(self.page_title, self.rev_id)
            elif self.page_title:
                url_params = '{}'.format(self.page_title)
            return {'url': '{}/rev_content/{}/'.format(ww_api_url, url_params),
                    'params': {'o_rev_id': 'true', 'editor': 'true',
                               'token_id': 'false', 'out': 'true', 'in': 'true'}}

    def _make_request(self, data):
        response = requests.get(**data).json()
        return response

    def get_revisions_data(self):
        # get revisions-editors
        data = self._prepare_request(rev_ids=True)
        response = self._make_request(data)
        # {rev_id: [timestamp, parent_id, editor]}
        revisions = {response['revisions'][0]['id']: [response['revisions'][0]['timestamp'],
                                                      0,
                                                      response['revisions'][0]['editor']]}
        for i, rev in enumerate(response['revisions'][1:]):
            revisions[rev['id']] = [rev['timestamp'],
                                    response['revisions'][i]['id'],  # parent = previous rev id
                                    rev['editor']]
        return revisions

    def get_editor_names(self, revisions):
        # get editor names from wp api
        editor_ids = {rev_data[2] for rev_id, rev_data in revisions.items()
                      if rev_data[2] and not rev_data[2].startswith('0|')}
        wp_users_obj = WikipediaUser(self.language)
        editor_names_dict = wp_users_obj.get_editor_names(editor_ids)

        # extend revisions data
        # {rev_id: [timestamp, parent_id, class_name/editor, editor_name]}
        for rev_id, rev_data in revisions.items():
            rev_data.append(editor_names_dict.get(rev_data[2], rev_data[2]))
            if rev_data[2].startswith('0|'):
                rev_data[2] = hashlib.md5(rev_data[2].encode('utf-8')).hexdigest()

        return editor_names_dict

    def get_tokens_data(self, revisions, editor_names_dict):
        data = self._prepare_request()
        response = self._make_request(data)
        _, rev_data = response['revisions'][0].popitem()
        tokens = rev_data['tokens']

        # set editor and class names and calculate conflict score for each token
        # if registered user, class name is editor id
        biggest_conflict_score = 0
        for token in tokens:
            # set editor name
            token['editor_name'] = editor_names_dict.get(token['editor'], token['editor'])
            # set html class name
            if token['editor'].startswith('0|'):
                token['class_name'] = hashlib.md5(token['editor'].encode('utf-8')).hexdigest()
            else:
                token['class_name'] = token['editor']
            # calculate age
            o_rev_ts = parser.parse(revisions[token['o_rev_id']][0])
            age = datetime.now(o_rev_ts.tzinfo) - o_rev_ts
            token['age'] = age.total_seconds()
            # calculate conflict score
            editor_in_prev = None
            conflict_score = 0
            for i, out_ in enumerate(token['out']):
                editor_out = revisions[out_][2]
                if editor_in_prev is not None and editor_in_prev != editor_out:
                    # exclude first deletions and self reverts (undo actions)
                    conflict_score += 1
                try:
                    in_ = token['in'][i]
                except IndexError:
                    # no in for this out. end of loop.
                    pass
                else:
                    editor_in = revisions[in_][2]
                    if editor_out != editor_in:
                        # exclude self reverts (undo actions)
                        conflict_score += 1
                    editor_in_prev = editor_in
            token['conflict_score'] = conflict_score
            if conflict_score > biggest_conflict_score:
                biggest_conflict_score = conflict_score

        return tokens, biggest_conflict_score

    def convert_tokens_data(self, tokens):
        # convert into list. exclude unnecessary token data
        # [[conflict_score, str, o_rev_id, in, out, editor/class_name, age]]
        return [[token['conflict_score'], token['str'], token['o_rev_id'],
                 token['in'], token['out'], token['class_name'], token['age']]
                for token in tokens]

    def get_revisions_and_tokens(self):
        """
        Returns all revisions data of the article and tokens of given article.
        If no rev id is given, tokens of latest revision is returned.
        """
        if self.page_id is None and self.page_title is None and self.rev_id is None:
            raise Exception('Please provide page id or page title or rev id.')

        revisions = self.get_revisions_data()
        editor_names_dict = self.get_editor_names(revisions)
        tokens, biggest_conflict_score = self.get_tokens_data(revisions, editor_names_dict)
        tokens = self.convert_tokens_data(tokens)

        return {'revisions': revisions,
                'tokens': tokens,
                'biggest_conflict_score': biggest_conflict_score}
