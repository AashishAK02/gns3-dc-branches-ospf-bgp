# DC + 3 Branches Network in GNS3 (OSPF + BGP)

A small GNS3 lab with 1 Data Center and 3 branch sites. One Python script configures all the routers automatically.

- Inside each site: **OSPF**
- Between sites (through the ISP router): **BGP**
- No firewall
- The DC has a simple web server that the branches can open in a browser

## Topology

```
                      R4 (ISP, AS 65100)
          ______________|______|______|______________
         |              |             |             |
   R2 (DC edge)   R1 (Br1 edge)  R7 (Br2 edge)  R3 (Br3 edge)
      AS 65000       AS 65001      AS 65002       AS 65003
         |              |             |             |
   R9 (DC core)   R8 (Br1 core)  R6 (Br2 core)  R5 (Br3 core)
         |              |             |             |
      Switch1        Switch2       Switch3        Switch4
         |              |             |             |
   Web server        PC 10.1.0.10  PC 10.2.0.10  PC 10.3.0.10
   10.0.0.10
```

Edge router = talks BGP to the ISP.
Core router = talks OSPF inside the site and is the gateway for the LAN.

## IP addresses

| Site | LAN | Gateway | Host |
|---|---|---|---|
| DC | 10.0.0.0/24 | 10.0.0.1 | 10.0.0.10 |
| Branch1 | 10.1.0.0/24 | 10.1.0.1 | 10.1.0.10 |
| Branch2 | 10.2.0.0/24 | 10.2.0.1 | 10.2.0.10 |
| Branch3 | 10.3.0.0/24 | 10.3.0.1 | 10.3.0.10 |

## Cabling

| Site | Edge to ISP | Edge to core | Core to edge | Core to switch | ISP port |
|---|---|---|---|---|---|
| DC | R2 f1/1 | R2 f0/0 | R9 f1/0 | R9 f0/0 | R4 f0/0 |
| Branch1 | R1 f2/0 | R1 f0/0 | R8 f0/0 | R8 f1/0 | R4 f1/0 |
| Branch2 | R7 f2/0 | R7 f1/0 | R6 f0/0 | R6 f1/0 | R4 f1/1 |
| Branch3 | R3 f1/1 | R3 f0/0 | R5 f0/0 | R5 f1/0 | R4 f2/0 |

## What you need

- GNS3
- Cisco router images (with FastEthernet ports in slots 1 and 2)
- Python 3 (no extra packages)

## Steps

### Step 1: Build the topology in GNS3

1. Create a new project.
2. Add 9 routers and name them R1 to R9.
3. Add 4 Ethernet switches.
4. Add 3 VPCS PCs and 1 Docker nginx container (for the DC web server).
5. Connect everything using the cabling table above.

### Step 2: Start everything

Click the green Play button to start all nodes.

### Step 3: Find the console ports

Right-click each router and choose **Console**, or look in the Topology Summary panel. Write down the port number for each router (like 5000, 5001, ...).

### Step 4: Edit the script

Open `deploy_gns3.py` and change:

- `GNS3_HOST`: keep `127.0.0.1` if GNS3 is on your PC, otherwise use the GNS3 VM's IP
- `CONSOLE`: put the correct console port next to each router

### Step 5: Test first (dry run)

```
python deploy_gns3.py --dry-run
```

This only creates the config files in the `configs` folder. Nothing is sent to the routers.

### Step 6: Push the configs

```
python deploy_gns3.py
```

You should see `[OK]` for every router. Wait about 1 minute.

### Step 7: Set up the PCs

In each VPCS console:

```
ip 10.1.0.10/24 10.1.0.1      (Branch1)
ip 10.2.0.10/24 10.2.0.1      (Branch2)
ip 10.3.0.10/24 10.3.0.1      (Branch3)
```

### Step 8: Set up the DC web server

1. Connect the nginx container to Switch1.
2. Right-click it, choose **Edit config**, and set:

```
auto eth0
iface eth0 inet static
    address 10.0.0.10
    netmask 255.255.255.0
    gateway 10.0.0.1
```

3. Restart the container.

### Step 9: Check that it works

| Where | Command | What you should see |
|---|---|---|
| R4 | `show ip bgp summary` | 4 neighbors with a number of prefixes |
| Edge routers | `show ip ospf neighbor` | State `FULL` |
| Core routers | `show ip route` | A default route (`0.0.0.0/0`) |
| Branch PC | `ping 10.0.0.10` | Replies |
| Browser | `http://10.0.0.10` | nginx welcome page |

## Problems?

- **BGP shows Idle or Active:** check `show ip interface brief` on both ends and try `ping` to the neighbor (for example 172.16.1.1).
- **Interface does not exist:** the router is missing a network module. Stop it, add one in **Configure > Slots**, and run the script again.
- **Script says FAIL:** check that the router is started and the console port is right.
- **Config missing on a router:** run the script again.

## Files

- `deploy_gns3.py` : the script
- `configs/` : the config files it creates
- `README.md` : this file
