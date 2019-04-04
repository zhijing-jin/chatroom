#!/usr/bin/python3

import socket
import sys
import multiprocessing
from multiprocessing import Process
from utils import show_time, sdbm_hash
from interaction import parse_rmsg, query, parse_members


def build_tcp_client(server_ip, server_port):
    # create socket and connect to a server
    try:
        sockfd = socket.socket()
        sockfd.connect((server_ip, server_port))
    except socket.error as emsg:
        print("Socket error: ", emsg)
        return False

    print("[Info] CLIENT getsockname() is", sockfd.getsockname())
    print("[Info] SERVER getpeername() is", sockfd.getpeername())

    return sockfd


def build_tcp_server(server_ip, server_port, msg_check_mem, sock_chatroom):
    # Step 1. create socket and bind
    sockfd = socket.socket()

    try:
        sockfd.bind(('', server_port))
    except socket.error as emsg:
        print("[build_tcp_server] Socket bind error: ", emsg)
        sys.exit(1)

    print("[build_tcp_server] SERVER established at {}:{}".format(server_ip, server_port))

    # Step 2. listen
    sockfd.listen(5)

    while True:
        # Step 3. accept new connection
        try:
            conn, addr = sockfd.accept()
        except socket.error as emsg:
            print("[build_tcp_server] Socket accept error: ", emsg)
            break

        # print out peer socket address information
        print("[build_tcp_server] Connection established. Remote client info:", addr)

        # Step 4. upon new connection, receive message
        try:
            rmsg = conn.recv(100).decode("utf-8")
            print("[build_tcp_server] tried rmsg: {}".format(rmsg))
        except socket.error as emsg:
            print("Socket recv error: ", emsg)
            break

        # Step 5. enable peer-to-peer handshake
        if rmsg.startswith('P:'):
            print("[build_tcp_server] received: {}".format(rmsg))

            rmsg = parse_rmsg(rmsg, prefix="P:", suffix="::\r\n")
            msgID = rmsg[-1]

            # if the msg is not from a peer in the same chatroom
            # refuse it by replying 'F:not_member_msg::\r\n'
            # else, reply with 'S:{msgID}::\r\n'
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
    # get current member list
    rmsg_mem = query(msg_check_mem, roomchat_sock)
    roomhash = rmsg_mem[0]

    while True:
        rmsg_mem = query(msg_check_mem, roomchat_sock)

        # if the roomhash is changed, update the member list
        if roomhash != rmsg_mem[0]:
            roomhash = rmsg_mem[0]
            try:
                mems = parse_members(rmsg_mem)
            except AssertionError:
                print('[Error] pls fix here')
                import pdb;
                pdb.set_trace()
            mem_hashes = set(mem.HashID for mem in mems)

            # if the my forward server is no longer in the member list,
            # make a new forward link
            if sock_peers['forward'] not in mem_hashes:
                sock_peers, msgID, my_tcp_conns = forward_link(mems, myHashID, sock_peers,
                                                               roomname, username, myip, myport, msgID, MsgWin,
                                                               my_tcp_conns)


def forward_link(gList, myHashID, sock_peers,
                 roomname, username, myip, myport, msgID, MsgWin,
                 my_tcp_conns):
    '''
    This function establishes a forward link to a peer in the chatroom
    :param gList: the list of members
    :param myHashID: the hash of `myname+myip+myport`
    :param sock_peers: a dict storing my backward and forward links
    :param roomname: the name of the chatroom
    :param username: my username
    :param myip: my ip address
    :param myport: my port
    :param msgID: the ID of my message, counting from zero
    :param MsgWin:
    :param my_tcp_conns: the list of connections, which needs to be closed in do_Quit()
    :return: sock_peers, msgID, my_tcp_conns
    '''
    my_gList_ix = [my_gList_ix for my_gList_ix, item in enumerate(gList)
                   if item.HashID == myHashID][0]
    start = (my_gList_ix + 1) % len(gList)

    # this while loop finds ONE peer to establish a forward link to
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
                # handshake
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
