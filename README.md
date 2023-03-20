# Python Docs Parser

## Возможности

This standalone script is supposed to collect a number of Static/Dynamic Paths programmed on the ACI leaf.

The script should be called against ACI leaf where it polls fv.BDDef, fv.EpP and fv.IfConn only.

Collected data used to construct a dict of the following format:

```bash
  {
    BD_name: {
      EPG_list: [EPG1, EPG2, ...],
      MultiDstFlood: multiDstPktAct,
      Total_number_of_paths
    },
    BD_name: {...},
  }
``` 

Unconditionally resulting dictionary is used to build a table (prettyTable). At this point, args/options are not added.
To put code into perspective:

### fv.BDDef
```bash
  bdDn                     : uni/tn-abl-tenant/BD-abl-bd
  ...
  multiDstPktAct           : bd-flood
  ...
```  
### fv.EpP
```bash
  epgPKey        : uni/tn-abl-tenant/ap-abl-app/epg-vl-1200
  bdDefDn        : uni/bd-[uni/tn-abl-tenant/BD-abl-bd]-isSvc-no
  ...
```
### fv.IfConn
```bash
  ...
  dn               : uni/epp/fv-[uni/tn-abl-tenant/ap-abl-app/epg-vl-1200]/node-101/stpathatt-[N3k-1-VPC1-2]/conndef/conn-[vlan-1200]-[0.0.0.0]
  ...
```  

fv.EpP used to correlate BD with EPG
fv.IfConn provides connectivity parameters for an interface, hence representing programmed Intf/Vlan pair.
When done table will be printed where:
- Name of BD
- MultiDstFlood config
- The number of EPGs per BD listed.
- Total number of paths (static and dynamic) across all EPGs in a given BD

```bash
+------------------------------------+---------------+-------------+-------------+
|                            BD Name | MultiDstFlood | N.of EPG(s) | Total paths |
+------------------------------------+---------------+-------------+-------------+
|             tn-random/BD-BD-random |    bd-flood   |     550     |     1633    |
|                      tn-RD/BD-BD35 |    bd-flood   |      1      |      3      |
+------------------------------------+---------------+-------------+-------------+
```

## Instructions

Clone the repo

```bash
git clone https://github.com/ablusenkov/mc_cpu_scale.git
```

(Optional) Create virtual environment in a way similar to:
```bash
python3 -m venv venv
source venv/bin/activate
```

Install relations.

```bash
pip3 install -r requirements.txt
```

Run

```bash
python3 ./EPgSPath_standalone.py 
```

<h5 align="center">Автор: <a href="https://github.com/ablusenkov">Oleksandr Blusenkov</a></h5>