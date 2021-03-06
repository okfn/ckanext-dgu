import os

from nose.tools import assert_equal
from nose.plugins.skip import SkipTest
from pylons import config
from sqlalchemy.util import OrderedDict

from ckanext.dgu.ons import importer
from ckanext.dgu.ons.loader import OnsLoader
from ckanext.importlib.tests.test_loader import TestLoaderBase, USER
from ckan import model
from ckan.lib import search
from ckan.tests import CreateTestData, TestSearchIndexer, is_search_supported
from ckan.tests.wsgi_ckanclient import WsgiCkanClient
from ckanext.dgu.tests import MockDrupalCase, strip_organisation_id

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PATH = os.path.join(TEST_DIR, 'samples')
SAMPLE_FILEPATH_TEMPLATE = os.path.join(SAMPLE_PATH, 'ons_hub_sample%s.xml')
def sample_filepath(id):
    return SAMPLE_FILEPATH_TEMPLATE % id

if not is_search_supported():
    raise SkipTest("Search not supported")

class OnsLoaderBase(TestLoaderBase, MockDrupalCase):
    @classmethod
    def setup_class(self):
        search.clear()
        super(OnsLoaderBase, self).setup_class()

    @classmethod
    def teardown_class(self):
        super(OnsLoaderBase, self).teardown_class()

