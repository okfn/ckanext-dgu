from setuptools import setup, find_packages

from ckanext.dgu import __version__

setup(
    name='ckanext-dgu',
    version=__version__,
    long_description="""\
    """,
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    namespace_packages=['ckanext', 'ckanext.dgu'],
    zip_safe=False,
    author='Open Knowledge Foundation',
    author_email='info@okfn.org',
    license='AGPL',
    url='http://ckan.org/',
    description='CKAN DGU extensions',
    keywords='data packaging component tool server',
    install_requires=[
        # List of dependencies is moved to pip-requirements.txt
        # to avoid conflicts with Debian packaging.
        #'swiss',
        #'ckanclient>=0.5',
        #'ckanext', when it is released
    ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    package_data={'ckan': ['i18n/*/LC_MESSAGES/*.mo']},
    entry_points="""
        [ckan.plugins]
        dgu_form_api = ckanext.dgu.plugin:FormApiPlugin
        dgu_form = ckanext.dgu.plugin:DguForm
        dgu_auth_api = ckanext.dgu.plugin:AuthApiPlugin
        form_api_tester = ckanext.dgu.testtools.form_api_tester:FormApiTester
        
        [console_scripts]
        ons_loader = ckanext.dgu.ons:load
        cospread_loader = ckanext.dgu.cospread:load
        change_licenses = ckanext.dgu.bin.change_licenses_cmd:command
        transfer_url = ckanext.dgu.bin.transfer_url_cmd:command
        ons_analysis = ckanext.dgu.bin.ons_analysis_cmd:command
        ofsted_fix = ckanext.dgu.bin.ofsted_fix_cmd:command        
        publisher_migration = ckanext.dgu.bin.publisher_migration:command
        metadata_v3_migration = ckanext.dgu.bin.metadata_v3_migration:command
        generate_test_organisations = ckanext.dgu.testtools.organisations:command
        ons_remove_resources = ckanext.dgu.bin.ons_remove_resources:command
        ons_remove_packages = ckanext.dgu.bin.ons_remove_packages:command
        ons_delete_resourceless_packages = ckanext.dgu.bin.ons_delete_resourceless_packages:command
        ons_uksa_data4nr = ckanext.dgu.bin.ons_uksa_data4nr:command
        dump_analysis = ckanext.dgu.bin.dump_analysis:command
        gov_daily = ckanext.dgu.bin.gov_daily:command
        sync_organisations = ckanext.dgu.bin.sync_organisations:command
        
        [ckan.forms]
        package_gov3 = ckanext.dgu.forms.package_gov3:get_gov3_fieldset

        [curate.actions]
        report=ckanext.dgu.curation:report

        [paste.paster_command]
        mock_drupal = ckanext.dgu.testtools.mock_drupal:Command
    """,
    test_suite = 'nose.collector',
)
