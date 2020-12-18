from WhoColor.utils import WikipediaRevText, WikiWhoRevContent
from WhoColor.parser import WikiMarkupParser


class WhoColorHandler(object):
    """
    Example handler to create WhoColor API response data.
    """

    def __init__(self, page_title=None, page_id=None, rev_id=None, language='en'):
        self.page_id = page_id
        self.page_title = page_title
        self.rev_id = rev_id
        self.language = language

    def __enter__(self):
        return self

    def handle(self):
        # get rev wiki text from wp
        wp_rev_text_obj = WikipediaRevText(self.page_title, self.page_id, self.rev_id, self.language)
        # {'page_id': , 'namespace': , 'rev_id': , 'rev_text': }
        rev_data = wp_rev_text_obj.get_rev_wiki_text()
        if rev_data is None or 'error' in rev_data or "-1" in rev_data:
            raise Exception('Problem with getting rev wiki text from wp.')

        # if rev_data['namespace'] != 0:
        #     raise Exception('Invalid namespace.')

        # get revision content (authorship data)
        ww_rev_content_obj = WikiWhoRevContent(page_id=rev_data['page_id'],
                                               rev_id=rev_data['rev_id'],
                                               language=self.language)
        # revisions {rev_id: [timestamp, parent_id, class_name/editor, editor_name]}
        # tokens [[conflict_score, str, o_rev_id, in, out, editor/class_name, age]]
        # biggest conflict score (int)

        revisions = ww_rev_content_obj.get_revisions_data()
        editor_names_dict = ww_rev_content_obj.get_editor_names(revisions)
        tokens, biggest_conflict_score = ww_rev_content_obj.get_tokens_data(revisions, editor_names_dict)

        # annotate authorship data to wiki text
        # if registered user, class name is editor id
        p = WikiMarkupParser(rev_data['rev_text'], tokens)
        p.generate_extended_wiki_markup()
        extended_html = wp_rev_text_obj.convert_wiki_text_to_html(p.extended_wiki_text)

        wikiwho_data = {'revisions': revisions,
                        'tokens': ww_rev_content_obj.convert_tokens_data(tokens),
                        'biggest_conflict_score': biggest_conflict_score}
        return extended_html, p.present_editors, wikiwho_data

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
