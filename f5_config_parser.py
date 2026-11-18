import argparse
import yaml
from pprint import pprint
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

parser = argparse.ArgumentParser(description='F5 Config parser')
parser.add_argument('-i', '--input', type=str, help='Input F5 config file in configs directory', default='config.txt')
parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
# parser.add_argument('-l', '--ltmhagroup', type=str, help='Input LTMHAGroup', required=True)
args = parser.parse_args()

def virtual_parser(obj):
    res = {}
    rules_list = []
    virtual_dn = ""
    object_subsection = ""
    for b, l in obj:
        if not virtual_dn:
            virtual_dn = l.split()[2]
            if "/" not in virtual_dn:
                virtual_dn = "/Common/" + virtual_dn
            _, virtual_partition, virtual_name = virtual_dn.split("/")
            res[virtual_dn] = {"partition": virtual_partition,
                                "object_name": virtual_name, "profiles": {}}
            continue

        if 'destination' in l:
            dst = l.split()[1]
            res[virtual_dn]['virtual_address'] = l.split()[1].split(':')[0]
            res[virtual_dn]["destination_address"] = dst.split(':')[0].split('/')[2]
            res[virtual_dn]["destination_partition"] = dst.split(':')[0].split('/')[1]
            res[virtual_dn]["destination_service_port"] = dst.split(':')[1]
        
        if 'source ' in l:
            res[virtual_dn]["source_address"] = l.split()[1]

        if b == 1 and 'pool' in l:
            pool_dn = l.split()[1]
            if "/" not in pool_dn:
                pool_dn = "/Common/" + pool_dn
            _, pool_partition, pool_name = pool_dn.split("/")
            res[virtual_dn]['pool'] = {"dn": pool_dn, "object_name": pool_name, "partition": pool_partition}

        # if 'source-address-translation ' in l and b == 2:
        #     object_subsection = 'SNAT'
        #     res[virtual_dn]["snat"] = {}
        # elif object_subsection == "SNAT" and b == 2 and "pool " in l:
        #     snat_pool_dn = l.split("pool")[1].strip()
        #     if "/" not in snat_pool_dn:
        #         snat_pool_dn = "/Common/" + snat_pool_dn
        #     _, snat_pool_partition, snat_pool_name = snat_pool_dn.split("/")
        #     res[virtual_dn]["snat"] = {"object_name": snat_pool_name, 
        #                                "partition": snat_pool_partition,
        #                                "dn": snat_pool_dn}
        # elif object_subsection == "SNAT" and b == 2 and "type " in l:
        #     snat_type = l.split("type ")[1].strip()
        #     res[virtual_dn]["snat"]["snat_type"] = snat_type
        # elif object_subsection == "SNAT" and b == 1:
        #     object_subsection = ""

        if 'rules' in l and b == 2:
            object_subsection = 'RULE'
            rules_list = []
        elif object_subsection == 'RULE' and b > 1:
            rule = l.strip()
            rules_list.append(rule)
        elif object_subsection == 'RULE' and b == 1:
            object_subsection = ''
            res[virtual_dn]['rules'] = rules_list
            rules_list = []

        # if "profiles" in l and b == 2:
        #     object_subsection = "PROFILES"
        # elif object_subsection == "PROFILES" and b == 2 and not l.lstrip().startswith("}"):
        #     profile_dn = l.split("{")[0].strip()
        #     if "/" not in profile_dn:
        #         profile_dn = "/Common/" + profile_dn
        #     if ".app/" not in profile_dn:
        #         _, profile_partition, profile_name = profile_dn.split("/")
        #         res[virtual_dn]["profiles"][profile_dn] = {"partition": profile_partition, "object_name": profile_name}
        # elif object_subsection == "PROFILES" and b > 2 and "context" in l:
        #     context = l.split("context")[1].strip()
        #     if context == "clientside":
        #         context = "ClientSide"
        #     elif context == "serverside":
        #         context = "ServerSide"
        #     if res[virtual_dn]["profiles"].get(profile_dn):
        #         res[virtual_dn]["profiles"][profile_dn]["context"] = context
        # elif object_subsection == "PROFILES" and b > 2:
        #     profile_dn = l.split("{")[0].strip()
        #     if "/" not in profile_dn:
        #         profile_dn = "/Common/" + profile_dn
        #     _, profile_partition, profile_name = profile_dn.split("/")
        #     if not res[virtual_dn]["profiles"].get(profile_dn):
        #         res[virtual_dn]["profiles"][profile_dn] = {"partition": profile_partition, "object_name": profile_name}
        # elif object_subsection == "PROFILES" and b == 1:
        #     object_subsection = ''

    return res


