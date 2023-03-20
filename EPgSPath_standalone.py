"""
This standalone script is supposed to collect a number of Static/Dynamic Paths programmed on the ACI leaf.
The script should be called against ACI leaf where it polls fv.BDDef, fv.EpP and fv.IfConn only.
Collected data used to construct a dict of the following format:

  {
    BD_name: {
      EPG_list: [EPG1, EPG2, ...],
      MultiDstFlood: multiDstPktAct,
      Total_number_of_paths

    },
    BD_name: {...},
  }

Unconditionally resulting dictionary is used to build a table (prettyTable). At this point, args/options are not added.
To put code into perspective:

  # fv.BDDef
  bdDn                     : uni/tn-abl-tenant/BD-abl-bd
  ...
  multiDstPktAct           : bd-flood
  ...

  # fv.EpP
  epgPKey        : uni/tn-abl-tenant/ap-abl-app/epg-vl-1200
  bdDefDn        : uni/bd-[uni/tn-abl-tenant/BD-abl-bd]-isSvc-no
  ...

  # fv.IfConn
  ...
  dn               : uni/epp/fv-[uni/tn-abl-tenant/ap-abl-app/epg-vl-1200]/node-101/stpathatt-[N3k-1-VPC1-2]/conndef/conn-[vlan-1200]-[0.0.0.0]
  ...

fv.EpP used to correlate BD with EPG
fv.IfConn provides connectivity parameters for an interface, hence representing programmed Intf/Vlan pair.

When done table will be printed where:
- Name of BD
- MultiDstFlood config
- The number of EPGs per BD listed.
- Total number of paths (static and dynamic) across all EPGs in a given BD

"""

import re
import requests
import urllib3

from getpass import getpass
from prettytable import PrettyTable

# Disabling an Insecure Request Warnings triggered by self signed cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

leaf_address = str(input('LEAF OOB address: '))
apic_username = str(input('Username: '))
apic_password = str(getpass('Password: '))


URL_AUTH = f'https://{leaf_address}/api/aaaLogin.json'
URL_LEAD = f'https://{leaf_address}/api/node/class'

POST = 'post'
GET = 'get'
AUTH_BODY = {
    'aaaUser': {
        'attributes':
            {
                'name': apic_username,
                'pwd': apic_password
            }
        }
    }


def api_call(method, url, body=None, cookies=None):
    """
    API call handler.
    :param method: CRUD method
    :param url: compleat url
    :param body: dict of body
    :param cookies: dict of coockies
    :return: .json of response on success or False+error code
    """

    if method == GET:
        try:
            response = requests.get(url=url,
                                     json=body,
                                     cookies=cookies,
                                     verify=False)
        except requests.RequestException:
            return 'Some network error...'

    if method == POST:
        try:
            response = requests.post(url=url,
                                     json=body,
                                     cookies=None,
                                     verify=False)
        except requests.RequestException:
            return 'Some network error...'

    if response.status_code == 200:
        return response.json()
    return False, response.status_code


def gen_dict_extract(var, key):
    """
    Nested dictionary lookup.
    :param var: dict with possibly embedded dict(s)
    :param key: key to look for
    :return: gen result, which to be yield for processing
    """

    if hasattr(var, 'items'):
        for k, v in var.items():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in gen_dict_extract(v, key):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(d, key):
                        yield result


if __name__ == '__main__':
    # retrieve an access token for further API calls
    access_reply = api_call(POST, URL_AUTH, AUTH_BODY)

    if False in access_reply:
        print(f'Auth request has failed with {access_reply[1]} error.')

    else:
        access_token = next(gen_dict_extract(access_reply, 'token'))
        cookie = {'APIC-cookie': access_token}

        url_bddef = f'{URL_LEAD}/fvBDDef.json?&order-by=fvBDDef.dn|desc'
        response = api_call(GET, url_bddef, cookies=cookie)
        attributes = response.get('imdata')

        result = {}
        epg_list = []

        # Create a result dict, prepopulated with a list for EPGs
        # And total number of Static/Dynamic paths
        if attributes:
            for item in attributes:
                single_result = []
                bdDn = gen_dict_extract(item, 'bdDn')
                multiDstPktAct = gen_dict_extract(item, 'multiDstPktAct')
                result[next(bdDn)] = {
                    'multiDstPktAct': next(multiDstPktAct),
                    'epgPKey': [],
                    'SPath': 0,
                }

        url_epp = f'{URL_LEAD}/fvEpP.json?&order-by=fvEpP.dn|desc'
        response = api_call(GET, url_epp, cookies=cookie)
        attributes = response.get('imdata')

        if attributes:
            for item in attributes:
                bdDefDn = gen_dict_extract(item, 'bdDefDn')
                # extracting DN of the BD from the bdDefDn
                dn = re.split(r'[\[\]]', next(bdDefDn), maxsplit=2)[1]
                epgPKey = gen_dict_extract(item, 'epgPKey')
                result[dn]['epgPKey'].append(next(epgPKey))

        url_ifconn = f'{URL_LEAD}/fvIfConn.json?&order-by=fvIfConn.dn|desc'
        response = api_call(GET, url_ifconn, cookies=cookie)
        attributes = response.get('imdata')

        path_counter = {}

        if attributes:
            for item in attributes:
                dn = gen_dict_extract(item, 'dn')
                # extracting dn of the EPG
                dn_epg = re.split(r'[\[\]]', next(dn), maxsplit=2)[1]
                if dn_epg in path_counter:
                    path_counter[dn_epg] += 1
                else:
                    path_counter[dn_epg] = 1

        for bd in result:
            for epg in path_counter:
                if epg in result[bd]['epgPKey']:
                    result[bd]['SPath'] += path_counter[epg]

        # Create a table
        # Dict needs to be reconstructed
        table = PrettyTable()
        table.field_names = [
            "BD Name",
            "MultiDstFlood",
            "N.of EPG(s)",
            "Total paths"
        ]

        for item, inner_value in result.items():
            row = [
                item.split('uni/')[1],
                inner_value['multiDstPktAct'],
                len(inner_value['epgPKey']),
                inner_value['SPath']
            ]
            table.add_row(row)

        table.align['BD Name'] = 'r'
        print(table.get_string(sortby="Total paths", reversesort=True))