class TestOnsLoadBasic(OnsLoaderBase):
    lots_of_publishers = True
    
    @classmethod
    def setup_class(self):
        super(TestOnsLoadBasic, self).setup_class()
        importer_ = importer.OnsImporter(sample_filepath(''))
        self.pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]

        self.loader = OnsLoader(self.testclient)
        self.res = self.loader.load_packages(self.pkg_dicts)
        assert self.res['num_errors'] == 0, self.res

    def test_0_search_options(self):
        field_keys = ['title', 'published_by']

        pkg_dict = {'title':'titleA',
                    'extras':{'published_by':'Department for Children, Schools and Families'}}
        opts = self.loader._get_search_options(field_keys, pkg_dict)
        assert_equal(opts, [{'published_by': 'Department for Children, Schools and Families', 'title': 'titleA'}])

        pkg_dict = {'title':'titleA',
                    'extras':{'published_by':'',
                              'published_via':'SomeAgency'}}
        opts = self.loader._get_search_options(field_keys, pkg_dict)
        assert_equal(opts, [{'published_via':'SomeAgency', 'title': 'titleA'}])

    def test_1_hub_id_extraction(self):
        def assert_id(hub_id_value, expected_id):
            resource = {'description':'Some description',
                        'hub-id':hub_id_value}
            result = self.loader._get_hub_id(resource)
            assert_equal(result, expected_id)
        assert_id("119-46440",
                  "119-46440")

    def test_2_date_choose(self):
        def assert_id(date1, date2, earlier_or_later, expected_date_index):
            dates = (date1, date2)
            pkg0 = {'extras':{'date': date1}}
            result = self.loader._choose_date(pkg0, date2,
                                              earlier_or_later,
                                              'date')
            if not expected_date_index:
                assert_equal(result, expected_date_index)
            else:
                assert_equal(result, dates[expected_date_index - 1])
        assert_id('2010-12-01', '2010-12-02', 'earlier', 1)
        assert_id('2010-12-01', '2010-12-02', 'later', 2)
        assert_id('2010-12-02', '2010-12-01', 'earlier', 2)
        assert_id('2010-12-02', '2010-12-01', 'later', 1)
        assert_id('', '2010-12-02', 'earlier', 2)
        assert_id('2010-12-01', '', 'later', 1)
        assert_id('', '', 'earlier', None)

    def test_fields(self):
        q = model.Session.query(model.Package)
        names = [pkg.name for pkg in q.all()]
        pkg1 = model.Package.by_name(u'uk_official_holdings_of_international_reserves')
        cereals = model.Package.by_name(u'cereals_and_oilseeds_production_harvest')
        custody = model.Package.by_name(u'end_of_custody_licence_release_and_recalls')
        probation = model.Package.by_name(u'probation_statistics_brief')
        assert pkg1, names
        assert cereals, names
        assert custody, names
        assert probation, names
        assert pkg1.title == 'UK Official Holdings of International Reserves', pkg1.title
        assert pkg1.notes.startswith("Monthly breakdown for government's net reserves, detailing gross reserves and gross liabilities."), pkg1.notes
        assert len(pkg1.resources) == 1, pkg1.resources
        assert pkg1.resources[0].url == 'http://www.hm-treasury.gov.uk/national_statistics.htm', pkg1.resources[0]
        assert_equal(pkg1.resources[0].description, 'December 2009')
        assert_equal(pkg1.resources[0].extras['hub-id'], '119-36345')
        assert len(custody.resources) == 2, custody.resources
        assert custody.resources[0].url == 'http://www.justice.gov.uk/publications/endofcustodylicence.htm', custody.resources[0]
        assert_equal(custody.resources[0].description, 'November 2009')
        assert_equal(custody.resources[0].extras['hub-id'], '119-36836')
        assert custody.resources[1].url == 'http://www.justice.gov.uk/publications/endofcustodylicence.htm', custody.resources[0]
        assert_equal(custody.resources[1].description, 'December 2009')
        assert_equal(custody.resources[1].extras['hub-id'], '119-36838')
        assert pkg1.extras['date_released'] == u'2010-01-06', pkg1.extras['date_released']
        assert probation.extras['date_released'] == u'2010-01-04', probation.extras['date_released']
        assert_equal(strip_organisation_id(pkg1.extras['published_by']), u"Her Majesty's Treasury [some_number]")
        assert_equal(strip_organisation_id(cereals.extras['published_by']), u"Department for Environment, Food and Rural Affairs [some_number]")
        assert_equal(strip_organisation_id(custody.extras['published_by']), u"Ministry of Justice [some_number]")
        assert u"Source agency: HM Treasury" in pkg1.notes, pkg1.notes
        assert pkg1.extras['categories'] == 'Economy', pkg1.extras['category']
        assert pkg1.extras['geographic_coverage'] == '111100: United Kingdom (England, Scotland, Wales, Northern Ireland)', pkg1.extras['geographic_coverage']
        assert pkg1.extras['national_statistic'] == 'no', pkg1.extras['national_statistic']
        assert cereals.extras['national_statistic'] == 'yes', cereals.extras['national_statistic']
        assert custody.extras['national_statistic'] == 'no', custody.extras['national_statistic']
        assert 'Designation: Official Statistics not designated as National Statistics' in custody.notes
        assert pkg1.extras['geographical_granularity'] == 'UK and GB', pkg1.extras['geographical_granularity']
        assert 'Language: English' in pkg1.notes, pkg1.notes
        def check_tags(pkg, tags_list):            
            pkg_tags = [tag.name for tag in pkg.tags]
            for tag in tags_list:
                assert tag in pkg_tags, "Couldn't find tag '%s' in tags: %s" % (tag, pkg_tags)
        check_tags(pkg1, ('economics-and-finance', 'reserves', 'currency', 'assets', 'liabilities', 'gold', 'economy', 'government-receipts-and-expenditure', 'public-sector-finance'))
        check_tags(cereals, ('environment', 'farming'))
        check_tags(custody, ('public-order-justice-and-rights', 'justice-system', 'prisons'))
        assert 'Alternative title: UK Reserves' in pkg1.notes, pkg1.notes
        
        assert pkg1.extras['external_reference'] == u'ONSHUB', pkg1.extras['external_reference']
        assert 'Open Government Licence' in pkg.license.title, pkg.license.title
        assert pkg1.extras['update_frequency'] == u'monthly', pkg1.extras['update_frequency']
        assert custody.extras['update_frequency'] == u'monthly', custody.extras['update_frequency']
        assert pkg1.author == u"Her Majesty's Treasury", pkg1.author
        assert cereals.author == u'Department for Environment, Food and Rural Affairs', cereals.author
        assert custody.author == u'Ministry of Justice', custody.author

        for pkg in (pkg1, cereals, custody):
            assert pkg.extras['import_source'].startswith('ONS'), '%s %s' % (pkg.name, pkg.extras['import_source'])