def vs_address_parser(obj):
    res = {}
    vs_address_dn = ""

    for b, l in obj:
        if not vs_address_dn:
            vs_address_dn = l.split()[2]
            if "/" not in vs_address_dn:
                vs_address_dn = "/Common/" + vs_address_dn
            _, vs_address_partition, vs_address_name = vs_address_dn.split("/")
            res[vs_address_dn] = {"object_name": vs_address_name, "partition": vs_address_partition}
            continue

        if "address " in l:
            address = l.split("address")[1].strip()
            res[vs_address_dn]["address"] = address
        elif "mask " in l:
            mask = l.split("mask")[1].strip()
            res[vs_address_dn]["mask"] = mask
        elif "arp " in l:
            arp = l.split("arp")[1].strip()
            res[vs_address_dn]["arp"] = arp
        elif "icmp-echo " in l:
            icmp_echo = l.split("icmp-echo")[1].strip()
            res[vs_address_dn]["icmp_echo"] = icmp_echo
        elif "route-advertisement " in l:
            route_advertisement = l.split("route-advertisement")[1].strip()
            res[vs_address_dn]["route_advertisement"] = route_advertisement
        elif "traffic-group " in l:
            traffic_group = l.split("traffic-group ")[1].strip()
            res[vs_address_dn]["traffic_group"] = traffic_group
    # Setting up default to disabled if route_advertisement is missing in the config
    if not res[vs_address_dn].get("route_advertisement"):
        res[vs_address_dn]["route_advertisement"] = "disabled"

    return res

def pool_parser(obj):
    res = {}
    pool_dn = ""
    pool_member_dn = ""
    obj_subsection = ""
    for b, l in obj:
        if not pool_dn:
            pool_dn = l.split()[2]
            if "/" not in pool_dn:
                pool_dn = "/Common/" + pool_dn
            _, pool_partition, pool_name = pool_dn.split("/")
            res[pool_dn] = {"object_name": pool_name, 
                            "partition": pool_partition, 
                            "monitors": {},
                            "members": {}}
            continue
        
        if "monitor " in l:
            for item in l.split():
                if "/" in item and not ".app/":
                    monitor_dn = item.strip()
                    _, monitor_partition, monitor_name = monitor_dn.split("/")
                    res[pool_dn]["monitors"][monitor_dn] = {"object_name": monitor_name,
                                                            "partition": monitor_partition}
        if "min-active-members " in l:
            min_active_members = l.split()[1].strip()
            res[pool_dn]["min_active_members"] = min_active_members
        
        if 'members' in l and b == 2:
            obj_subsection = "POOL_MEMBERS"
        elif obj_subsection == "POOL_MEMBERS" and b == 3:
            if not pool_member_dn:
                pool_member_dn = l.split()[0]
                if "/" not in pool_member_dn:
                    pool_member_dn = "/Common/" + pool_member_dn
                node = pool_member_dn.split(":")[0]
                service_port = int(pool_member_dn.split(":")[1])
                res[pool_dn]["members"][pool_member_dn] = {"node": node,
                                                           "service_port": service_port}
            elif "address " in l:
                address = l.split("address")[1].strip()
                res[pool_dn]["members"][pool_member_dn]["address"] = address
            elif "priority-group " in l:
                priority_group = l.split("priority-group")[1].strip()
                res[pool_dn]["members"][pool_member_dn]["priority_group"] = int(priority_group)
        elif obj_subsection == "POOL_MEMBERS" and b == 2:
            pool_member_dn = ""
        elif obj_subsection == "POOL_MEMBERS" and b == 1:
            obj_subsection = ""

    return res

