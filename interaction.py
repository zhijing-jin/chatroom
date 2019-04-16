import time
from utils import sdbm_hash, show_time
from collections import OrderedDict
from tkinter import END
import asyncio


class Member(object):
    def __init__(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])


def query(msg_str, sockfd, recv_size=1000):
    expected = {
        "L:": "G:",
        "J:": "M:",
    }
    msg = str.encode(msg_str)

    rmsg = "[Nothing]"
    for _ in range(10):
        check_header = (msg_str[:2], rmsg[:2])

        sockfd.send(msg)
        rmsg = sockfd.recv(recv_size).decode("utf-8")
        if not ((msg_str in expected) and (check_header not in expected.items())):
            break
        else:
            print("[interaction.py >query] querying the {}th time".format(_))

    if rmsg.startswith("F:"):
        # if rmsg == 'F:error message::\r\n':
        print("[Error] {} F error message: {}, for input: {}".format(show_time(), rmsg, msg_str))

    return rmsg


def parse_name(userentry, length=32):
    name = userentry.get()
    name = [c for c in name if c != ':'][:length]
    name = ''.join(name)
    userentry.delete(0, END)

    return name


def parse_rmsg(msg_str, prefix="G:", suffix="::\r\n"):
    # G:Name1:Name2:Name3::\r\n

    if not msg_str.startswith(prefix): print ("[Error] rmsg must start with {}, not {}".format(prefix, msg_str))
    if not msg_str.endswith(suffix): print ("[Error] rmsg must end with {}".format(suffix))
    msg_str = msg_str[len(prefix): -len(suffix)]
    return msg_str.split(':')


def parse_send_message(msg_str, prefix="T:", suffix="::\r\n"):
    if not msg_str.startswith(prefix): print ("[Error] rmsg must start with {}, not {}".format(prefix, msg_str))
    if not msg_str.endswith(suffix): print ("[Error] rmsg must end with {}".format(suffix))
    msg_str = msg_str[len(prefix): -len(suffix)]
    msg_split = msg_str.split(':')
    if len(msg_split) < 5:
        return None, None
    try:
        msglength = int(msg_split[4])
    except:
        return None, None
    return msg_split[:4], msg_str[-msglength:]


def handle_join_rmsg(rmsg, roomname, CmdWin, MsgWin):
    if rmsg[0] != 'F':
        gList = parse_members(rmsg)
        gList = sorted(gList, key=lambda x: x.name)
        mem_list = ["\t- Name: {} (IP: {}, port: {})".format(mem.name, mem.ip, mem.port) for mem in gList]
        mem_list = '\n'.join(mem_list)

        outstr = "\n[Join]\tRoomname: {}\n\tRoom members are as follows:".format(roomname)
        outstr += "\n" + mem_list
        CmdWin.insert(1.0, outstr)

    elif rmsg.startswith('F:JOIN message - Already joined another chatroom!!:'):
        outstr = "\n[Join] Error - Request rejected: Already joined another chatroom!!"
        CmdWin.insert(1.0, outstr)


def parse_members(msg_str, prefix="M:", suffix="::\r\n"):
    msg = parse_rmsg(msg_str, prefix=prefix, suffix=suffix)
    # M:15384212722403738702:u1:localhost:32340:u2:localhost:32340:u3:localhost:32340::
    # 15384212722403738702:u1:localhost:32340:u2:localhost:32340:u3:localhost:32340

    MSID = msg[0]
    mem_msg = msg[1:]
    mems = []
    assert len(mem_msg) % 3 == 0, "[Error] membership messsage is not a multiple of 3"
    for ix in range(len(mem_msg))[::3]:
        name = mem_msg[ix]
        ip = mem_msg[ix + 1]
        port = mem_msg[ix + 2]
        hash = sdbm_hash(name + ip + port)
        mem = Member(HashID=hash, name=name, ip=ip, port=int(port), backward=[])
        mems += [mem]
    gList = sorted(mems, key=lambda x: x.HashID, reverse=True)

    return gList


def parse_memberships(msg_str, prefix="M:", suffix="::\r\n"):
    # G:Name1:Name2:Name3::\r\n
    if not msg_str.startswith(prefix): print ("[Error] rmsg must start with {}, not {}".format(prefix, msg_str))
    if not msg_str.endswith(suffix): print ("[Error] rmsg must end with {}".format(suffix))

    msg_str = msg_str[len(prefix): -len(suffix)]

    # user_ID:IP:port
    return msg_str.split(':')