class TestOnsLoadTwice(OnsLoaderBase):
    @classmethod
    def setup_class(self):
        super(TestOnsLoadTwice, self).setup_class()
        # sample_filepath(2 has the same packages as 1, but slightly updated
        for filepath in [sample_filepath(''), sample_filepath(2)]:
            importer_ = importer.OnsImporter(filepath)
            pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]
            loader = OnsLoader(self.testclient)
            res = loader.load_packages(pkg_dicts)
            assert res['num_errors'] == 0, res

    def test_packages(self):
        pkg = model.Package.by_name(u'uk_official_holdings_of_international_reserves')
        assert pkg.title == 'UK Official Holdings of International Reserves', pkg.title
        assert pkg.notes.startswith('CHANGED'), pkg.notes
        assert len(pkg.resources) == 1, pkg.resources
        assert 'CHANGED' in pkg.resources[0].description, pkg.resources


class TestOnsLoadClashTitle(OnsLoaderBase):
    # two packages with the same title, both from ONS,
    # but from different departments, so must be different packages

    lots_of_publishers = True
    
    @classmethod
    def setup_class(self):
        super(TestOnsLoadClashTitle, self).setup_class()
        # ons items have been split into 3 files, because search needs to
        # do indexing in between
        for suffix in 'abc':
            importer_ = importer.OnsImporter(sample_filepath('3' + suffix))
            pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]
            loader = OnsLoader(self.testclient)
            self.res = loader.load_packages(pkg_dicts)
            assert self.res['num_errors'] == 0, self.res

    def test_ons_package(self):
        pkg = model.Package.by_name(u'annual_survey_of_hours_and_earnings')
        assert pkg
        assert_equal(strip_organisation_id(pkg.extras.get('published_by')), 'Office for National Statistics [some_number]')
        assert 'Office for National Statistics' in pkg.notes, pkg.notes
        assert len(pkg.resources) == 2, pkg.resources
        assert '2007 Results Phase 3 Tables' in pkg.resources[1].description, pkg.resources
        assert '2007 Pensions Results' in pkg.resources[0].description, pkg.resources

    def test_welsh_package(self):
        pkg = model.Package.by_name(u'annual_survey_of_hours_and_earnings_')
        assert pkg
        assert_equal(strip_organisation_id(pkg.extras['published_by']), 'Welsh Government [some_number]')
        assert len(pkg.resources) == 1, pkg.resources
        assert '2008 Results' in pkg.resources[0].description, pkg.resources


class TestOnsLoadClashSource(OnsLoaderBase):
    # two packages with the same title, and department, but one not from ONS,
    # so must be different packages
    @classmethod
    def setup_class(self):
        super(TestOnsLoadClashSource, self).setup_class()

        self.clash_name = u'cereals_and_oilseeds_production_harvest'
        CreateTestData.create_arbitrary([
            {'name':self.clash_name,
             'title':'Test clash',
             'extras':{
                 'published_by':'Department for Environment, Food and Rural Affairs',
                 'import_source':'DECC-Jan-09',
                 },
             }
            ])
        importer_ = importer.OnsImporter(sample_filepath(''))
        pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]
        loader = OnsLoader(self.testclient)
        self.res = loader.load_packages(pkg_dicts)
        assert self.res['num_errors'] == 0, self.res

    def test_names(self):
        pkg1 = model.Package.by_name(self.clash_name)
        assert pkg1.title == u'Test clash', pkg1.title

        pkg2 = model.Package.by_name(self.clash_name + u'_')
        assert pkg2.title == u'Cereals and Oilseeds Production Harvest', pkg2.title

class TestOnsLoadSeries(OnsLoaderBase):
    @classmethod
    def setup_class(self):
        super(TestOnsLoadSeries, self).setup_class()
        for filepath in [sample_filepath('4a'), sample_filepath('4b')]:
            importer_ = importer.OnsImporter(filepath)
            pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]
            for pkg_dict in pkg_dicts:
                assert pkg_dict['title'] == 'Regional Labour Market Statistics', pkg_dict
                assert_equal(strip_organisation_id(pkg_dict['extras']['published_by']),
                             'Office for National Statistics [some_number]')
                assert '2010-08-' in pkg_dict['extras']['date_released'], pkg_dict
                assert pkg_dict['extras']['date_updated'] == '', pkg_dict
            loader = OnsLoader(self.testclient)
            res = loader.load_packages(pkg_dicts)
            assert res['num_errors'] == 0, res

    def test_packages(self):
        pkg = model.Package.by_name(u'regional_labour_market_statistics')
        assert pkg
        assert pkg.title == 'Regional Labour Market Statistics', pkg.title
        assert_equal(strip_organisation_id(pkg.extras['published_by']), 'Office for National Statistics [some_number]')
        assert len(pkg.resources) == 9, pkg.resources
        assert_equal(pkg.extras['date_released'], '2010-08-10')
        assert_equal(pkg.extras['date_updated'], '2010-08-13')

