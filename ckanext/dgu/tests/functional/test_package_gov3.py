import re

from nose.tools import assert_raises

from pylons import config

from ckan.lib.helpers import json
from ckan.lib.helpers import literal
from ckan.lib.create_test_data import CreateTestData
from ckanext.dgu.forms.formapi import DrupalRequestError
from ckan.tests.functional.api.base import (Api1TestCase,
                                            Api2TestCase,
                                            ApiUnversionedTestCase)
from ckanext.dgu.tests.forms.test_form_api import BaseFormsApiCase
from ckanext.dgu.tests import *

package_form = 'package_gov3'

class FormsApiTestCase(BaseFormsApiCase, MockDrupalCase):

    @classmethod
    def setup(self):
        self.fixtures = Gov3Fixtures()
        self.fixtures.create()
        self.pkg_dict = self.fixtures.pkgs[0]
        self.package_name = self.pkg_dict['name']
        test_user = self.get_user_by_name(unicode(self.fixtures.user_name))
        self.extra_environ = {
            'Authorization' : str(test_user.apikey)
        }

    @classmethod
    def teardown(self):
        self.fixtures.delete()

    def test_get_package_create_form(self):
        form, ret_status = self.get_package_create_form(package_form=package_form)
        self.assert_formfield(form, 'Package--name', '')
        self.assert_formfield(form, 'Package--title', '')
        self.assert_not_formfield(form, 'Package--version', '')
        self.assert_formfield(form, 'Package--url', '')
        self.assert_formfield(form, 'Package--notes', '')
        self.assert_formfield(form, 'Package--resources-0-url', '')
        self.assert_formfield(form, 'Package--resources-0-format', '')
        self.assert_formfield(form, 'Package--resources-0-description', '')
        self.assert_formfield(form, 'Package--resources-0-id', '')
        self.assert_formfield(form, 'Package--author', '')
        self.assert_formfield(form, 'Package--author_email', '')
        self.assert_not_formfield(form, 'Package--maintainer', '')
        self.assert_not_formfield(form, 'Package--maintainer_email', '')
        self.assert_formfield(form, 'Package--license_id', '')
        self.assert_not_formfield(form, 'Package--extras-newfield0-key', '')
        self.assert_not_formfield(form, 'Package--extras-newfield0-value', '')
        self.assert_not_formfield(form, 'Package--extras-newfield1-key', '')
        self.assert_not_formfield(form, 'Package--extras-newfield1-value', '')
        self.assert_not_formfield(form, 'Package--extras-newfield2-key', '')
        self.assert_not_formfield(form, 'Package--extras-newfield2-value', '')
        self.assert_not_formfield(form, 'Package--extras-date_update_future-key', '')
        self.assert_not_formfield(form, 'Package--extras-date_update_future-value', '')

    def test_get_package_edit_form(self):
        package = self.get_package_by_name(self.package_name)
        form, ret_status = self.get_package_edit_form(package.id, package_form=package_form)
        prefix = 'Package-%s-' % package.id
        self.assert_formfield(form, prefix + 'name', package.name)
        self.assert_not_formfield(form, prefix + 'external_reference')
        self.assert_not_formfield(form, prefix + 'categories')
        expected_values = dict([(key, value) for key, value in package.extras.items()])
        expected_values['temporal_coverage-to'] = '6/2009'
        expected_values['temporal_coverage-from'] = '12:30 24/6/2008'
        expected_values['date_updated'] = '12:30 30/7/2009'
        expected_values['date_update_future'] = '1/7/2009'
        expected_values['date_released'] = '30/7/2009'
        expected_values['published_by'] = strip_organisation_id(expected_values['published_by'])
        expected_values['published_via'] = strip_organisation_id(expected_values['published_via'])
        del expected_values['national_statistic']
        del expected_values['geographic_coverage'] # don't test here
        del expected_values['external_reference']
        del expected_values['import_source']
        for key, value in expected_values.items():
            self.assert_formfield(form, prefix + key, value)

    def test_get_package_edit_form_restrict(self):
        package = self.get_package_by_name(self.package_name)
        form, ret_status = self.get_package_edit_form(package.id, package_form=package_form, restrict=1)
        prefix = 'Package-%s-' % package.id
        self.assert_not_formfield(form, prefix + 'national_statistic', package.name)
        self.assert_formfield(form, prefix + 'notes', package.notes)
        for key in ('national_statistic', ):
            value = package.extras[key]
            self.assert_not_formfield(form, prefix + key, value)
        

