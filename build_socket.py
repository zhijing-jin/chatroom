#!/usr/bin/python3

import socket
import sys
import multiprocessing
from multiprocessing import Process
from utils import show_time, sdbm_hash
from interaction import parse_rmsg, query, parse_members


def build_tcp_client(server_ip, server_port):
    # create socket and connect to Comm_pipe
    try:
        sockfd = socket.socket()
        sockfd.connect((server_ip, server_port))
    except socket.error as emsg:
        print("Socket error: ", emsg)
        return False

    # once the connection is established; print out
    # the socket addresses of your local socket and
    # the Comm_pipe
    print("[Info] CLIENT getsockname() is", sockfd.getsockname())
    print("[Info] SERVER getpeername() is", sockfd.getpeername())

    return sockfd


def build_tcp_server(server_ip, server_port, msg_check_mem, sock_chatroom):
    # create socket and bind
    sockfd = socket.socket()

    try:
        sockfd.bind(('', server_port))
    except socket.error as emsg:
        print("[build_tcp_server] Socket bind error: ", emsg)
        sys.exit(1)

    print("[build_tcp_server] SERVER established at {}:{}".format(server_ip, server_port))

    # listen and accept new connection
    sockfd.listen(5)

    while True:
        try:
            conn, addr = sockfd.accept()
        except socket.error as emsg:
            print("[build_tcp_server] Socket accept error: ", emsg)
            break

        # print out peer socket address information
        print("[build_tcp_server] Connection established. Remote client info:", addr)

        try:
            rmsg = conn.recv(100).decode("utf-8")
            print("[build_tcp_server] tried rmsg: {}".format(rmsg))
        except socket.error as emsg:
            print("Socket recv error: ", emsg)
            break

        if rmsg.startswith('P:'):
            print("[build_tcp_server] received: {}".format(rmsg))

            rmsg = parse_rmsg(rmsg, prefix="P:", suffix="::\r\n")
            msgID = rmsg[-1]
            client_hash = sdbm_hash("{}{}{}".format(*rmsg[1:]))

            rmsg_mems = query(msg_check_mem, sock_chatroom)
            gList = parse_members(rmsg_mems)
            mem_hashes = set(mem.HashID for mem in gList)

            if not client_hash in mem_hashes:
                print("[Error] Detected non-member connection. Closing.")
                msg = 'F:not_member_msg::\r\n'.format(msgID=msgID)
                conn.send(str.encode(msg))
                # break

            msg = 'S:{msgID}::\r\n'.format(msgID=msgID)
            conn.send(str.encode(msg))
            print("[build_tcp_server] Connection established with {}:{}".format(*rmsg[2:4]))
        else:
            break

    # TODO: is this the right termination?
    sockfd.close()
    conn.close()


def retain_forward_link(msg_check_mem, roomchat_sock, myHashID, sock_peers,
                 roomname, username, myip, myport, msgID, MsgWin,
                 my_tcp_conns):
    rmsg_mem = query(msg_check_mem, roomchat_sock)

    # get current member list
    roomhash = rmsg_mem[0]
    while True:
        rmsg_mem = query(msg_check_mem, roomchat_sock)

        # get current member list
        if roomhash != rmsg_mem[0]:
            roomhash = rmsg_mem[0]
            try:
                mems = parse_members(rmsg_mem)
            except AssertionError:
                print('[Error] pls fix here')
                import pdb; pdb.set_trace()
            mem_hashes = set(mem.HashID for mem in mems)

            if sock_peers['forward'] not in mem_hashes:
                sock_peers, msgID, my_tcp_conns = forward_link(mems, myHashID, sock_peers,
                 roomname, username, myip, myport, msgID, MsgWin,
                 my_tcp_conns)




def forward_link(gList, myHashID, sock_peers,
                 roomname, username, myip, myport, msgID, MsgWin,
                 my_tcp_conns):
    if True:

        # start client for every new member
        my_gList_ix = [my_gList_ix for my_gList_ix, item in enumerate(gList)
                       if item.HashID == myHashID][0]
        start = (my_gList_ix + 1) % len(gList)

        while gList[start].HashID != myHashID:
            print("[loop gList] start:", start)

            if gList[start].HashID in sock_peers['backward']:
                start = (start + 1) % len(gList)
            else:
                my_tcp_client = build_tcp_client(gList[start].ip, gList[start].port)
                # my_tcp_client = build_tcp_client('localhost', 32345)
                # if myport == 32342:
                #     import pdb;
                #     pdb.set_trace()

                if my_tcp_client != False:
                    # if tcp_exists(my_tcp_client, conf_pref=b"[server -> client]",
                    #               conf_suf='{}:{}'.format(gList[start].ip, gList[start].port)):

                    msg = 'P:{roomname}:{username}:{userIP}:{port}:{msgID}::\r\n'. \
                        format(roomname=roomname, username=username,
                               userIP=myip, port=myport, msgID=msgID)
                    MsgWin.insert(1.0, "\n[JOIN] peer-to-peer handshake sent msg: {}".format(msg))
                    rmsg = query(msg, my_tcp_client)
                    if rmsg.startswith('S:'):
                        sock_peers['forward'] = gList[start].HashID
                        gList[start].backward += [myHashID]
                        gList[my_gList_ix].forward = gList[start].HashID

                        msgID += 1
                        my_tcp_conns += [my_tcp_client]
                        print("[Info] sock_peers['forward']:", gList[start].name)
                        break
                    elif rmsg.startswith('F:not_member_msg::\r\n'):
                        my_tcp_client.close()
                    else:
                        start = (start + 1) % len(gList)
                else:
                    start = (start + 1) % len(gList)
    return sock_peers, msgID, my_tcp_conns