class TestOnsLoadMissingDept(OnsLoaderBase):
    # existing package to be updated has no department given (previously
    # there was no default to 'UK Statistics Authority'.
    @classmethod
    def setup_class(self):
        super(TestOnsLoadMissingDept, self).setup_class()

        self.orig_pkg_dict = {
             "name": u"measuring_subjective_wellbeing_in_the_uk",
             "title": "Measuring Subjective Wellbeing in the UK",
             "notes": "This report reviews:\n\nWhat is subjective wellbeing and why should we measure it?\n\nHow subjective wellbeing is currently measured in the UK - what subjective wellbeing questions are already being asked on major social surveys in the UK\n\nThe potential uses of subjective wellbeing data collected via these surveys\n\n\nIt concludes that subjective wellbeing is a valid construct that can be measured reliably. This is the first output of ONS' work on subjective wellbeing.\n\nSource agency: Office for National Statistics\n\nDesignation: Supporting material\n\nLanguage: English\n\nAlternative title: Working Paper: Measuring Subjective Wellbeing in the UK",
             "license_id": "ukcrown-withrights",
             "tags": ["communities", "health-well-being-and-care", "people-and-places", "societal-wellbeing", "subjective-wellbeing-subjective-well-being-objective-measures-subjective-measures", "well-being"],
             "groups": [],
             "extras": {"geographic_coverage": "111100: United Kingdom (England, Scotland, Wales, Northern Ireland)", "geographical_granularity": "UK and GB", "external_reference": "ONSHUB", "temporal_granularity": "", "date_updated": "", "precision": "", "temporal_coverage_to": "", "temporal_coverage_from": "", "national_statistic": "no", "import_source": "ONS-ons_data_7_days_to_2010-09-17", "published_by": 'Office for National Statistics [8]', "update_frequency": "", "date_released": "2010-09-14", "categories": "People and Places"},
            "resources": [{"url": "http://www.ons.gov.uk/about-statistics/measuring-equality/wellbeing/news-and-events/index.html", "format": "", "description": "2010", "extras":{"hub-id":"77-31166"}}],
             }
        CreateTestData.create_arbitrary([self.orig_pkg_dict])

        # same data is imported, but should find record and add department
        importer_ = importer.OnsImporter(sample_filepath(5))
        self.pkg_dict = [pkg_dict for pkg_dict in importer_.pkg_dict()][0]
        loader = OnsLoader(self.testclient)
        self.res = loader.load_package(self.pkg_dict)

    def test_reload(self):
        # Check that another package has not been created
        assert self.pkg_dict['name'] == self.orig_pkg_dict['name'], self.pkg_dict['name']
        pkg1 = model.Package.by_name(self.orig_pkg_dict['name'])

        assert_equal(strip_organisation_id(pkg1.extras.get('published_by')), u'Office for National Statistics [some_number]')


class TestNationalParkDuplicate(OnsLoaderBase):
    @classmethod
    def setup_class(self):
        super(TestNationalParkDuplicate, self).setup_class()
        filepath = sample_filepath(6)
        importer_ = importer.OnsImporter(filepath)
        pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]
        self.name = u'national_park_parliamentary_constituency_and_ward_level_mid-year_population_estimates_experimental'
        for pkg_dict in pkg_dicts:
            assert pkg_dict['name'] == self.name, pkg_dict['name']
            assert pkg_dict['title'] == 'National Park, Parliamentary Constituency and Ward level mid-year population estimates (experimental)', pkg_dict
            assert_equal(strip_organisation_id(pkg_dict['extras']['published_by']), 'Office for National Statistics [some_number]')
            assert pkg_dict['extras']['published_via'] == '', pkg_dict
        loader = OnsLoader(self.testclient)
        res = loader.load_packages(pkg_dicts)
        assert res['num_errors'] == 0, res

    def test_packages(self):
        names = [pkg.name for pkg in model.Session.query(model.Package).all()]
        assert_equal(names, [self.name])
        pkg = model.Package.by_name(self.name)
        assert pkg
        assert len(pkg.resources) == 3, pkg.resources

