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

sys.path.append('.')

from utils import sdbm_hash
from build_socket import build_tcp_client, forward_link # retain_forward_link # build_tcp_server,
from interaction import query, parse_name, parse_rmsg, handle_join_rmsg, \
	parse_memberships, parse_members, keepalive

from time import sleep

#
# Global variables
#
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
sock_peers = {'backward': [], 'forward': None} # backward holds a list of hasIDs [hashID], forward holds hashID where this p2p is pointing at
my_tcp_server = None
my_tcp_conns = []
backward_link = [] #backward links
forwardlink = [] #forward links
multiproc = [] # a global list to manage the multi processing




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
		roomname = None
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
	global roomname, roomchat_ip, \
		multiproc, msgID, sock_peers, \
		my_tcp_conns
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

		# Step 2. keepalive, by sending JOIN msg to the chatroom app every 20 sec
		p = Process(target=keepalive, args=(msg_check_mem, roomchat_sock, username,))
		p.start()
		multiproc += [p]
		print('[Info] out of keepalive')

		# # Step 3. this is Zihao's poke function, enabling do_Poke()
		# if zihao:
		#     ## FIXME: if mysock is created inside the other process, mysock may still be None.
		#     if mysock == None:
		#         print("starts multi process")
		#         p = Process(target=set_my_server)  # , args=(shared_list,))
		#         p.start()
		#         multiproc += [p]
		#     else:
		#         print("we have established the server!")
		#     # set_my_server(1)

		myHashID = sdbm_hash("{}{}{}".format(username, myip, myport))
		print("hi I am here", flush=False)

		# Step 4. start my TCP server, as the server for other users to CONNECT to in the chatroom
		p = Process(target=build_tcp_server,
					args=(msg_check_mem,))
		p.start()
		multiproc += [p]

		# Step 5. start a TCP client, to CONNECT another user's TCP server in the chatroom
		print('[Info] Entering forward link establishment')
		gList = parse_members(rmsg)
		sock_peers, msgID, my_tcp_conns = \
			forward_link(gList, myHashID, sock_peers, roomname,
						 username, myip, myport, msgID, MsgWin, my_tcp_conns)

		# update my TCP client when a relevant user terminates
		# (when the user that you CONNECT to terminates, you need to connect to another TCP server instead)
		# TODO: for the following process, I need to reuse `msgID` and `my_tcp_conns`
		p = Process(target=retain_forward_link,
					args=(msg_check_mem, myHashID, msgID))
		p.start()
		multiproc += [p]

		# import pdb;
		# pdb.set_trace()




def do_Send():
	print('my_tcp_conns', my_tcp_conns)
	print('sock_peers', sock_peers)
	# print()
	if not username:
		CmdWin.insert(1.0, "\n[Error] You must have a username first.")
		return

	if not roomname:
		CmdWin.insert(1.0, "\n[Error] You must join a chatroom first.")
		return

	sendmsg = userentry.get()
	if not sendmsg:
		CmdWin.insert(1.0, "\n[Error] Empty message cannot be sent.")
		return

	CmdWin.insert(1.0, "\nPress Send")

	# s = socket.socket()
	# msg = 'K:{roomname}:{username}::\r\n'.format(roomname=roomname, username=username)
	# MsgWin.insert(1.0, "\n The message you are sending is " + msg)
	# idx = membermsg.index(targetname)
	# print("index of ", targetname, " is ", str.encode(msg),
	#       (membermsg[idx + 1], int(membermsg[idx + 2])), flush=False)
	#
	# s.sendto(str.encode(msg), (membermsg[idx + 1], int(membermsg[idx + 2])))
	# s.settimeout(2);
	#
	# try:
	#     rmsg = s.recvfrom(1000)  # .decode("utf-8")
	# except socket.timeout:
	#     CmdWin.insert(1.0, "\n[Error] Your [Poke] was not sent successfully")
	#     return
	# if not rmsg:
	#     print("failure", flush=False)
	#     CmdWin.insert(1.0, "\n[Error] Poke failure")
	# elif "A::\r\n" == rmsg[0].decode("utf-8"):
	#     print("success", flush=False)
	#     CmdWin.insert(1.0, "\n[Poke] You poked {}".format(targetname))
	# else:
	#     CmdWin.insert(1.0, "\n[Error] Poke failure")







def do_Poke():
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
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		msg = 'K:{roomname}:{username}::\r\n'.format(roomname=roomname, username=username)
		MsgWin.insert(1.0, "\n The message you are sending is " + msg)
		idx = membermsg.index(targetname)
		print("index of ", targetname, " is ", str.encode(msg),
			  (membermsg[idx + 1], int(membermsg[idx + 2])), flush=False)

		s.sendto(str.encode(msg), (membermsg[idx + 1], int(membermsg[idx + 2])))
		s.settimeout(2);

		try:
			rmsg = s.recvfrom(1000)  # .decode("utf-8")
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
	global my_tcp_server, my_tcp_conns
	CmdWin.insert(1.0, "\nPress Quit")
	roomchat_sock.close()
	print("[Info] Closed socket")

	if my_tcp_server is not None:
		my_tcp_server.close()
		for conn in my_tcp_conns:
			conn.close()
		print("[Info] Closed tcp_conn, tcp_server")

	for p in multiproc:
		p.terminate()
		p.join()
	print("[Info] Closed multiprocessing")

	sys.exit(0)

def build_tcp_server(msg_check_mem):
	global myip, myport, roomchat_sock, backward_link, MsgWin, CmdWin
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

	while True:
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

					# add the backward link to connections
					print("before accept", backward_link)
					backward_link += [conn]
					RList += [conn]
					print("after accept", backward_link)

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
				# else:
				# 	print('I am in tcp chatting')


	# TODO: is this the right termination?
	sockfd.close()
	conn.close()

def retain_forward_link(msg_check_mem, myHashID, msgID):
	global my_tcp_conns, roomname, username, myip, myport, MsgWin, roomchat_sock, sock_peers, forward_link
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
