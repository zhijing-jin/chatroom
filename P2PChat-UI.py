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

sys.path.append('.')

from utils import sdbm_hash
from build_socket import build_socket
from interaction import query, parse_name, parse_rmsg, parse_memberships, parse_members, keepalive

import multiprocessing
from time import sleep
#
# Global variables
#
server = sys.argv[1]
server = '127.0.0.1' if server == 'localhost' else server

port = int(sys.argv[2])
myport = int(sys.argv[3])
sockfd = build_socket(server, port)

myserver = '127.0.0.1'
myport = int(sys.argv[3])
mysock = None
username = ""
username_change = True
roomname = ""

multiproc =[]


# set_my_server()

#
# Functions to handle user input
#

def do_User():
    global username, username_change
    if not username_change:
        CmdWin.insert(1.0, "\n[Warn] You cannot change username because you have [Join]'ed. Your current name: {}".format(username))
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
    rmsg = query(msg, sockfd)

    groups = parse_rmsg(rmsg)

    if groups == ['']:
        CmdWin.insert(1.0, "\n[List] No active chatrooms")
    else:
        for group in groups:
            CmdWin.insert(1.0, "\n    {}".format(group))
        CmdWin.insert(1.0, "\n[List] Here are the active chatrooms:")

    MsgWin.insert(1.0, "\nThe received message: {}".format(rmsg))

    # G:Name1:Name2:Name3::\r\n


def do_Join():
    global roomname, server, username_change, multiproc
    roomname = parse_name(userentry)

    if not username:
        CmdWin.insert(1.0, "\n[Error] Username cannot be empty. Pls input username and press [User].")
        return

    if not roomname:
        CmdWin.insert(1.0, "\n[Error] roomname cannot be empty.")
    else:
        msg = 'J:{roomname}:{username}:{userIP}:{port}::\r\n'. \
            format(roomname=roomname, username=username,
                   userIP=myserver, port=myport)

        MsgWin.insert(1.0, "\n[JOIN] sent msg: {}".format(msg))
        rmsg = query(msg, sockfd)

        if rmsg[0] != 'F':
            outstr = "\n[Join] roomname: " + roomname
            CmdWin.insert(1.0, outstr)
        MsgWin.insert(1.0, "\n[Join] received msg: {}".format(rmsg))

        # after joining
        username_change = False

        p = multiprocessing.Process(target=keepalive, args=(msg, sockfd, username,))
        p.start()
        multiproc += [p]
        print('[Info] out of keepalive')

        gList = parse_members(rmsg)
        myHashID = sdbm_hash("{}{}{}".format(username, server, myport))

        ix = [ix for ix, item in enumerate(gList) if item.HashID == myHashID][0]
        start = ix + 1
        # import pdb; pdb.set_trace()

        # if len(gList) > start:
        #     while gList[start].HashID != myHashID:
        #         pass

        if mysock == None:
            print("starts multi process")
            p = multiprocessing.Process(target=set_my_server)
            p.start()
            multiproc += [p]
        else:
            print("we have established the server!")
        #set_my_server(1)

def set_my_server():
    print("in server")

    global mysock
    address = (myserver, myport)
    mysock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        mysock.bind((myserver, myport))
    except socket.error as emsg:
        print("Socket bind error: ", emsg)
        sys.exit(1)

    # start the main loop
    while (True):

        msg, addr = mysock.recvfrom(1024)
        print("we receiver the msg", msg, flush=False)

        if not msg:
            print("[Error] chat server broken")
        else:
            print(msg, addr, flush=False)
            rmsg = parse_rmsg(msg.decode("utf-8"), prefix="K:", suffix="::\r\n")
            #MsgWin.insert(1.0, "\n~~~~~~~~~~~~~{}~~~~~~~~~~~~~~".format(rmsg[1]))
            MsgWin.insert(1.0, "\n The message you are sending is ") # + msg)
            print("Inserted to Msg")
            mysock.sendto(str.encode("A::\r\n"), addr)
    mysock.close()


def do_Send():
    CmdWin.insert(1.0, "\nPress Send")


def do_Poke():
    if not username:
        CmdWin.insert(1.0, "\n[Error] You must have a username first.")
        return

    if not roomname:
        CmdWin.insert(1.0, "\n[Error] You must join a chatroom first.")
        return

    targetname = userentry.get()

    # if empty, provide list; if not empty check if it's inside the list
    msg = 'J:{roomname}:{username}:{userIP}:{port}::\r\n'.format(roomname=roomname, username=username,
           userIP=myserver, port=myport)
    rmsg = query(msg, sockfd)
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
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = 'K:{roomname}:{username}::\r\n'.format(roomname=roomname, username=username)
        MsgWin.insert(1.0, "\n The message you are sending is " + msg)
        idx = membermsg.index(targetname)
        print("index of ", targetname, " is ", str.encode(msg), (membermsg[idx+1], int(membermsg[idx+2])), flush=False)
        s.sendto(str.encode(msg), (membermsg[idx+1], int(membermsg[idx+2])))
        rmsg = s.recvfrom(1000) #.decode("utf-8")
        print("this is rmsg", rmsg[0].decode("utf-8"), flush=False)
        if "A::\r\n" == rmsg[0].decode("utf-8"):
            CmdWin.insert(1.0, "\n[Poke] You poked {}".format(targetname))
        else:
            CmdWin.insert(1.0, "\n[Error] Poke failure")



def do_Quit():
    CmdWin.insert(1.0, "\nPress Quit")
    sockfd.close()
    print("[Info] Closed socket")
    for p in multiproc:
        p.terminate()
        p.join()
    print("[Info] Closed multiprocessing")

    sys.exit(0)



# this is a test button, that create a user and a room without using the UI
def do_Auto():
    msg = 'J:COMP3234:triangle:{userIP}:{port}::\r\n'.format(userIP=server, port=port)
    rmsg = query(msg, sockfd)
    MsgWin.insert(1.0, "\nThe received message: {}".format(rmsg))


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

# auto buttons
Butt07 = Button(topmidframe, width='6', relief=RAISED,
                text="Auto", command=do_Auto)
Butt07.pack(side=LEFT, padx=8, pady=8)

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
