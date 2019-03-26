from utils import sdbm_hash
from collections import OrderedDict


def query(msg_str, sockfd, recv_size=1000):
    msg = str.encode(msg_str)
    sockfd.send(msg)
    rmsg = sockfd.recv(recv_size).decode("utf-8")
    if rmsg == 'F:error message::\r\n':
        print("[Error] F:error message")

    return rmsg


def parse_rmsg(msg_str, prefix="G:", suffix="::\r\n"):
    # G:Name1:Name2:Name3::\r\n

    assert msg_str.startswith(prefix), "Groups must start with {}".format(prefix)
    assert msg_str.endswith(suffix), "Groups must end with {}".format(suffix)
    msg_str = msg_str[len(prefix): -len(suffix)]
    return msg_str.split(':')


def parse_members(msg_str, prefix="M:", suffix="::\r\n"):
    msg = parse_rmsg(msg_str, prefix=prefix, suffix=suffix)
    # M:15384212722403738702:u1:localhost:32340:u2:localhost:32340:u3:localhost:32340::
    # 15384212722403738702:u1:localhost:32340:u2:localhost:32340:u3:localhost:32340
    MSID = msg[0]
    mem_msg = msg[1:]
    mems = {}
    assert len(mem_msg) % 3 == 0, "[Error] membership messsage is not a multiple of 3"
    for ix in range(len(mem_msg))[::3]:
        name = mem_msg[ix]
        ip = mem_msg[ix + 1]
        port = mem_msg[ix + 2]
        hash = sdbm_hash(name + ip + port)
        mems[hash] = {'name': name, 'ip': ip, 'port': int(port)}
    mems = OrderedDict(sorted(mems.items()))
    for ix, hash in enumerate(mems):
        mems[hash]['ix'] = ix
    return mems


def parse_memberships(msg_str, prefix="M:", suffix="::\r\n"):
    # G:Name1:Name2:Name3::\r\n

    assert msg_str.startswith(prefix), "Memberships must start with {}".format(prefix)
    assert msg_str.endswith(suffix), "Memberships must end with {}".format(suffix)
    msg_str = msg_str[len(prefix): -len(suffix)]

    # user_ID:IP:port
    return msg_str.split(':')