class TestDeathsOverwrite(OnsLoaderBase):
    @classmethod
    def setup_class(self):
        super(TestDeathsOverwrite, self).setup_class()
        self.orig_pkg_dict = {
            "name": u"weekly_provisional_figures_on_deaths_registered_in_england_and_wales",
            "title": "Weekly provisional figures on deaths registered in England and Wales",
            "version": None, "url": None, "author": "Office for National Statistics", "author_email": None, "maintainer": None, "maintainer_email": None,
            "notes": "Weekly death figures provide provisional counts of the number of deaths registered in England and Wales in the latest four weeks for which data are available up to the end of 2009. From week one 2010 the latest eight weeks for which data are available will be published.\n\nSource agency: Office for National Statistics\n\nDesignation: National Statistics\n\nLanguage: English\n\nAlternative title: Weekly deaths",
            "license_id": "ukcrown-withrights",
            "tags": ["death", "deaths", "life-events", "life-in-the-community", "mortality-rates", "population", "weekly-deaths"],
            "groups": [], "extras": {
                "geographic_coverage": "101000: England, Wales",
                "geographical_granularity": "Country",
                "external_reference": "ONSHUB",
                "temporal_coverage-from": "",
                "temporal_granularity": "",
                "date_updated": "",
                "series": "Weekly provisional figures on deaths registered in England and Wales",
                "published_via": "",
                "precision": "",
                "geographic_granularity": "",
                "temporal_coverage_to": "",
                "temporal_coverage_from": "",
                "taxonomy_url": "",
                "import_source": "ONS-ons_data_60_days_to_2010-09-22",
                "date_released": "2010-08-03",
                "temporal_coverage-to": "",
                "published_by": "Office for National Statistics [8]",
                "update_frequency": "",
                "national_statistic": "yes",
                "categories": "Population"},
            "resources": [
                {"url": "http://www.statistics.gov.uk/StatBase/Prep/9684.asp", "format": "", "description": "17/07/2009", "hash": "", "extras": {"hub-id": "77-27942"} }],
            }

        CreateTestData.create_arbitrary([self.orig_pkg_dict])

        # same data is imported, but should find record and add department
        importer_ = importer.OnsImporter(sample_filepath(7))
        self.pkg_dict = [pkg_dict for pkg_dict in importer_.pkg_dict()][0]
        loader = OnsLoader(self.testclient)
        print self.pkg_dict
        self.res = loader.load_package(self.pkg_dict)
        self.name = self.orig_pkg_dict['name']

    def test_packages(self):
        names = [pkg.name for pkg in model.Session.query(model.Package).all()]
        assert_equal(names, [self.name])
        pkg = model.Package.by_name(self.name)
        assert pkg
        assert len(pkg.resources) == 2, pkg.resources

