# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.common.provider import cleanup_vm
from cfme.services.catalogs.catalog_item import CatalogItem
from cfme.services.catalogs.catalog_item import CatalogBundle
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from cfme.web_ui import flash
from utils.log import logger
from utils.wait import wait_for
from utils import testgen
from utils.blockers import BZ

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('logged_in', 'vm_name', 'catalog_item', 'uses_infra_providers'),
    pytest.mark.long_running
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(
        metafunc, 'provisioning', template_location=["provisioning", "template"])

    new_idlist = []
    new_argvalues = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # No provisioning data available
            continue

        # required keys should be a subset of the dict keys set
        if not {'template', 'host', 'datastore'}.issubset(args['provisioning'].viewkeys()):
            # Need all three for template provisioning
            continue

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


def test_order_catalog_item(provider, setup_provider, catalog_item, request, register_event):
    """Tests order catalog item
    Metadata:
        test_flag: provision
    """
    vm_name = catalog_item.provisioning_data["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=1400, delay=20)
    assert row.last_message.text == 'Request complete'
    register_event(
        provider.get_yaml_data()['type'],
        "service", catalog_item.name, ["service_provision_complete"])


def test_order_catalog_item_via_rest(
        request, rest_api, provider, setup_provider, catalog_item, catalog):
    """Same as :py:func:`test_order_catalog_item`, but using REST.
    Metadata:
        test_flag: provision, rest
    """
    vm_name = catalog_item.provisioning_data["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider))
    catalog_item.create()
    request.addfinalizer(catalog_item.delete)
    catalog = rest_api.collections.service_catalogs.find_by(name=catalog)
    assert len(catalog) == 1
    catalog, = catalog
    template = catalog.service_templates.find_by(name=catalog_item.name)
    assert len(template) == 1
    template, = template
    req = template.action.order()

    @pytest.wait_for(timeout="15m", delay=5)
    def request_finished():
        req.reload()
        logger.info("Request status: %s, Request state: %s, Request message: %s",
            req.status, req.request_state, req.message)
        return req.status.lower() == "ok" and req.request_state.lower() == "finished"


def test_order_catalog_bundle(provider, setup_provider, catalog_item, request):
    """Tests ordering a catalog bundle
    Metadata:
        test_flag: provision
    """

    vm_name = catalog_item.provisioning_data["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    catalog_item.create()
    bundle_name = fauxfactory.gen_alphanumeric()
    catalog_bundle = CatalogBundle(name=bundle_name, description="catalog_bundle",
                   display_in=True, catalog=catalog_item.catalog, dialog=catalog_item.dialog)
    catalog_bundle.create([catalog_item.name])
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_bundle)
    logger.info('Waiting for cfme provision request for service %s', bundle_name)
    row_description = bundle_name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=1200, delay=20)
    assert row.last_message.text == 'Request complete'


# Note here this needs to be reduced, doesn't need to test against all providers
@pytest.mark.usefixtures('has_no_infra_providers')
def test_no_template_catalog_item(provider, setup_provider, provisioning, vm_name, dialog, catalog):
    """Tests no template catalog item
    Metadata:
        test_flag: provision
    """
    template, catalog_item_type = map(provisioning.get,
        ('template', 'catalog_item_type'))
    if provider.type == 'rhevm':
        catalog_item_type = "RHEV"
    item_name = fauxfactory.gen_alphanumeric()
    catalog_item = CatalogItem(item_type=catalog_item_type, name=item_name,
                  description="my catalog", display_in=True, catalog=catalog, dialog=dialog)
    catalog_item.create()
    flash.assert_message_match("'Catalog/Name' is required")


@pytest.mark.meta(blockers=[BZ(1210541, forced_streams=["5.4", "5.5", "upstream"])])
def test_edit_catalog_after_deleting_provider(provider, setup_provider, catalog_item):
    """Tests edit catalog item after deleting provider
    Metadata:
        test_flag: provision
    """
    catalog_item.create()
    provider.delete(cancel=False)
    catalog_item.update({'description': 'my edited description'})
    flash.assert_success_message('Service Catalog Item "{}" was saved'.format(
                                 catalog_item.name))


@pytest.mark.usefixtures('setup_provider')
def test_request_with_orphaned_template(provider, setup_provider, catalog_item):
    """Tests edit catalog item after deleting provider
    Metadata:
        test_flag: provision
    """
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog, catalog_item)
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    row_description = catalog_item.name
    cells = {'Description': row_description}
    provider.delete(cancel=False)
    provider.wait_for_delete()
    requests.go_to_request(cells)
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=1800, delay=20)
    assert row.status.text == 'Error'
