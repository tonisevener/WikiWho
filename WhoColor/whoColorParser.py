# -*- coding: utf-8 -*-
"""

:Authors:
    Felix Stadthaus,
    Kenan Erdogan
"""
import re
import io
from .special_markups import SPECIAL_MARKUPS, REGEX_HELPER_PATTERN


class WikiMarkupParser(object):
    def __init__(self, wiki_text, tokens):  # , revisions):
        # Saves the full wikipedia markup and all WikiWho tokens
        self.wiki_text = wiki_text
        self.tokens = tokens
        self.tokens_len = len(tokens)
        # self.revisions = revisions
        self.token = None
        # self.next_special_elem = None

        # Saves the current positions
        self._token_index = 0
        self._wiki_text_pos = 0

        # Saves whether there is currently an open span tag
        self._open_span = False
        # Array that holds the starting positions of blocks (special elements) we already jumped into
        self._jumped_elems = set()

        # The return values of the parser (error can be an error description)
        self.extended_wiki_text = io.StringIO()

        self.error = False
        self.present_editors = dict()  # {editor_id: [editor_name, class_name, count], }
        self.conflict_scores = list()

    def __set_token(self):
        self.token = None
        if self._token_index < self.tokens_len:
            self.token = self.tokens[self._token_index]
            self.conflict_scores.append(self.token['conflict_score'])
            token_pos = re.search(re.escape(self.token['str']), self.wiki_text[self._wiki_text_pos:], re.IGNORECASE)
            if token_pos is None:
                # token is not found. because most probably it contains some characters that has different length
                # in lower and upper case such as 'İstanbul'
                # get next token
                self._token_index += 1
                self.__set_token()
                return
            self.token['end'] = self._wiki_text_pos + token_pos.end()
            if self.token['editor'] in self.present_editors:
                self.present_editors[self.token['editor']][2] += 1
            else:
                self.present_editors[self.token['editor']] = [self.token['editor_name'],
                                                              self.token['class_name'],
                                                              1]  # token count

    def __get_first_regex(self, regex):
        # first_match = None
        # for match in regex.finditer(self.wiki_text):
        #     # search every time from the beginning of text
        #     if (first_match is None or first_match.start() > match.start()) and match.start() >= self._wiki_text_pos:
        #         # if match is first and starts after wiki text pos
        #         first_match = match
        # if first_match is not None:
        #     print('__get_first_regex:', self._wiki_text_pos, self._jumped_elems, first_match.start(), first_match.group(), regex)
        #     return {'str': first_match.group(), 'start': first_match.start()}
        # return None
        # NOTE this doesnt work because if regex contains positive look behind!
        match = regex.search(self.wiki_text[self._wiki_text_pos:])
        if match:
            return {
                'str': match.group(),
                'start': self._wiki_text_pos + match.start()
            }
        return None

    def __get_special_elem_end(self, special_elem):
        # Get end position of current special markup element
        end_pos_data = {}
        if special_elem.get('end_len') is not None and special_elem.get('end') is not None:
            # if special markup is single (has no end regex)
            end_pos_data['start'] = special_elem['end']
            end_pos_data['len'] = special_elem['end_len']
            end_pos_data['end'] = end_pos_data['start'] + end_pos_data['len']
        else:
            end_regex = self.__get_first_regex(special_elem['end_regex'])
            if end_regex is not None:
                end_pos_data['start'] = end_regex['start']
                end_pos_data['len'] = len(end_regex['str'])
                end_pos_data['end'] = end_pos_data['start'] + end_pos_data['len']
        return end_pos_data

    def __get_next_special_element(self):
        # if self.next_special_elem and self.next_special_elem['start'] > self._wiki_text_pos:
        #     return self.next_special_elem
        # Get starting position of next special markup element
        next_ = {}
        for special_markup in SPECIAL_MARKUPS:
            found_markup = self.__get_first_regex(special_markup['start_regex'])
            if found_markup is not None and \
               (not next_ or next_['start'] > found_markup['start']) and \
               found_markup['start'] not in self._jumped_elems:
                next_ = special_markup
                next_['start'] = found_markup['start']
                next_['start_len'] = len(found_markup['str'])
                if next_['type'] == 'single':
                    # to be used in __get_special_elem_end - because it has no end regex
                    next_['end'] = next_['start']
                    next_['end_len'] = next_['start_len']
        # self.next_special_elem = next_
        return next_

    def __add_spans(self, token, new_span=True):
        """
        If there is an opened span and new_span is True, close previous span and start new span (no_spans=False)
        If there is an opened span and new_span is False, close previous span (no_spans=True)
        If there is not an opened span and new_span is True, start a new span (no_spans=False)
        If there is not an opened span and new_span is do nothing (no_spans=True)
        """
        if self._open_span is True:
            self.extended_wiki_text.write('</span>')
            self._open_span = False
        if new_span is True:
            self.extended_wiki_text.write('<span class="editor-token token-editor-{}" id="token-{}">'.\
                                       format(token['class_name'], self._token_index))
            self._open_span = True

    def __parse_wiki_text(self, add_spans=True, special_elem=None, no_jump=False):
        """
        There are 3 possible calls of this method in this algorithm.
        1) start of script and adding not special tokens with spans around into extended markup:
        add_spans is True, special_elem is None and no_jump is False: Start, add spans around tokens until reaching
        next special element. And jump into that element and process tokens inside that element.
        2) Handling special markup elements:
        add_spans is False, special_elem is not None and no_jump is True: Add each token until end of current special
        element into extended wiki text without spans.
        add_spans is False, special_elem is not None and no_jump is False: Add each token until end of current special
        element into extended wiki text without spans. If there is special element inside current special element,
        jump into that element and process tokens inside that element

        :param add_spans: Flag to decide adding spans around tokens.
        :param special_elem: Current special element that parser is inside.
        :param no_jump: Flag to decide jumping into next special element.
        :return: True if parsing is successful.
        """
        # Get end position of current special markup
        special_elem_end = self.__get_special_elem_end(special_elem) if special_elem else False
        if no_jump is False:
            # Get starting position of next special markup element in wiki text
            next_special_elem = self.__get_next_special_element()

        while self._wiki_text_pos < (len(self.wiki_text) - 1):
            if self.token is None:
                # No token left to parse
                # Add everything that's left to the end of the extended wiki text
                self.extended_wiki_text.write(self.wiki_text[self._wiki_text_pos: len(self.wiki_text)])
                self._wiki_text_pos = len(self.wiki_text)  # - 1
                return True

            # Don't jump anywhere if no_jump is set
            if no_jump is False and (not special_elem_end or self._wiki_text_pos < special_elem_end['start']):
                if next_special_elem and \
                   (not special_elem_end or next_special_elem['start'] < special_elem_end['start']) and \
                   next_special_elem['start'] < self.token['end']:
                    # Special markup element was found before or reaching into token
                    # Or token itself is a start of special markup
                    self._jumped_elems.add(next_special_elem['start'])

                    if add_spans:
                        # if no_spans=False, this special markup will have one span around with editor of first token
                        self.__add_spans(self.token, new_span=not next_special_elem['no_spans'])

                    # NOTE: add_spans=False => no spans will added inside special markups
                    self.__parse_wiki_text(add_spans=False,
                                           special_elem=next_special_elem,
                                           no_jump=next_special_elem['no_jump'])
                    if special_elem:
                        # _wiki_text_pos is updated, we have to update the end position of current special markup
                        special_elem_end = self.__get_special_elem_end(special_elem)
                    # Get starting position of next special markup element
                    next_special_elem = self.__get_next_special_element()
                    continue

            # Is it end of special element?
            if special_elem_end and special_elem_end['end'] < self.token['end']:
                # Special element has been matched before the token
                # => Set position to special element's end
                self.extended_wiki_text.write(self.wiki_text[self._wiki_text_pos:special_elem_end['end']])
                self._wiki_text_pos = special_elem_end['end']
                return True

            # Add sequence author tags around token
            if add_spans:
                self.__add_spans(self.token)  # close and open span tag

            # add remaining token (and possible preceding chars) to resulting altered markup
            self.extended_wiki_text.write(self.wiki_text[self._wiki_text_pos:self.token['end']])
            self._wiki_text_pos = self.token['end']

            # Increase token index
            self._token_index += 1
            # Get new token
            self.__set_token()

        # Close opened tags
        if self._open_span:
            self.extended_wiki_text.write("</span>")
            self._open_span = False
        return True

    def __parse(self):
        # Current WikiWho token
        self.__set_token()
        return self.__parse_wiki_text()

    def __set_present_editors(self):
        """
        Sort editors who owns tokens in given revision according to percentage of owned tokens in decreasing order.
        """
        self.present_editors = tuple(
            (editor_name, class_name, token_count*100.0/self.tokens_len)
            for editor_id, (editor_name, class_name, token_count) in
            sorted(self.present_editors.items(), key=lambda x: x[1][2], reverse=True)
        )

    def generate_extended_wiki_markup(self):
        """
        Parse wiki text and add spans around tokens if possible.
        Generate list of editors who are present in this article page including 3 information to be used in js code:
        editor name, class name and authorship scores.
        """
        # Add regex helper pattern into wiki text in order to keep newlines
        self.wiki_text = self.wiki_text.replace('\r\n', REGEX_HELPER_PATTERN).\
                                        replace('\n', REGEX_HELPER_PATTERN).\
                                        replace('\r', REGEX_HELPER_PATTERN)

        self.__parse()
        self.__set_present_editors()

        # Remove regex patterns
        self.wiki_text = self.wiki_text.replace(REGEX_HELPER_PATTERN, '\n')
        self.extended_wiki_text = self.extended_wiki_text.getvalue()
        self.extended_wiki_text = self.extended_wiki_text.replace(REGEX_HELPER_PATTERN, '\n')