def node_parser(obj):
    res = {}
    node_dn = ""
    object_subsection = ""

    for b, l in obj:
        if not node_dn:
            node_dn = l.split()[2]
            if "/" not in node_dn:
                node_dn = "/Common/" + node_dn
            _, node_partition, node_name = node_dn.split("/")
            res[node_dn] = {
                "object_name": node_name,
                "partition": node_partition
            }

        if 'address ' in l:
            address = l.split("address")[1].strip()
            res[node_dn]['ip_address'] = address

        if 'fqdn' in l and b == 2:
            object_subsection = "NODE_FQDN"
        elif object_subsection == "NODE_FQDN" and b > 1:
            if "autopopulate" in l:
                if l.split()[1] == "enabled":
                    autopopulate_state = "true"
                else:
                    autopopulate_state = "false"

                res[node_dn]["fqdn_autopopulate"] = autopopulate_state
            if "name" in l:
                res[node_dn]["fqdn_name"] = l.split()[1]
            if "address-family" in l:
                res[node_dn]["fqdn_address_family"] = l.split()[1]
        elif object_subsection == "NODE_FQDN" and b == 1:
            object_subsection = ''
        # need to add state "user-up" or "user-down"

    return res

def rule_parser(obj):
    res = {}
    rule_dn = ""
    rule_script = ""

    for b, l in obj:
        if not rule_dn:
            rule_dn = l.split()[2]
            if "/" not in rule_dn:
                rule_dn = "/Common/" + rule_dn
            _, rule_partition, rule_name = rule_dn.split("/")
            res[rule_dn] = {"object_name": rule_name, 
                            "partition": rule_partition,
                            "vips": [],
                            "pools": []}
            continue

        if 'set destpool ' in l or ' pool ' in l:
            pool = l.split('pool')[1].strip().split()[0].replace("}", "").replace("\"", "")
            if not pool.startswith('$') and not '.app/' in pool:
                pl = {"object_name": pool, "partition": rule_partition}
                if pl not in res[rule_dn]["pools"]:
                    res[rule_dn]["pools"].append(pl)

        if b >= 1 and "ltm rule " not in l:
            rule_script += l
        if b == 0:
            res[rule_dn]["script"] = rule_script

    return res    

def snat_member_parser(obj):
    res = {}
    snat_member_dn = ""
    for b, l in obj:
        if "ltm snat-translation" in l and not snat_member_dn:
            snat_member_dn = l.split()[2]
            if "/" not in snat_member_dn:
                snat_member_dn = "/Common/" + snat_member_dn
            _, snat_member_partition, snat_member_name = snat_member_dn.split("/")
            res[snat_member_dn] = { "object_name": snat_member_name,
                                    "partition": snat_member_partition }
            continue
        if "address " in l:
            address = l.split("address")[1].strip()
            res[snat_member_dn]["address"] = address
        elif "traffic-group " in l:
            traffic_group = l.split("traffic-group ")[1].strip()
            res[snat_member_dn]["traffic_group"] = traffic_group

    return res

def snat_pool_parser(obj):
    res = {}
    members_section = False
    snat_pool_dn = ""

    for b, l in obj:
        if not snat_pool_dn:
            snat_pool_dn = l.split()[2]
            if "/" not in snat_pool_dn:
                snat_pool_dn = "/Common/" + snat_pool_dn
            _, snat_pool_partition, snat_pool_name = snat_pool_dn.split("/")
            res[snat_pool_dn] = {"object_name": snat_pool_name, "partition": snat_pool_partition, "members": {}}
            continue
        if "members " in l and b == 2:
            members_section = True
        elif members_section and b == 2:
            member_dn = l.strip()
            if "/" not in member_dn:
                member_dn = "/Common/" + member_dn
            _, member_partition, member_name = member_dn.split("/")
            res[snat_pool_dn]["members"][member_dn] = {"object_name": member_name, "partition": member_partition}
        elif members_section and b == 1:
            members_section = False
    
    return res