class TestAgencyFind(OnsLoaderBase):
    lots_of_publishers = True
    
    @classmethod
    def setup_class(self):
        super(TestAgencyFind, self).setup_class()
        self.orig_pkg_dict = {
            "name": u"national_child_measurement_programme",
            "title": "National Child Measurement Programme",
            "version": None, "url": None, "author": None, "author_email": None, "maintainer": None, "maintainer_email": None,
            "notes": "The National Child Measurement Programme weighs and measures primary school children.\r\nThis publication was formerly announced as \"National Child Measurement Programme - Statistics on Child Obesity 2008-09\" but the title has been amended to reflect suggestions from the UKSA Assessments Board.\r\nSource agency: Information Centre for Health and Social Care\r\nDesignation: National Statistics\r\nLanguage: English\r\nAlternative title: National Child Measurement Programme",
            "license_id": "uk-ogl",
            "tags": ["health", "health-and-social-care", "health-of-the-population", "lifestyles-and-behaviours", "nhs", "well-being-and-care"],
            "groups": [],
            "extras": {
                "geographic_coverage": "100000: England",
                "geographical_granularity": "Country",
                "external_reference": "ONSHUB",
                "temporal_coverage-from": "",
                "temporal_granularity": "",
                "date_updated": "",
                "precision": "",
                "geographic_granularity": "",
                "temporal_coverage_to": "",
                "temporal_coverage_from": "",
                "taxonomy_url": "",
                "import_source": "ONS-ons_data_2009-12",
                "date_released": "2009-12-10",
                "temporal_coverage-to": "",
                "published_by": u"NHS Information Centre for Health and Social Care [16121]",
                "update_frequency": "",
                "national_statistic": "yes",
                "categories": "Health and Social Care"},
            "resources": [{"url": "http://www.ic.nhs.uk/ncmp", "format": "", "description": "England, 2008/09 School Year", "extras":{"hub-id":"119-37085"}},
                          {"url": "http://www.dh.gov.uk/en/Publichealth/Healthimprovement/Healthyliving/DH_073787", "format": "", "description": "2008", "extras":{"hub-id":"119-31792"}},
                          {"url": "http://www.ic.nhs.uk/ncmp", "format": "", "description": "Statistics on child obesity 2007-08", "extras":{"hub-id":"119-31784"}}],
            }

        CreateTestData.create_arbitrary([self.orig_pkg_dict])

        # same data is imported, but should find record and add department
        importer_ = importer.OnsImporter(sample_filepath(8))
        self.pkg_dict = [pkg_dict for pkg_dict in importer_.pkg_dict()][0]
        assert self.pkg_dict['extras']['published_by'].startswith('NHS Information Centre for Health and Social Care')
        assert_equal(self.pkg_dict['extras']['published_via'], '')
        loader = OnsLoader(self.testclient)
        print self.pkg_dict
        # load package twice, to ensure reload works too
        self.res = loader.load_package(self.pkg_dict)
        self.res = loader.load_package(self.pkg_dict)
        self.name = self.orig_pkg_dict['name']
        self.num_resources_originally = len(self.orig_pkg_dict['resources'])

    def test_packages(self):
        names = [pkg.name for pkg in model.Session.query(model.Package).all()]
        assert_equal(names, [self.name])
        pkg = model.Package.by_name(self.name)
        assert pkg
        assert_equal(len(pkg.resources), self.num_resources_originally + 1)

    def test_resources_sorted(self):
        pkg = model.Package.by_name(self.name)
        hub_ids = [int(res.extras['hub-id'].replace('-', '')) for res in pkg.resources]
        assert_equal(hub_ids, sorted(hub_ids))


