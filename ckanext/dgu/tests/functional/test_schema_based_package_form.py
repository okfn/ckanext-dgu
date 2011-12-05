"""
Tests the package form

The new package form is being refactored so as not to use sqlalchemy.  These
are the tests for this form.  For tests based on the sqlaclhemy-based form,
see 'test_package_gov3.py'.
"""

from ckanext.dgu.tests import Gov3Fixtures

from ckan.tests import WsgiAppCase, CommonFixtureMethods
from ckan.tests.html_check import HtmlCheckMethods

def url_for(**kwargs):
    """
    TODO: why isn't the real url_for picking up the correct route?
    """
    from ckan.tests import url_for as _url_for
    url = _url_for(**kwargs)
    return url.replace('dataset','package')

class TestFormRendering(WsgiAppCase, HtmlCheckMethods, CommonFixtureMethods):
    """
    Tests that the various fields are represeted correctly in the form.
    """

    # input name -> (Label text , input type)
    _expected_fields = {
        # Basic information
        'title':     ('Title *', 'input'),
        'name':      ('Identifier *', 'input'),
        'notes':     ('Abstract *', 'textarea'),
        
        # Details
        'date_released':                ('Date released', 'input'),
        'date_updated':                 ('Date updated', 'input'),
        'date_update_future':           ('Date to be published', 'input'),
        'update_frequency':             ('Update frequency', 'select'),
        'update_frequency-other':       ('Other:', 'input'),
        'precision':                    ('Precision', 'input'),
        'geographic_granularity':       ('Geographic granularity', 'select'),
        'geographic_granularity-other': ('Other', 'input'),
        'geographic_coverage':          ('Geographic coverage', 'input'),
        'temporal_granularity':         ('Temporal granularity', 'select'),
        'temporal_granularity-other':   ('Other', 'input'),
        'temporal_coverage':            ('Temporal coverage', 'input'),
        'url':                          ('URL', 'input'),
        'taxonomy_url':                 ('Taxonomy URL', 'input'),

        # Resources
        # ... test separately

        # More details
        'published_by':         ('Published by *', 'select'),
        'published_via':        ('Published via', 'select'),
        'author':               ('Contact', 'input'),
        'author_email':         ('Contact email', 'input'),
        'mandate':              ('Mandate', 'input'),
        'license_id':           ('Licence *', 'select'),
        'tag_string':           ('Tags', 'input'),
        'national_statistic':   ('National Statistic', 'input'),

        # After fieldsets
        'log_message':  ('Edit summary', 'textarea'),

    }

    @classmethod
    def setup(self):
        """
        Create standard gov3 test fixtures for this suite.

        This test class won't be editing any packages, so it's ok to only
        create these fixtures once.
        """
        self.fixtures = Gov3Fixtures()
        self.fixtures.create()

    @classmethod
    def teardown(self):
        """
        Cleanup the Gov3Fixtures
        """
        self.fixtures.delete()

    def test_new_form_has_all_fields(self):
        """
        Asserts that a form for a new package contains the various expected fields
        """
        offset = url_for(controller='package', action='new')
        response = self.app.get(offset)

        # quick check that we're checking the correct url
        assert "package" in offset

        for field, (label_text, input_type) in self._expected_fields.items():

            # e.g. <label for="title">Title *</label>
            self.check_named_element(response.body,
                                     'label',
                                     'for="%s"' % field,
                                     label_text)

            # e.g. <input name="title">
            self.check_named_element(response.body,
                                     input_type,
                                     'name="%s' % field)

    def test_edit_form_form_has_all_fields(self):
        """
        Asserts that edit-form of a package has the fields prefilled correctly.
        """

        package = self.fixtures.pkgs[0]

        offset = url_for(controller='package', action='edit', id=package['name'])
        response = self.app.get(offset)

        # form field name => expected form field value
        expected_field_values = {}

        # populate expected_field_values with the simple fields first
        for field_name in self._expected_fields:
            try:
                expected_value = package[field_name]
                if isinstance(expected_value, basestring):
                    expected_field_values[field_name] = expected_value
            except KeyError:
                pass

        # populate expected_field_values for tag_string and license_id
        # by hand, as the field names in the package dict don't follow the
        # same naming scheme as the form fields.
        expected_field_values['tag_string'] = package['tags']
        expected_field_values['license_id'] = package['license']

        # TODO: uncomment out the next line to test that the values
        #       stored as extras get promoted to having dedicated
        #       form fields, rather than the generated "key:value" fields.
        # expected_field_values.update(package['extras'].items())
    
        for field_name, expected_value in expected_field_values.items():
            self.check_named_element(response.body,
                                     '(input|textarea)',
                                     'name="%s"' % field_name,
                                     expected_value)

