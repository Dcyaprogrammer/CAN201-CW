from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4, tcp

class RyuForward(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    def __init__(self, *args, **kwargs):
        super(RyuForward, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
    
    # table-miss rule
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):

        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        # lowest priority
        self.add_flow(datapath, 0, match, actions, buffer_id=None)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, idle_timeout=5):

        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        # excluding table-miss rule
        timeout = idle_timeout if priority > 0 else 0

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, 
                                    priority=priority, 
                                    match=match, 
                                    instructions=inst, 
                                    buffer_id=buffer_id,
                                    idle_timeout=timeout)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, 
                                    priority=priority, 
                                    match=match, 
                                    instructions=inst,
                                    idle_timeout=timeout)
        datapath.send_msg(mod)
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes", ev.msg.msg_len, ev.msg.total_len)
        
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # ignore lldp packets
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        
        # check TCP/IPv4
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if not ip_pkt:
            return
        tcp_pkt = ip_pkt.get_protocol(tcp.tcp)
        if not tcp_pkt:
            return
        
        # check TCP SYN
        if not (tcp_pkt.bits & tcp.TCP_SYN) or (tcp_pkt.bits & tcp.TCP_ACK):
            return
        
        src_ip = ip_pkt.src
        dst_ip = ip_pkt.dst
        src_port = tcp_pkt.src_port
        dst_port = tcp_pkt.dst_port
        
        # learn mac
        dst = eth.dst
        src = eth.src
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)
        self.mac_to_port[dpid][src] = in_port

        # check
        if src == '00:00:00:00:00:03':  
            if '00:00:00:00:00:01' in self.mac_to_port[dpid]:  
                out_port = self.mac_to_port[dpid]['00:00:00:00:00:01']
                if dst == '00:00:00:00:00:01':
                    self.logger.info("Forward: Client traffic directly to Server1 on port %s", out_port)
                else:
                    self.logger.info("Redirect: Client traffic (dst=%s) redirected to Server1 on port %s", dst, out_port)
            else:
                if dst in self.mac_to_port[dpid]:
                    out_port = self.mac_to_port[dpid][dst]
                else:
                    out_port = ofproto.OFPP_FLOOD
        else:
            if dst in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst]
            else:
                out_port = ofproto.OFPP_FLOOD
        
        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst,
            )
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, buffer_id=msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions, buffer_id=None)
        
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id, 
            in_port=in_port,
            actions=actions,
            data=data
        )
        datapath.send_msg(out)