def http_profile(obj):
    res = {}

    for b, l in obj:
        if "defaults-from " in l:
            defaults_from = l.split("defaults-from")[1].strip()
            res["defaults_from"] = defaults_from
        elif "proxy-type " in l:
            proxy_type = l.split("proxy-type")[1].strip()
            res["proxy_type"] = proxy_type
        elif "insert-xforwarded-for " in l:
            ixf = l.split("insert-xforwarded-for")[1].strip()
            if ixf == "enabled":
                res["insert_xforwarded_for"] = True
            else:
                res["insert_xforwarded_for"] = False
    return res

def tcp_profile(obj):
    res = {}

    for b, l in obj:
        if "defaults-from " in l:
            defaults_from = l.split("defaults-from")[1].strip()
            res["defaults_from"] = defaults_from
        elif "idle-timeout " in l:
            idle_timeout = l.split("idle-timeout")[1].strip()
            res["idle_timeout"] = idle_timeout
        elif "nagle " in l:
            nagle = l.split("nagle")[1].strip()
            res["nagle"] = nagle
        elif "syn-cookie-enable " in l:
            syn_cookie_enable = l.split("syn-cookie-enable")[1].strip()
            res["syn_cookie_enable"] = syn_cookie_enable

    return res

def client_ssl_profile(obj):
    res = {}
    cert_section = False
    cert_key_chain_name = ""
    cert_ref = ""
    key_ref = ""
    chain_ref = ""
    passphrase = ""

    for b, l in obj:
        if "defaults-from " in l:
            defaults_from = l.split("defaults-from")[1].strip()
            res["defaults_from"] = defaults_from
        elif "inherit-ca-certkeychain " in l:
            inherit_ca_certkeychain = l.split("inherit-ca-certkeychain")[1].strip()
            res["inherit_ca_certkeychain"] = inherit_ca_certkeychain
        elif "server-name " in l:
            server_name = l.split("server-name")[1].strip()
            res["server_name"] = server_name
        elif "cert-key-chain " in l:
            cert_section = True
            res["cert_key_chain"] = {}
        elif cert_section and b == 3 and not cert_key_chain_name:
            cert_key_chain_name = l.split()[0].strip()
        elif cert_section and cert_key_chain_name and b == 3:
            if "cert " in l:
                cert_ref = l.split("cert")[1].strip()
            elif "chain " in l:
                chain_ref = l.split("chain")[1].strip()
            elif "key " in l: 
                key_ref = l.split("key")[1].strip()
            elif "passphrase " in l:
                passphrase = l.split("passphrase")[1].strip()
        elif cert_section and b == 2:
            res["cert_key_chain"][cert_key_chain_name] =  {"cert": cert_ref, 
                                                            "chain": chain_ref, 
                                                            "key": key_ref, 
                                                            "passphrase": passphrase}
   
            cert_ref = key_ref = chain_ref = cert_key_chain_name = passphrase = ""
        elif cert_section and b == 1:
            cert_section = False            

    return res

def server_ssl_profile(obj):
    res = {}

    for b, l in obj:
        if "defaults-from " in l:
            defaults_from = l.split("defaults-from")[1].strip()
            res["defaults_from"] = defaults_from
        elif "inherit-ca-certkeychain " in l:
            inherit_ca_certkeychain = l.split("inherit-ca-certkeychain")[1].strip()
            res["inherit_ca_certkeychain"] = inherit_ca_certkeychain
        elif "server-name " in l:
            server_name = l.split("server-name")[1].strip()
            res["server_name"] = server_name
        elif "cert " in l:
            cert_ref = l.split("cert")[1].strip()
            res["cert"] = cert_ref
        elif "chain " in l:
            chain_ref = l.split("chain")[1].strip()
            res["chain"] = chain_ref
        elif "key " in l: 
            key_ref = l.split("key")[1].strip()
            res["key"] = key_ref 
        elif "passphrase " in l:
            passphrase = l.split("passphrase")[1].strip()
            res["passphrase"] = passphrase
        elif "sni-default " in l:
            sni_default = l.split("sni-default")[1].strip()
            res["sni_default"] = sni_default  

    return res


