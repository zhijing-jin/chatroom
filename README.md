# chatroom

## News (15 Apr)
- Bug1: Sometimes the 1st message by `do_Send()` is duplicated.
- Bug2: `do_Quit()`: only need to paraphrase `Rready, Wready, Eready = select.select(RList, [], [], 10)`


## New Progress:
Zhijing debugged `do_Quit()`.
- Action 1: close the threads in a certain order, because sockets need to be closed at last
- Action 2: debugged `keepalive`-> abandoned `time.sleep()`, used `threading.Event().wait()` instead.
- Action 2: debugged `select.select`-> abandoned `timeout=10`, used `timeout=1` as a temporary solution instead.

## Stage One (by Mar 26)
Stage one includes the following functions:
- `Zhijing` do_User()
- `Zihao` do_List()
- `Zhijing` part of the do_Join() function, which involves the interactions between the P2PChat program and
the Room server in handling the JOIN request and the subsequent JOIN requests in the KEEPALIVE procedure. To show that the program has successfully joined the chatroom, it simply displays the members’ info to the Command Window.
- `Zihao` do_Poke()

## Stage Two (by Apr 10)
- `Zhijing` do_Join()
- `Zihao` do_Send()
- `Zhijing` do_Quit() 
- `Zihao` Multithreading
