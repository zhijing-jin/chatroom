import time
from utils import sdbm_hash, show_time
from collections import OrderedDict
from tkinter import END


def query(msg_str, sockfd, recv_size=1000):
    msg = str.encode(msg_str)
    sockfd.send(msg)
    rmsg = sockfd.recv(recv_size).decode("utf-8")
    if rmsg == 'F:error message::\r\n':
        print("[Error] F:error message, for input:", msg_str)

    return rmsg


def parse_name(userentry, length=32):
    name = userentry.get()
    name = [c for c in name if c != ':'][:length]
    name = ''.join(name)
    userentry.delete(0, END)

    return name

def parse_rmsg(msg_str, prefix="G:", suffix="::\r\n"):
    # G:Name1:Name2:Name3::\r\n

    assert msg_str.startswith(prefix), "rmsg must start with {}, not {}".format(prefix, msg_str)
    assert msg_str.endswith(suffix), "rmsg must end with {}".format(suffix)
    msg_str = msg_str[len(prefix): -len(suffix)]
    return msg_str.split(':')

def parse_send_message(msg_str, prefix="T:", suffix="::\r\n"):
    assert msg_str.startswith(prefix), "rmsg must start with {}, not {}".format(prefix, msg_str)
    assert msg_str.endswith(suffix), "rmsg must end with {}".format(suffix)
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
        outstr = "\n[Join] roomname: " + roomname
        CmdWin.insert(1.0, outstr)
    elif rmsg.startswith('F:JOIN message - Already joined another chatroom!!:'):
        outstr = "\n[Join] Error - Request rejected: Already joined another chatroom!!"
        CmdWin.insert(1.0, outstr)
    MsgWin.insert(1.0, "\n[Join] received msg: {}".format(rmsg))

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




class Member(object):
    def __init__(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])


def parse_memberships(msg_str, prefix="M:", suffix="::\r\n"):
    # G:Name1:Name2:Name3::\r\n

    assert msg_str.startswith(prefix), "Memberships must start with {}".format(prefix)
    assert msg_str.endswith(suffix), "Memberships must end with {}".format(suffix)
    msg_str = msg_str[len(prefix): -len(suffix)]

    # user_ID:IP:port
    return msg_str.split(':')


def keepalive(msg, sockfd, txt='', interval=20):
    while True:
        # second = datetime.datetime.now().strftime('%m%d%H%M-%S')[-2:]
        # if int(second) % 20 == 0:
        time.sleep(interval)
        # show_time(txt)
        rmsg = query(msg, sockfd)