class TestFormsApi1(Api1TestCase, FormsApiTestCase): pass

class TestFormsApi2(Api2TestCase, FormsApiTestCase):

    def test_get_department_from_organisation_api(self):
        assert self.app.get('/api/2/util/publisher/2/department').body=='"7"',self.app.get('/api/2/util/publisher/2/department').body

class EmbeddedFormTestCase(BaseFormsApiCase, MockDrupalCase):
    '''Tests the form as it would be used embedded in dgu html.'''

    def setup(self):
        self.fixtures = Gov3Fixtures()
        self.fixtures.create()
        self.pkg_dict = self.fixtures.pkgs[0]
        self.package_name = self.pkg_dict['name']
        test_user = self.get_user_by_name(unicode(self.fixtures.user_name))
        self.extra_environ = {
            'Authorization' : str(test_user.apikey)
        }
        self.form = package_form

    def teardown(self):
        self.fixtures.delete()

    def _insert_into_field_tag(self, form_html, field_name, tag_name, tag_insertion):
        '''Finds the tag for a package field and inserts some html into it.'''
        form_html, num_replacements = re.subn(
            '(<%s[^>]* id="Package-.{0,36}-%s" .*) ?((value)|(name)=[^>]*>)' % \
            (tag_name, field_name),
            r'\1 class="disabled" readonly \2', form_html)
        assert num_replacements == 1, num_replacements
        return form_html

    def form_from_res(self, res):
        assert not "<html>" in str(res.body), "The response is an HTML doc, not just a form: %s" % str(res.body)
        res.body = '''
<html>
  </body>
    <form method="post">
        %s
        <input type="submit">
    </form>
  </body>
</html>
''' % res.body

        return res.forms[0]

    def test_submit_package_create_form_valid(self):
        package_name = u'new_name'
        CreateTestData.flag_for_deletion(package_name)
        assert not self.get_package_by_name(package_name)
        form, ret_status = self.get_package_create_form(package_form=self.form)
        res = self.post_package_create_form(form=form, package_form=self.form, name=package_name, published_by='National Health Service [1]', published_via='Department of Energy and Climate Change [4]', license_id='gfdl', notes='def', title='efg')
        self.assert_header(res, 'Location')
        assert (not res.body) or (not json.loads(res.body))
        self.assert_header(res, 'Location', 'http://localhost'+self.package_offset(package_name))
        pkg = self.get_package_by_name(package_name)
        assert pkg

    def test_submit_package_edit_form_valid(self):
        package_name = self.package_name
        pkg = self.get_package_by_name(package_name)
        new_title = u'New Title'
        form, ret_status = self.get_package_edit_form(pkg.id, package_form=self.form)
        res = self.post_package_edit_form(pkg.id, form=form, title=new_title, package_form=self.form)
        assert (not res.body) or (not json.loads(res.body)), res.body
        pkg = self.get_package_by_name(package_name)
        assert pkg.title == new_title, pkg

    def test_submit_package_edit_form_valid_restrict(self):
        package_name = self.package_name
        pkg = self.get_package_by_name(package_name)
        new_title = u'New Title'
        form, ret_status = self.get_package_edit_form(pkg.id, package_form=self.form, restrict=1)
        prefix = 'Package-%s-' % pkg.id
        self.assert_not_formfield(form, prefix + 'national_statistic', pkg.name)
        res = self.post_package_edit_form(pkg.id, form=form, title=new_title, package_form=self.form, restrict=1)
        assert (not res.body) or (not json.loads(res.body)), res.body
        pkg = self.get_package_by_name(package_name)
        assert pkg.title == new_title, pkg

    def test_package_create_form_invalid(self):
        # user 99 doesn't exist
        assert_raises(DrupalRequestError, self.get_package_create_form, \
                      package_form=self.form, user_id='99')

    def test_package_edit_form_invalid(self):
        package_name = self.package_name
        pkg = self.get_package_by_name(package_name)
        # user 99 doesn't exist
        assert_raises(DrupalRequestError, self.get_package_edit_form, \
                      pkg.id, package_form=self.form, user_id='99')

    def test_create_package(self):
        res, ret_status = self.get_package_create_form()
        # TODO finish this test

    # TODO add other tests in from test_form.py

