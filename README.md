# chatroom

## To do (16 Apr)
- Bug: Sometimes the 1st message by `do_Send()` is duplicated.
- Change logging:  "Poke: The message you are sending is K:a:4::"

## Trivial
- [fixed] Join takes 10 seconds
- [fixed] do_Join's backward,forward has problems
- [fixed] change client_thread select.select(,,,1)
- [fixed] poke cannot be successful
- when restarting, we found that the port is not already released.
- Bug2: `do_Quit()`: only need to paraphrase `Rready, Wready, Eready = select.select(RList, [], [], 10)`
- need to lock `query`

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