def http_monitor(obj):
    res = {}

    for b, l in obj:
        l = l.rstrip().lstrip('\"').rstrip('\"').rstrip()
        if "destination " in l:
            destination = l.split("destination")[1].strip()
            res["destination"] = destination
        elif "interval " in l:
            interval = l.split("interval")[1].strip()
            res["interval"] = int(interval)
        elif "time-until-up " in l:
            time_until_now = l.split("time-until-up")[1].strip()
            res["time_until_now"] = int(time_until_now)
        elif "timeout " in l:
            timeout = l.split("timeout")[1].strip()
            res["timeout"] = int(timeout)
        elif "ip-dscp " in l:
            ip_dscp = l.split("ip-dscp")[1].strip()
            res["ip_dscp"] = int(ip_dscp)
        elif "recv " in l:
            recv = l.split("recv")[1].strip()
            res["recv"] = recv
        elif "send " in l:
            send = l.split("send")[1].strip()
            res["send"] = send

    return res

def https_monitor(obj):
    res = {}

    for b, l in obj:
        l = l.rstrip().lstrip('\"').rstrip('\"').rstrip()
        if "destination " in l:
            destination = l.split("destination")[1].strip()
            res["destination"] = destination
        elif "defaults-from " in l:
            defaults_from = l.split("defaults-from")[1].strip()
            res["defaults_from"] = defaults_from
        elif "interval " in l:
            interval = l.split("interval")[1].strip()
            res["interval"] = int(interval)
        elif "time-until-up " in l:
            time_until_now = l.split("time-until-up")[1].strip()
            res["time_until_now"] = int(time_until_now)
        elif "timeout " in l:
            timeout = l.split("timeout")[1].strip()
            res["timeout"] = int(timeout)
        elif "ip-dscp " in l:
            ip_dscp = l.split("ip-dscp")[1].strip()
            res["ip_dscp"] = int(ip_dscp)
        elif "recv " in l:
            recv = l.split("recv")[1].strip()
            res["recv"] = recv
        elif "send " in l:
            send = l.split("send")[1].strip().replace('"', '')
            res["send"] = send
        elif "ssl-profile " in l:
            ssl_profile = l.split("ssl-profile")[1].strip()
            res["ssl_profile"] = ssl_profile

    return res