class TestDeletedDecoyWhenAdmin(OnsLoaderBase):
    @classmethod
    def setup_class(self):
        super(TestDeletedDecoyWhenAdmin, self).setup_class()
        self.tsi = TestSearchIndexer()
        self.orig_pkg_dict = {
            "name": u"quarterly_epidemiological_commentary",
            "title": "Quarterly Epidemiological Commentary",
            "version": None, "url": None, "author": None, "author_email": None, "maintainer": None, "maintainer_email": None,
            "notes": "Epidemiological analyses of Mandatory surveillance data on MRSA bacteraemia and C. difficile infection covering at least nine quarters\r\nSource agency: Health Protection Agency\r\nDesignation: Official Statistics not designated as National Statistics\r\nLanguage: English\r\nAlternative title: Quarterly Epi Commentary",
            "license_id": "uk-ogl",
            "tags": ["conditions-and-diseases", "health", "health-and-social-care", "health-of-the-population", "nhs-trust-hcai-pct-mrsa-mrsa-bacteraemia-c-difficile-c-diff-clostridium-difficile-healthcare-associa", "well-being-and-care"],
            "groups": [],
            "extras": {
                "geographic_coverage": "100000: England",
                "geographical_granularity": "Other",
                "external_reference": "ONSHUB",
                "temporal_coverage-from": "",
                "temporal_granularity": "",
                "date_updated": "",
                "precision": "",
                "geographic_granularity": "",
                "temporal_coverage_to": "",
                "temporal_coverage_from": "",
                "taxonomy_url": "",
                "import_source": "ONS-ons_data_7_days_to_2010-06-23",
                "date_released": "2010-06-18",
                "temporal_coverage-to": "",
                "published_by": "Department of Health",
                "published_via": "Health Protection Agency",
                "update_frequency": "quarterly",
                "national_statistic": "no",
                "categories": "Health and Social Care"
                },
            "resources": []            
            }
        self.deleted_decoy_pkg_dict = {
            "name": u"quarterly_epidemiological_commentary_-_none",
            "title": "Quarterly Epidemiological Commentary",
            "extras": {
                "published_via": "Health Protection Agency",
                "published_by": "Department of Health",
                },
            }
        CreateTestData.create_arbitrary([self.orig_pkg_dict])
        CreateTestData.create_arbitrary([self.deleted_decoy_pkg_dict],
                                        extra_user_names=[u'testsysadmin'])

        # make a sysadmin user
        rev = model.repo.new_revision()
        testsysadmin = model.User.by_name(u'testsysadmin')
        model.add_user_to_role(testsysadmin, model.Role.ADMIN, model.System())

        # delete decoy
        decoy_pkg = model.Package.by_name(self.deleted_decoy_pkg_dict['name'])
        assert decoy_pkg
        decoy_pkg.delete()
        model.repo.commit_and_remove()

        self.tsi.index()

        # same data is imported, but should find record and add department
        importer_ = importer.OnsImporter(sample_filepath(9))
        self.pkg_dict = [pkg_dict for pkg_dict in importer_.pkg_dict()][0]

    @classmethod
    def teardown(self):
        search.clear()

    def test_load(self):
        user = model.User.by_name(u'testsysadmin')
        assert user
        testclient_admin = WsgiCkanClient(self.app, api_key=user.apikey)
        loader = OnsLoader(testclient_admin)
        print self.pkg_dict
        self.res = loader.load_package(self.pkg_dict)
        self.name = self.orig_pkg_dict['name']
        self.decoy_name = self.deleted_decoy_pkg_dict['name']
        self.num_resources_originally = len(self.orig_pkg_dict['resources'])

        names = [pkg.name for pkg in model.Session.query(model.Package).all()]
        assert_equal(set(names), set((self.name, self.decoy_name)))
        pkg = model.Package.by_name(self.name)
        assert pkg
        assert_equal(len(pkg.resources), self.num_resources_originally + 1)

class TestOnsUnknownPublisher(OnsLoaderBase):
    @classmethod
    def setup_class(self):
        super(TestOnsUnknownPublisher, self).setup_class()
        for filepath in (sample_filepath('10'),):
            importer_ = importer.OnsImporter(filepath)
            pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]
            assert_equal(len(pkg_dicts), 1)
            pkg_dict = pkg_dicts[0]
            assert_equal(pkg_dict['title'], 'NHS Cancer Waiting Times in Wales')
            assert_equal(pkg_dict['extras']['published_by'], '')
            assert_equal(pkg_dict['extras']['published_via'], '')
            loader = OnsLoader(self.testclient)
            res = loader.load_packages(pkg_dicts)
            assert res['num_errors'] == 0, res

    def test_packages(self):
        pkg = model.Package.by_name(u'nhs_cancer_waiting_times_in_wales')
        assert pkg
        assert_equal(pkg.title, 'NHS Cancer Waiting Times in Wales')
        assert_equal(pkg.extras['published_by'], '')
        assert_equal(pkg.extras['published_via'], '')

class TestReloadUnknownPublisher(OnsLoaderBase):
    @classmethod
    def setup_class(self):
        super(TestReloadUnknownPublisher, self).setup_class()
        for filepath in (sample_filepath('10'), sample_filepath('10')):
            importer_ = importer.OnsImporter(filepath)
            pkg_dicts = [pkg_dict for pkg_dict in importer_.pkg_dict()]
            assert_equal(len(pkg_dicts), 1)
            loader = OnsLoader(self.testclient)
            res = loader.load_packages(pkg_dicts)
            assert res['num_errors'] == 0, res

    def test_packages(self):
        pkg = model.Package.by_name(u'nhs_cancer_waiting_times_in_wales')
        assert pkg
        pkg = model.Package.by_name(u'nhs_cancer_waiting_times_in_wales_')
        assert not pkg
