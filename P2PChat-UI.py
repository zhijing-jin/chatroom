#!/usr/bin/python3

# Student name and No.:
# Student name and No.:
# Development platform:
# Python version:
# Version:


from tkinter import *
import sys
import socket
import datetime
import sched
import multiprocessing
from multiprocessing import Process
import select
import threading
import time
import ctypes

sys.path.append('.')

from utils import sdbm_hash, show_time
from build_socket import build_tcp_client  # forward_link # retain_forward_link # build_tcp_server,
from interaction import query, parse_name, parse_rmsg, handle_join_rmsg, \
    parse_memberships, parse_members, parse_send_message

from time import sleep

#
# Global variables
#
show_time("[P2P] start program")
roomchat_ip = sys.argv[1]
roomchat_ip = '127.0.0.1' if roomchat_ip == 'localhost' else roomchat_ip

roomchat_port = int(sys.argv[2])
roomchat_sock = build_tcp_client(roomchat_ip, roomchat_port)

myip = '127.0.0.1'
myport = int(sys.argv[3])
mysock = None
username = ""
roomname = ""

msgID = 0
# this will include myself, so that when my message is sent back to me, I know not to resend it
# HID as str, msgID as int
HID_msgID_dict = {}
sock_peers = {'backward': [],
              'forward': None}  # backward holds a list of hasIDs [hashID], forward holds hashID where this p2p is pointing at
my_tcp_server = None
my_tcp_conns = []
my_udp_socket = None
backwardlink = {}  # backward links {"hash": conn}
forwardlink = None  # forward links
multiproc = []  # a global list to manage the multi processing
multithread = []  # a global list to manage the multithread work
thread_end = False

''' this is a super class for all the thread objects '''


