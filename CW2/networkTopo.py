from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import Host, OVSKernelSwitch
from mininet.log import setLogLevel, info
from mininet.node import RemoteController
from mininet.term import makeTerm

def myTopo():
    net = Mininet(topo=None, autoSetMacs=True, build=False, ipBase='10.0.1.0/24')

    # add controller
    c1 = net.addController('c1', controller=RemoteController)

    # add hosts
    client = net.addHost('client', cls=Host, ip='10.0.1.5/24', defaultRoute=None)
    server1 = net.addHost('server1', cls=Host, ip='10.0.1.2/24', defaultRoute=None)
    server2 = net.addHost('server2', cls=Host, ip='10.0.1.3/24', defaultRoute=None)

    # add switch
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch, failMode='standalone')

    # add links
    net.addLink(client, s1)
    net.addLink(server1, s1)
    net.addLink(server2, s1)

    net.build()

    # set mac
    server1.setMAC(intf='se1-eth0', mac='00:00:00:00:00:01')
    server2.setMAC(intf='se2-eth0', mac='00:00:00:00:00:02')
    client.setMAC(intf='cl-eth0', mac='00:00:00:00:00:03')

    server1.setIP(intf='se1-eth0', ip='10.0.1.2/24')
    server2.setIP(intf='se2-eth0', ip='10.0.1.3/24')
    client.setIP(intf='cl-eth0', ip='10.0.1.5/24')

    # start network
    net.start()

    net.terms += [makeTerm(c1), makeTerm(s1), makeTerm(server1), makeTerm(server2), makeTerm(client)]

    # run CLI
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    myTopo()