def main():
    bracket = 0
    object_header = ""
    object_subsection = ""
    vs_dict = {}
    pool_dict = {}
    vs_address_dict = {}
    rule_dict = {}
    node_dict = {}
    pool_members_dict = {}
    snat_pool_dict = {}
    snat_members_dict = {}
    profiles = {}
    monitors = {}

    # Create imports directory if missing
    imports_path = Path("./imports")
    imports_path.mkdir(exist_ok=True)
    
    # ltm_ha_group = args.ltmhagroup
    profile_dn = profile_type = monitor_dn = monitor_type = ""
    ltm_obj = []

    fh = open(f'{args.input}', 'r', encoding='utf-8', errors='ignore')
    lines = fh.readlines()
    print(f"Reading {len(lines)} lines from input file.")
    for i,line in enumerate(lines):
        ignore_brackets = False
        line_filtered = line.rstrip().lstrip('\"').rstrip('\"').rstrip()
        if line_filtered.strip():
            if line_filtered.strip()[0] == '#':
                ignore_brackets = True
        if not ignore_brackets:
            for c in line_filtered:
                if c == "{":
                    bracket += 1
                elif c == "}":
                    bracket -= 1
            if bracket == 1 and 'ltm' in line_filtered:
                object_header = line

        if object_header.startswith('ltm rule') and ".app/" not in object_header:
            ltm_obj.append((bracket, line))
            if bracket == 0:
                rule_dict.update(rule_parser(ltm_obj))
                ltm_obj = []
                # resetting object_header
                object_header = ""

        if object_header.startswith('ltm node'):
            ltm_obj.append((bracket, line))
            if bracket == 0:
                node_dict.update(node_parser(ltm_obj))
                ltm_obj = []

        if object_header.startswith('ltm virtual ') and ".app/" not in object_header:
            ltm_obj.append((bracket, line))
            if bracket == 0:
                vs_dict.update(virtual_parser(ltm_obj))
                ltm_obj = []
        
        if object_header.startswith("ltm pool ") and ".app/" not in object_header:
            ltm_obj.append((bracket, line))
            if bracket == 0:
                pool_dict.update(pool_parser(ltm_obj))
                ltm_obj = []
        
        if object_header.startswith("ltm profile") and ".app/" not in object_header:
            if not profile_dn:
                profile_dn = object_header.split()[3]
                profile_type = object_header.split()[2]
                if "/" not in profile_dn:
                    profile_dn = "/Common/" + profile_dn
                _, profile_partition, profile_name = profile_dn.split("/")
                profiles[profile_dn] = {"object_name": profile_name, 
                                        "partition": profile_partition,
                                        "profile_type": profile_type}
                continue
            ltm_obj.append((bracket, line))
            if bracket == 0:
                if profile_dn and profile_type == "client-ssl":
                    profiles[profile_dn].update(client_ssl_profile(ltm_obj))
                elif profile_dn and profile_type == "server-ssl":
                    profiles[profile_dn].update(server_ssl_profile(ltm_obj))
                elif profile_dn and profile_type == "tcp":
                    profiles[profile_dn].update(tcp_profile(ltm_obj))
                elif profile_dn and profile_type == "http":
                    profiles[profile_dn].update(http_profile(ltm_obj))
                ltm_obj = []
                profile_dn = ""

        if object_header.startswith("ltm snatpool "):
            ltm_obj.append((bracket, line))
            if bracket == 0:
                snat_pool_dict.update(snat_pool_parser(ltm_obj))
                ltm_obj = []

        if object_header.startswith("ltm snat-translation "):
            ltm_obj.append((bracket, line))
            if bracket == 0:
                snat_members_dict.update(snat_member_parser(ltm_obj))
                ltm_obj = []

        if object_header.startswith("ltm monitor") and ".app/" not in object_header:
            if not monitor_dn:
                monitor_dn = object_header.split()[3]
                monitor_type = object_header.split()[2]
                if "/" not in monitor_dn:
                    monitor_dn = "/Common/" + monitor_dn
                _, monitor_partition, monitor_name = monitor_dn.split("/")
                monitors[monitor_dn] = {
                    "object_name": monitor_name,
                    "partition": monitor_partition,
                    "monitor_type": monitor_type
                }
                continue
            ltm_obj.append((bracket, line))
            if bracket == 0:
                if monitor_dn and monitor_type == "http":
                    monitors[monitor_dn].update(http_monitor(ltm_obj))
                elif monitor_dn and monitor_type == "https":
                    monitors[monitor_dn].update(https_monitor(ltm_obj))
                ltm_obj = []
                monitor_dn = ""

        if object_header.startswith("ltm virtual-address"):
            ltm_obj.append((bracket, line))
            if bracket == 0:
                vs_address_dict.update(vs_address_parser(ltm_obj))
                ltm_obj = []


    # Parsing pools to create pool_member dictionary.
    for pool_dn, v in pool_dict.items():
        pool_name = v["object_name"]
        pool_partition = v["partition"]

        for member_dn, member_data in v["members"].items():
            if member_dn in pool_members_dict.keys():
                pool_temp = {"object_name": pool_name, "partition": pool_partition}
                if pool_temp not in pool_members_dict[member_dn]["pools"]:
                    pool_members_dict[member_dn]["pools"].append(pool_temp)
            else:
                pool_members_dict[member_dn] = {"node": member_data["node"], 
                                                    "service_port": member_data["service_port"], 
                                                    "pools": [
                    {
                        "object_name": pool_name,
                        "partition": pool_partition
                    }
                ]}
        
        if v["monitors"]:
            for m, md in v["monitors"].items():
                if m in monitors:
                    md["monitor_type"] = monitors[m]["monitor_type"]

    # Updating rules with VIP reference and adding profile data into VIP
    for k,v in vs_dict.items():
        if v.get("rules"):
            for rule in v["rules"]:
                if rule in rule_dict:
                    rule_dict[rule]["vips"].append(v)

        if v.get("profiles"):
            for p, pd in v["profiles"].items(): 
                if p in profiles:
                    v["profiles"][p].update(profiles[p])
                else:
                    if "tcp" in p:
                        v["profiles"][p]["profile_type"] = "tcp"
        
        if v.get("virtual_address"):
            if v["virtual_address"] in vs_address_dict:
                vs_address_dict[v["virtual_address"]]["vip"] = k

    # Updating snat members with pool information
    for k, v in snat_pool_dict.items():
        if v.get("members"):
            for m in v["members"]:
                if m in snat_members_dict:
                    snat_members_dict[m]["snat_pool"] = k

    if args.verbose:
        print("Virtuals: ")
        pprint(vs_dict)
        print("\n\n")

        print("Virtual Addresses: ")
        pprint(vs_address_dict)
        print("\n\n")

        print("Pools: ")
        pprint(pool_dict)
        print("\n\n")
        
        print("iRules: ")
        pprint(rule_dict)
        print("\n\n")
        
        print("Nodes: ")
        pprint(node_dict)
        print("\n\n")

        print("Pool members: ")
        pprint(pool_members_dict)
        print("\n\n")

        print("Profiles: ")
        pprint(profiles)
        print("\n\n")

        print("SNAT Pools: ")
        pprint(snat_pool_dict)
        print("\n\n")

        print("SNAT Members: ")
        pprint(snat_members_dict)
        print("\n\n")
        
        print("Monitors: ")
        pprint(monitors)
        print("\n\n")

    environment = Environment(loader=FileSystemLoader('templates/'))

    # Creating infrahub import file for loading nodes
    if node_dict:
        v = {"nodes": node_dict}
        template = environment.get_template('nodes.j2')
        node_import = template.render(v)

        with open(f"imports_test/1_nodes.yml", 'w') as fh:
            fh.write(node_import)
            fh.write('\n')


    # if monitors:
    #     v = {"monitors": monitors}
    #     template = environment.get_template('monitors.j2')
    #     monitors_import = template.render(v)

    #     with open(f"imports/2_monitors.yml", 'w') as fh:
    #         fh.write(monitors_import)
    #         fh.write('\n')


    # Creating infrahub import file for loading pools
    if pool_dict:
        v = {"pools": pool_dict}
        template = environment.get_template('pools.j2')
        pool_import = template.render(v)

        with open(f"imports_test/3_pools.yml", 'w') as fh:
            fh.write(pool_import)
            fh.write('\n')

    if pool_members_dict:
        v = {"members": pool_members_dict}
        template = environment.get_template('pool_members.j2')
        members_import = template.render(v)

        with open(f"imports_test/4_pool_members.yml", 'w') as fh:
            fh.write(members_import)
            fh.write('\n')

    # if profiles:
    #     v = {"profiles": profiles}
    #     template = environment.get_template('profiles.j2')
    #     profiles_import = template.render(v)

    #     with open(f"imports/5_profiles.yml", 'w') as fh:
    #         fh.write(profiles_import)
    #         fh.write('\n')

    # if snat_pool_dict:
    #     v = {"snat_pools": snat_pool_dict}
    #     template = environment.get_template('snat_pools.j2')
    #     snat_pools_import = template.render(v)

    #     with open(f"imports/6_snat_pools.yml", 'w') as fh:
    #         fh.write(snat_pools_import)
    #         fh.write('\n')

    # if snat_members_dict:
    #     v = {"snat_members": snat_members_dict}
    #     template = environment.get_template('snat_members.j2')
    #     snat_members_import = template.render(v)

    #     with open(f"imports/7_snat_members.yml", 'w') as fh:
    #         fh.write(snat_members_import)
    #         fh.write('\n')

    if vs_dict:
        v = {"vips": vs_dict}
        template = environment.get_template('vips.j2')
        vip_import = template.render(v)

        with open(f"imports_test/8_vips.yml", 'w') as fh:
            fh.write(vip_import)
            fh.write('\n')

    if vs_address_dict:
        v = {"vs_addr": vs_address_dict}
        template = environment.get_template('virtual_address.j2')
        vs_address_import = template.render(v)

        with open(f"imports_test/9_virtual_address.yml", 'w') as fh:
            fh.write(vs_address_import)
            fh.write('\n')

    if rule_dict:
        v = {"rules": rule_dict}
        template = environment.get_template('rules.j2')
        rule_import = template.render(v)

        with open(f"imports_test/91_rules.yml", 'w') as fh:
            fh.write(rule_import)
            fh.write('\n')


if __name__ == "__main__":
    main()