class working_threads(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        print('to be overwritten')

    def get_id(self):

        # returns id of the respective thread
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id

    def raise_exception(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id,
                                                         ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print('Exception raise failure')


class keepalive_thread(working_threads):
    def __init__(self, msg, sockfd, txt='', interval=20, name='keep alive thread'):
        working_threads.__init__(self)
        self.name = name
        self.interval = interval
        self.msg = msg
        self.sockfd = sockfd
        self.txt = txt

    def run(self):
        try:
            while not thread_end:
                time.sleep(self.interval)
                print('[P2P >keepalive] {} greetings from {} with thread {}'.format(show_time(), self.txt, self.name))

                rmsg = query(self.msg, self.sockfd)
        finally:
            print("[P2P >keepalive] {} internally ended".format(self.name))


class server_thread(working_threads):
    def __init__(self, msg, name='server thread'):
        working_threads.__init__(self)
        self.msg = msg
        self.name = name

    def run(self):
        try:
            build_tcp_server(self.msg)
        finally:
            print("{} internally ended".format(self.name))


class client_thread(working_threads):
    def __init__(self, name='client thread'):
        working_threads.__init__(self)
        self.name = name

    def run(self):
        global forwardlink

        try:
            RList = [forwardlink]

            # create an empty WRITE socket list
            WList = []

            while not thread_end:
                print('Client is ready for receiving messages')
                # use select to wait for any incoming connection requests or
                # incoming messages or 10 seconds
                try:
                    Rready, Wready, Eready = select.select(RList, [], [], 10)
                except select.error as emsg:
                    print("At select, caught an exception:", emsg)
                    sys.exit(1)
                except KeyboardInterrupt:
                    print("At select, caught the KeyboardInterrupt")
                    sys.exit(1)

                # if has incoming activities
                if Rready:
                    forwardlink.settimeout(0.1);
                    print('Client is ready in tcp chatting', forwardlink)

                    try:
                        rmsg = forwardlink.recv(1000)  # .decode("utf-8")
                        if rmsg:
                            receive_and_send(rmsg, forwardlink)
                        else:
                            print("A client connection is broken!!")
                    except socket.timeout:
                        print("Your forward link was not sent successfully")

        finally:
            print("{} internally ended".format(self.name))


def err(msg='We encounter an error'):
    print('[Error] {}'.format(msg))


'''
sending_sock is where the message comes from, and therefore not necessary to resend message to him
'''


def receive_and_send(rmsg, sending_sock):
    global HID_msgID_dict, roomchat_sock
    print('this is rmsg', rmsg)
    msg_split, content = parse_send_message(rmsg.decode("utf-8"))
    print(msg_split, content)
    if msg_split:  # otherwise the msg format is incorrect
        origin_roomname = msg_split[0]
        originHID = msg_split[1]
        origin_username = msg_split[2]
        msgID = msg_split[3]
        print(origin_roomname, originHID, origin_username, msgID, content)

        if origin_roomname != roomname:
            print('this is not my room')
            return
        if originHID in HID_msgID_dict and int(HID_msgID_dict[originHID]) >= int(msgID):
            err('we have recorded this message')
            return

        if not originHID in HID_msgID_dict:
            # handle the case that this is an unknown peer
            print("[Info] I don't know this guy, add it to my dict")
            msg_check_mem = 'J:{roomname}:{username}:{userIP}:{port}::\r\n'. \
                format(roomname=roomname, username=username,
                       userIP=myip, port=myport)
            try:
                newmsg = query(msg_check_mem, roomchat_sock)
                membermsg = parse_memberships(newmsg)
                memberships = membermsg[1::3]
            except:
                err('Fail to ask roomserver about the unknown sender')
            if not newmsg or newmsg[0] == 'F':
                err('Fail to ask roomserver about the unknown sender')
                return

            try:
                # if cannot find him in the group list, report an error
                idx = memberships.index(origin_username)
            except:
                err('Fail to find sender: {} in this chatroom'.format(origin_username))
                return
            print("[Info] upon asking for this unknown, I get", newmsg)

        HID_msgID_dict[originHID] = int(msgID)
        MsgWin.insert(1.0, "\n[{origin_username}] [ID: {msgID}]: {content}".format(origin_username=origin_username,
                                                                                   msgID=msgID, content=content))

        my_connections = list(backwardlink.values())
        if forwardlink:
            my_connections += [forwardlink]
        for sk in my_connections:
            if sk != sending_sock:
                sk.send(rmsg)

    else:
        print('incorrect msg format')


class forwardlink_thread(working_threads):
    def __init__(self, msg, myHashID, msgID, name='forwardlink thread'):
        threading.Thread.__init__(self)
        self.msg = msg
        self.name = name
        self.myHashID = myHashID
        self.msgID = msgID

    def run(self):
        try:
            retain_forward_link(self.msg, self.myHashID, self.msgID)
        # while not thread_end:
        # 	time.sleep(5)
        # 	print('link waken')
        finally:
            print("{} internally ended".format(self.name))


#
# Functions to handle user input
#

# this function checks whether the client has joined in  or not
# considering possible unstability of network, a local variable may not be sufficient to check join
# therefore each time need to check join, we send a query, and set roomname to False if failed
# in this way, if the client accidentally gets kicked from a chatroom, he still can join a chatroom
def check_join():
    global roomname

    if not roomname:
        return False
    if not username:
        return False
    msg_check_mem = 'J:{roomname}:{username}:{userIP}:{port}::\r\n'. \
        format(roomname=roomname, username=username,
               userIP=myip, port=myport)
    try:
        rmsg = query(msg_check_mem, roomchat_sock)
    except:
        return False
    if rmsg[0] == 'F':  # if 'F',
        roomname = Nonem
        return False
    else:
        return True


def do_User():
    global username
    if check_join():
        CmdWin.insert(1.0,
                      "\n[Warn] You cannot change username because you have [Join]'ed. Your current name: {}".format(
                          username))
        return
    name = parse_name(userentry)
    if not name:
        CmdWin.insert(1.0, "\n[Error] Username cannot be empty.")
    else:
        username = name
        outstr = "\n[User] username: " + name
        CmdWin.insert(1.0, outstr)


def do_List():
    msg = 'L::\r\n'
    rmsg = query(msg, roomchat_sock)

    groups = parse_rmsg(rmsg, prefix="G:")

    if groups == ['']:
        CmdWin.insert(1.0, "\n[List] No active chatrooms")
    else:
        for group in groups:
            CmdWin.insert(1.0, "\n    {}".format(group))
        CmdWin.insert(1.0, "\n[List] Here are the active chatrooms:")

    MsgWin.insert(1.0, "\nThe received message: {}".format(rmsg))


# G:Name1:Name2:Name3::\r\n


def do_Join():
    global roomname, roomchat_ip, \
        multiproc, msgID, sock_peers, \
        my_tcp_conns, forwardlink, multithread
    name = parse_name(userentry)

    if not username:
        CmdWin.insert(1.0, "\n[Error] Username cannot be empty. Pls input username and press [User].")
        return

    if not name:
        CmdWin.insert(1.0, "\n[Error] roomname cannot be empty.")
    elif check_join():
        if name == roomname:
            CmdWin.insert(1.0, "\n[Warn] You are already in room {}.".format(roomname))
        else:
            CmdWin.insert(1.0, "\n[Error] Already in a room. Cannot change rooms.")
    else:
        roomname = name
        # Step 1. join the chatroom, by sending msg to chatroom app
        msg_check_mem = 'J:{roomname}:{username}:{userIP}:{port}::\r\n'. \
            format(roomname=roomname, username=username,
                   userIP=myip, port=myport)
        rmsg = query(msg_check_mem, roomchat_sock)
        handle_join_rmsg(rmsg, roomname, CmdWin, MsgWin)
        print("[P2P >do_Join] JOIN message: {}, for input: {}".format(rmsg, msg_check_mem))

        # Step 2. keepalive, by sending JOIN msg to the chatroom app every 20 sec

        # TODO: change to thread
        # p = Process(target=keepalive, args=(msg_check_mem, roomchat_sock, username,))
        # p.start()
        # multiproc += [p]
        # print('[Info] out of keepalive')

        t = keepalive_thread(msg_check_mem, roomchat_sock,
                             username)  # ing.Thread(target=tmp_test, args=(1,)) #target=keepalive, args=(msg_check_mem, roomchat_sock, username,))
        t.start()
        multithread += [t]

        # except:
        #     print('Unable to use multi threading on keepalive')
        #     exit(0)
        # print('[Info] out of keepalive')

        myHashID = sdbm_hash("{}{}{}".format(username, myip, myport))

        # Step 4. start my TCP server, as the server for other users to CONNECT to in the chatroom
        # TODO: chagne to thread
        # p = Process(target=build_tcp_server,
        # 		args=(msg_check_mem,))
        # p.start()
        # multiproc += [p]
        t = server_thread(msg_check_mem)
        t.start()
        multithread += [t]
        # print('[Info] out of server thread')

        # Step 5. start a TCP client, to CONNECT another user's TCP server in the chatroom
        print('[Info] Entering forward link establishment')
        gList = parse_members(rmsg)
        sock_peers, get, my_tcp_conns, forwardlink = \
            forward_link(gList, myHashID, sock_peers, roomname,
                         username, myip, myport, msgID, MsgWin, my_tcp_conns)

        # update my TCP client when a relevant user terminates
        # (when the user that you CONNECT to terminates, you need to connect to another TCP server instead)
        # TODO: for the following process, I need to reuse `msgID` and `my_tcp_conns`
        # TODO: change to thread
        # p = Process(target=retain_forward_link,
        #             args=(msg_check_mem, myHashID, msgID))
        # p.start()
        # multiproc += [p]
        t = forwardlink_thread(msg_check_mem, myHashID, msgID)
        t.start()
        multithread += [t]

    # import pdb;
    # pdb.set_trace()


def do_Send():
    global msgID, HID_msgID_dict

    # print()
    if not username:
        CmdWin.insert(1.0, "\n[Error] You must have a username first.")
        return

    if not check_join():
        CmdWin.insert(1.0, "\n[Error] You must join a chatroom first.")
        return

    sendmsg = userentry.get()
    if not sendmsg:
        CmdWin.insert(1.0, "\n[Error] Empty message cannot be sent.")
        return

    originHID = sdbm_hash("{}{}{}".format(username, myip, myport))

    msgID += 1
    # also include myself in the dictionary
    HID_msgID_dict[str(originHID)] = msgID
    msg = 'T:{roomname}:{originHID}:{username}:{msgID}:{msgLength}:{content}::\r\n'.format(roomname=roomname,
                                                                                           originHID=originHID,
                                                                                           username=username,
                                                                                           msgID=msgID,
                                                                                           msgLength=len(sendmsg),
                                                                                           content=sendmsg)
    MsgWin.insert(1.0,
                  "\n[{username}] [ID: {msgID}]: {content}".format(username=username, msgID=msgID, content=sendmsg))

    if forwardlink:
        forwardlink.send(str.encode(msg))
    for bwl in list(backwardlink.values()):
        print('I send via', bwl)
        bwl.send(str.encode(msg))
    userentry.delete(0, END)


def do_Poke():
    global my_udp_socket
    if not username:
        CmdWin.insert(1.0, "\n[Error] You must have a username first.")
        return

    if not check_join():
        CmdWin.insert(1.0, "\n[Error] You must join a chatroom first.")
        return

    targetname = parse_name(userentry)

    # if empty, provide list; if not empty check if it's inside the list
    msg = 'J:{roomname}:{username}:{userIP}:{port}::\r\n'.format(roomname=roomname, username=username,
                                                                 userIP=myip, port=myport)
    rmsg = query(msg, roomchat_sock)
    membermsg = parse_memberships(rmsg)
    memberships = membermsg[1::3]

    if not targetname:
        for member in memberships:
            if member != username:
                CmdWin.insert(1.0, "\n    {}".format(member))
        CmdWin.insert(1.0, "\n[Poke] To whom you want to send the poke?")
    elif targetname == username:
        CmdWin.insert(1.0, "\n[Error] Cannot poke yourselves")
    elif not targetname in memberships:
        CmdWin.insert(1.0, "\n[Error] The username you provided is not in this chatroom")
    else:
        # global mysock
        # if not mysock:
        #     print("rediculous!")\
        rmsg = query(msg, roomchat_sock)
        membermsg = parse_memberships(rmsg)
        memberships = membermsg[1::3]

        try:
            # if I use membermsg to find, and if someone use a port as username, it could cause misunderstanding
            # therefore I use membership to search among usernames instead, and recover to membermsg
            idx = memberships.index(targetname) * 3 + 1
        except:
            for member in memberships:
                if member != username:
                    CmdWin.insert(1.0, "\n    {}".format(member))
            CmdWin.insert(1.0, "\n[Poke] That member has left the chat room. To whom you want to send the poke?")
            return

        if not my_udp_socket:
            my_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = 'K:{roomname}:{username}::\r\n'.format(roomname=roomname, username=username)
        MsgWin.insert(1.0, "\n The message you are sending is " + msg)

        print("index of ", targetname, " is ", str.encode(msg),
              (membermsg[idx + 1], int(membermsg[idx + 2])), flush=False)

        my_udp_socket.sendto(str.encode(msg), (membermsg[idx + 1], int(membermsg[idx + 2])))
        my_udp_socket.settimeout(2);

        try:
            rmsg = my_udp_socket.recvfrom(1000)  # .decode("utf-8")
        except socket.timeout:
            CmdWin.insert(1.0, "\n[Error] Your [Poke] was not sent successfully")
            return
        if not rmsg:
            print("failure", flush=False)
            CmdWin.insert(1.0, "\n[Error] Poke failure")
        elif "A::\r\n" == rmsg[0].decode("utf-8"):
            print("success", flush=False)
            CmdWin.insert(1.0, "\n[Poke] You poked {}".format(targetname))
        else:
            CmdWin.insert(1.0, "\n[Error] Poke failure")


def do_Quit():
    global my_tcp_server, my_tcp_conns, thread_end
    CmdWin.insert(1.0, "\nPress Quit")
    roomchat_sock.close()
    print("[Info] Closed socket")

    if my_tcp_server is not None:
        my_tcp_server.close()
        for conn in my_tcp_conns:
            conn.close()
        print("[Info] Closed tcp_conn, tcp_server")

    # for p in multiproc:
    #     p.terminate()
    #     p.join()
    # print("[Info] Closed multiprocessing")

    # sys.exit(0)

    thread_end = True
    # for t in multithread:
    # 	t.raise_exception()

    for t in multithread:
        t.raise_exception()
        t.join()
        print("[Info] {name} has joined".format(name=t.name))
    print("[Info] Closed multithreading")

    sys.exit(0)


def build_tcp_server(msg_check_mem):
    global myip, myport, roomchat_sock, backwardlink, MsgWin, CmdWin, HID_msgID_dict
    # Step 1. create socket and bind
    sockfd = socket.socket()
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sockfd.bind((myip, myport))
        udp.bind((myip, myport))
    except socket.error as emsg:
        print("[build_tcp_server] Socket bind error: ", emsg)
        sys.exit(1)

    print("[build_tcp_server] SERVER established at {}:{}".format(myip, myport))

    # Step 2. listen
    sockfd.listen(5)

    # add the listening socket to the READ socket list
    RList = [sockfd, udp]
    # create an empty WRITE socket list
    WList = []

    while not thread_end:
        # use select to wait for any incoming connection requests or
        # incoming messages or 10 seconds
        try:
            Rready, Wready, Eready = select.select(RList, [], [], 10)
        except select.error as emsg:
            print("At select, caught an exception:", emsg)
            sys.exit(1)
        except KeyboardInterrupt:
            print("At select, caught the KeyboardInterrupt")
            sys.exit(1)

        # if has incoming activities
        if Rready:
            print('I am very busy')
            # for each socket in the READ ready list
            for sd in Rready:
                if sd == udp:
                    print('I am in udp')
                    msg, addr = sd.recvfrom(1024)
                    print("we receiver the msg", msg, flush=False)

                    if not msg:
                        print("[Error] chat server broken")
                    else:
                        print(msg, addr, flush=False)
                        rmsg = parse_rmsg(msg.decode("utf-8"), prefix="K:", suffix="::\r\n")
                        MsgWin.insert(1.0, "\n~~~~~~~~~~~~~{}~~~~~~~~~~~~~~".format(rmsg[1]))

                        print("You are poked by {}!!".format(rmsg[1]))
                        sd.sendto(str.encode("A::\r\n"), addr)
                elif sd == sockfd:
                    print('I am in tcp establishing')

                    # Step 3. accept new connection
                    try:
                        conn, addr = sd.accept()
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
                        rmsg_mems = query(msg_check_mem, roomchat_sock)
                        gList = parse_members(rmsg_mems)
                        mem_hashes = set(mem.HashID for mem in gList)
                        HID_msgID_dict[str(client_hash)] = msgID

                        if not client_hash in mem_hashes:
                            print("[Error] Detected non-member connection. Closing.")
                            msg = 'F:not_member_msg::\r\n'.format(msgID=msgID)
                            conn.send(str.encode(msg))
                        # break

                        msg = 'S:{msgID}::\r\n'.format(msgID=msgID)
                        conn.send(str.encode(msg))
                        print("[build_tcp_server] Connection established with {}:{}".format(*rmsg[2:4]))

                        # Step 6. add the backward link to connections
                        backwardlink[client_hash] = conn
                        print("[P2P >build_tcp_server] backward link first established: {}".format(backwardlink))
                        RList += [conn]
                    else:
                        break
                else:  # it could be forward or a backward link, I don't care
                    # if sd == forward:
                    # 	print('wow this is forward')
                    # else:
                    # 	print('this is backward :(')
                    print('I am in tcp chatting', sd)
                    rmsg = sd.recv(1000)
                    if rmsg:
                        receive_and_send(rmsg, sd)
                    else:
                        print("A client connection is broken!!")


# TODO: is this the right termination?
# sockfd.close()
# conn.close()

def retain_forward_link(msg_check_mem, myHashID, msgID):
    global my_tcp_conns, roomname, username, myip, myport, MsgWin, roomchat_sock, sock_peers, \
        forwardlink, backwardlink
    # get current member list
    rmsg_mem = query(msg_check_mem, roomchat_sock)
    roomhash = rmsg_mem[0]

    retain_num = 0

    while not thread_end:

        rmsg_mem = query(msg_check_mem, roomchat_sock)
        if rmsg_mem.startswith("F:"):
            # this is the case that two simutaneous messages form a mal-formatted request
            continue

        # if the roomhash is changed, update the member list
        if roomhash != rmsg_mem[0]:
            retain_num += 1
            print("[P2P >retain_forw] retain_num: {}".format(retain_num))

            roomhash = rmsg_mem[0]
            try:
                mems = parse_members(rmsg_mem)
            except AssertionError:
                print('[P2P >retain_forward_link][Error] pls fix here. I received: {}, I sent: {}'.format(rmsg_mem,
                                                                                                          msg_check_mem))
            # import pdb;
            # pdb.set_trace()
            mem_hashes = set(mem.HashID for mem in mems)
            print("[P2P >retain] backwardlink RIGHT BEFORE update: {}".format(backwardlink))
            backwardlink = {k: v for k, v in backwardlink.items() if k in mem_hashes}
            print("[P2P >retain] backwardlink RIGHT AFTER update: {}".format(backwardlink))

            # if the my forward server is no longer in the member list,
            # make a new forward link
            if sock_peers['forward'] not in mem_hashes:
                sock_peers, msgID, my_tcp_conns, forwardlink = forward_link(mems, myHashID, sock_peers,
                                                                            roomname, username, myip, myport, msgID,
                                                                            MsgWin,
                                                                            my_tcp_conns)
            print("[P2P >retain] forwardlink RIGHT AFTER update: {}".format(forwardlink))

        time.sleep(1)


def forward_link(gList, myHashID, sock_peers_TODO,
                 roomname, username, myip, myport, msgID, MsgWin,
                 my_tcp_conns_TODO):
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
    global my_tcp_conns, forwardlink, sock_peers, multithread
    my_gList_ix = [my_gList_ix for my_gList_ix, item in enumerate(gList)
                   if item.HashID == myHashID][0]
    start = (my_gList_ix + 1) % len(gList)

    forwardlink = None

    # this while loop finds ONE peer to establish a forward link to
    while gList[start].HashID != myHashID:
        print("[loop gList] start:", start)

        if gList[start].HashID in sock_peers['backward']:
            start = (start + 1) % len(gList)
        else:
            forwardlink = build_tcp_client(gList[start].ip, gList[start].port)
            # forwardlink = build_tcp_client('localhost', 32345)
            # if myport == 32342:
            #     import pdb;
            #     pdb.set_trace()

            if forwardlink != False:
                t = client_thread()
                t.start()
                multithread += [t]
                print("[P2P >forward_link] out of client thread")
                # handshake
                msg = 'P:{roomname}:{username}:{userIP}:{port}:{msgID}::\r\n'. \
                    format(roomname=roomname, username=username,
                           userIP=myip, port=myport, msgID=msgID)
                MsgWin.insert(1.0, "\n[JOIN] peer-to-peer handshake sent msg: {}".format(msg))
                rmsg = query(msg, forwardlink)
                if rmsg.startswith('S:'):
                    sock_peers['forward'] = gList[start].HashID
                    gList[start].backward += [myHashID]
                    gList[my_gList_ix].forward = gList[start].HashID

                    msgID += 1
                    my_tcp_conns += [forwardlink]
                    # backwardlink += [forwardlink]
                    print("[P2P >forward_link] sock_peers['forward']:", gList[start].name)
                    break
                elif rmsg.startswith('F:not_member_msg::\r\n'):
                    forwardlink.close()
                else:
                    start = (start + 1) % len(gList)
            else:
                start = (start + 1) % len(gList)
    return sock_peers, msgID, my_tcp_conns, forwardlink


# manager = multiprocessing.Manager()
#
# Set up of Basic UI
#
win = Tk()
win.title("MyP2PChat")

# Top Frame for Message display
topframe = Frame(win, relief=RAISED, borderwidth=1)
topframe.pack(fill=BOTH, expand=True)
topscroll = Scrollbar(topframe)
MsgWin = Text(topframe, height='15', padx=5, pady=5,
              fg="red", exportselection=0, insertofftime=0)
MsgWin.pack(side=LEFT, fill=BOTH, expand=True)
# shared_list = manager.list()
# shared_list.append(MsgWin)
topscroll.pack(side=RIGHT, fill=Y, expand=True)
MsgWin.config(yscrollcommand=topscroll.set)
topscroll.config(command=MsgWin.yview)

# Top Middle Frame for buttons
topmidframe = Frame(win, relief=RAISED, borderwidth=1)
topmidframe.pack(fill=X, expand=True)
Butt01 = Button(topmidframe, width='6', relief=RAISED,
                text="User", command=do_User)
Butt01.pack(side=LEFT, padx=8, pady=8)
Butt02 = Button(topmidframe, width='6', relief=RAISED,
                text="List", command=do_List)
Butt02.pack(side=LEFT, padx=8, pady=8)
Butt03 = Button(topmidframe, width='6', relief=RAISED,
                text="Join", command=do_Join)
Butt03.pack(side=LEFT, padx=8, pady=8)
Butt04 = Button(topmidframe, width='6', relief=RAISED,
                text="Send", command=do_Send)
Butt04.pack(side=LEFT, padx=8, pady=8)
Butt06 = Button(topmidframe, width='6', relief=RAISED,
                text="Poke", command=do_Poke)
Butt06.pack(side=LEFT, padx=8, pady=8)
Butt05 = Button(topmidframe, width='6', relief=RAISED,
                text="Quit", command=do_Quit)
Butt05.pack(side=LEFT, padx=8, pady=8)

# Lower Middle Frame for User input
lowmidframe = Frame(win, relief=RAISED, borderwidth=1)
lowmidframe.pack(fill=X, expand=True)
userentry = Entry(lowmidframe, fg="blue")
userentry.pack(fill=X, padx=4, pady=4, expand=True)

# Bottom Frame for displaying action info
bottframe = Frame(win, relief=RAISED, borderwidth=1)
bottframe.pack(fill=BOTH, expand=True)
bottscroll = Scrollbar(bottframe)
CmdWin = Text(bottframe, height='15', padx=5, pady=5,
              exportselection=0, insertofftime=0)
CmdWin.pack(side=LEFT, fill=BOTH, expand=True)
bottscroll.pack(side=RIGHT, fill=Y, expand=True)
CmdWin.config(yscrollcommand=bottscroll.set)
bottscroll.config(command=CmdWin.yview)


def main():
    if len(sys.argv) != 4:
        print("P2PChat.py <server address> <server port no.> <my port no.>")
        sys.exit(2)

    win.mainloop()


if __name__ == "__main__":
    main()
