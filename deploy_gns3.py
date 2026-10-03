#!/usr/bin/env python3
"""
GNS3 deployment: DC (R2/R9) + 3 branches, ISP = R4. OSPF inside, eBGP outside.
No extra packages needed (uses plain sockets to the GNS3 console ports).

  python deploy_gns3.py --dry-run   # only write configs to ./configs/
  python deploy_gns3.py             # push to routers via console telnet

1) Start all nodes in GNS3 first.
2) Fill CONSOLE with each router's console port (GNS3: right-click -> Console,
   or hover over the node / see the Topology Summary panel).
"""
import argparse
import os
import socket
import time

GNS3_HOST = "127.0.0.1"          # IP of the GNS3 server (or GNS3 VM)

# Console telnet port of each router (EDIT THESE)
CONSOLE = {
    "R4": 5000, "R2": 5001, "R9": 5002,
    "R1": 5003, "R8": 5004,
    "R7": 5005, "R6": 5006,
    "R3": 5007, "R5": 5008,
}

ISP = {"name": "R4", "asn": 65100}

# Interface names are exactly as in your GNS3 drawing.
SITES = {
    "DC": dict(id=0, asn=65000, edge="R2", core="R9",
               edge_wan="FastEthernet1/1", edge_core="FastEthernet0/0",
               core_up="FastEthernet1/0", core_lan="FastEthernet0/0",
               isp_if="FastEthernet0/0"),
    "Branch1": dict(imaind=1, asn=65001, edge="R1", core="R8",
               edge_wan="FastEthernet2/0", edge_core="FastEthernet0/0",
               core_up="FastEthernet0/0", core_lan="FastEthernet1/0",
               isp_if="FastEthernet1/0"),
    "Branch2": dict(id=2, asn=65002, edge="R7", core="R6",
               edge_wan="FastEthernet2/0", edge_core="FastEthernet1/0",
               core_up="FastEthernet0/0", core_lan="FastEthernet1/0",
               isp_if="FastEthernet1/1"),
    "Branch3": dict(id=3, asn=65003, edge="R3", core="R5",
               edge_wan="FastEthernet1/1", edge_core="FastEthernet0/0",
               core_up="FastEthernet0/0", core_lan="FastEthernet1/0",
               isp_if="FastEthernet2/0"),
}
# Links between R2-R1, R1-R7, R7-R3 are left unconfigured (stay shut down).


def core_cfg(n, s):
    i = s["id"]
    return [
        f"hostname {n}-CORE",
        "interface Loopback0", f" ip address 1.1.{i}.2 255.255.255.255",
        f"interface {s['core_up']}", " description To EDGE",
        f" ip address 10.{i}.255.2 255.255.255.252", " no shutdown",
        f"interface {s['core_lan']}", " description Site LAN",
        f" ip address 10.{i}.0.1 255.255.255.0", " no shutdown",
        "router ospf 1", f" router-id 1.1.{i}.2",
        f" passive-interface {s['core_lan']}",
        f" network 10.{i}.255.0 0.0.0.3 area 0",
        f" network 10.{i}.0.0 0.0.0.255 area 0",
    ]


def edge_cfg(n, s):
    i = s["id"]
    return [
        f"hostname {n}-EDGE",
        "interface Loopback0", f" ip address 1.1.{i}.1 255.255.255.255",
        f"interface {s['edge_wan']}", " description WAN to ISP",
        f" ip address 172.16.{i}.2 255.255.255.252", " no shutdown",
        f"interface {s['edge_core']}", " description To CORE",
        f" ip address 10.{i}.255.1 255.255.255.252", " no shutdown",
        "router ospf 1", f" router-id 1.1.{i}.1",
        f" passive-interface {s['edge_wan']}",
        f" network 10.{i}.255.0 0.0.0.3 area 0",
        " default-information originate always",
        f"router bgp {s['asn']}", f" bgp router-id 1.1.{i}.1",
        f" neighbor 172.16.{i}.1 remote-as {ISP['asn']}",
        f" network 10.{i}.0.0 mask 255.255.255.0",
    ]


def isp_cfg():
    cfg = ["hostname ISP", "interface Loopback0",
           " ip address 9.9.9.9 255.255.255.255"]
    for n, s in SITES.items():
        cfg += [f"interface {s['isp_if']}", f" description To {n}-EDGE",
                f" ip address 172.16.{s['id']}.1 255.255.255.252", " no shutdown"]
    cfg += [f"router bgp {ISP['asn']}", " bgp router-id 9.9.9.9"]
    for s in SITES.values():
        cfg.append(f" neighbor 172.16.{s['id']}.2 remote-as {s['asn']}")
    return cfg


def build_all():
    cfgs = {ISP["name"]: isp_cfg()}
    for n, s in SITES.items():
        cfgs[s["edge"]] = edge_cfg(n, s)
        cfgs[s["core"]] = core_cfg(n, s)
    return cfgs


def push(dev, cfg):
    """Send config lines straight to the GNS3 console telnet port."""
    sock = socket.create_connection((GNS3_HOST, CONSOLE[dev]), timeout=10)

    def send(line, wait=0.15):
        sock.sendall((line + "\r\n").encode())
        time.sleep(wait)
        sock.settimeout(0.1)
        try:
            sock.recv(65535)          # drain output, we don't need it
        except socket.timeout:
            pass

    send("", 1)
    send("no", 1.5)                   # skip initial config dialog if shown
    send("", 1)
    send("enable")
    send("configure terminal")
    for line in cfg:
        send(line)
    send("end")
    send("write memory", 3)
    sock.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfgs = build_all()
    os.makedirs("configs", exist_ok=True)
    for dev, cfg in cfgs.items():
        with open(f"configs/{dev}.cfg", "w") as f:
            f.write("\n".join(cfg) + "\n")
    print(f"Wrote {len(cfgs)} configs to ./configs/")
    if args.dry_run:
        return
    for dev, cfg in cfgs.items():
        try:
            push(dev, cfg)
            print(f"[OK]   {dev}")
        except Exception as e:
            print(f"[FAIL] {dev}: {e}")

    for dev, cfg in cfgs.items():
        if dev != "R4":
            continue
    ...


if __name__ == "__main__":
    main()