class TestEmbeddedFormApi1(Api1TestCase, EmbeddedFormTestCase): pass

class TestEmbeddedFormApi2(Api2TestCase, EmbeddedFormTestCase): pass

class TestGeoCoverageBug(Api2TestCase, BaseFormsApiCase, MockDrupalCase):
    @classmethod
    def setup(self):
        self.user_name = u'tester1'
        self.pkg_dict = {"name": u"lichfield-councillors", "title": "Councillors", "version": None, "url": "http://www.lichfielddc.gov.uk/data", "author": "Democratic and Legal", "author_email": None, "maintainer": "Web Team", "maintainer_email": "webmaster@lichfielddc.gov.uk", "notes": "A list of Lichfield District Councillors, together with contact details, political party and committees", "license_id": "localauth-withrights", "license": "OKD Compliant::Local Authority Copyright with data.gov.uk rights", "tags": ["committees", "cool", "councillors", "democracy", "lichfield", "meetings"], "groups": ["ukgov"], "extras": {"temporal_coverage-from": "", "date_updated": "2010-03-29", "temporal_coverage_to": "", "import_source": "COSPREAD-cospread-2010-03-31mk2.csv", "geographical_granularity": "local authority", "temporal_granularity": "", "agency": "", "geographic_granularity": "", "temporal_coverage-to": "", "published_by": "Scotland Office", "precision": "", "temporal_coverage_from": "", "taxonomy_url": "", "mandate": "", "categories": "", "geographic_coverage": "010000: Scotland", "external_reference": "", "national_statistic": "no", "date_update_future": "", "update_frequency": "Daily", "date_released": "2009-08-01"}, "resources": [{"url": "http://www.lichfielddc.gov.uk/site/custom_scripts/councillors_xml.php?viewBy=name", "format": "Other XML", "description": "", "hash": ""}]}
        CreateTestData.create_arbitrary([self.pkg_dict], extra_user_names=[self.user_name])
        self.package_name = self.pkg_dict['name']

        test_user = self.get_user_by_name(unicode(self.user_name))
        self.extra_environ = {
            'Authorization' : str(test_user.apikey)
        }

    @classmethod
    def teardown(self):
        CreateTestData.delete()

    def test_edit_coverage(self):
        package = self.get_package_by_name(self.package_name)
        form, ret_status = self.get_package_edit_form(package.id, package_form=package_form)
        prefix = 'Package-%s-' % package.id
        self.assert_formfield(form, prefix + 'name', package.name)
        self.assert_formfield(form, prefix + 'geographic_coverage-england', None)
        self.assert_formfield(form, prefix + 'geographic_coverage-scotland', 'True')
        self.assert_formfield(form, prefix + 'geographic_coverage-wales', None)
        fields = {
            'geographic_coverage-england':True,
            'geographic_coverage-scotland':True,
            'geographic_coverage-wales':True,
            }
        res = self.post_package_edit_form(package.id, form=form, package_form=package_form, **fields)
        assert (not res.body) or (not json.loads(res.body)), res.body

        package = self.get_package_by_name(self.package_name)
        self.assert_equal(package.extras['geographic_coverage'], '111000: Great Britain (England, Scotland, Wales)')
        
