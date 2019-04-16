#
# This is the hash function for generating a unique
# Hash ID for each peer.
# Source: http://www.cse.yorku.ca/~oz/hash.html
#
# Concatenate the peer's username, str(IP address),
# and str(Port) to form a string that be the input
# to this hash function
#
import asyncio


def sdbm_hash(instr):
    hash = 0
    for c in instr:
        hash = int(ord(c)) + (hash << 6) + (hash << 16) - hash
    return hash & 0xffffffffffffffff


def mproc_res(func, input_args):
    '''
    This is a multiprocess function where you execute the function with
    every input in the input_list simutaneously.
    @ return output_list: the list of outputs w.r.t. input_list
    '''
    from multiprocessing import Pool
    pool = Pool(processes=1)
    input_list = [input_args]
    output_list = pool.map(func, input_list)
    return output_list


def multiproc():
    import time
    import multiprocessing

    def worker(text):
        while True:
            time.sleep(5)
            show_time(text)

    jobs = []
    sublists = ['job_1', 'job_2']
    for entry in sublists:
        p = multiprocessing.Process(target=worker, args=(entry,))
        jobs.append(p)
        p.start()
        time.sleep(1)
    worker('job_3')


def show_time(what_happens='', cat_server=False, printout=True):
    import datetime

    disp = '\ttime: ' + \
           datetime.datetime.now().strftime('%m%d%H%M-%S')
    disp = disp + '\t' + what_happens if what_happens else disp
    if printout:
        print(disp)
    curr_time = datetime.datetime.now().strftime('%m%d%H%M-%S')

    if cat_server:
        hostname = socket.gethostname()
        prefix = "rosetta"
        if hostname.startswith(prefix):
            host_id = hostname[len(prefix):]
            try:
                host_id = int(host_id)
                host_id = "{:02d}".format(host_id)
            except:
                pass
            hostname = prefix[0] + host_id
        else:
            hostname = hostname[0]
        curr_time += hostname
    return curr_time


def mproc_func(text):
    import time
    for i in range(5):
        time.sleep(10)
        show_time(text)
    return i


async def async_func(text):
    for i in range(5):
        # await asyncio.sleep(1)
        show_time(text)
    return text


@asyncio.coroutine
def async_cor_func(text):
    for i in range(5):
        yield from asyncio.sleep(1)
        show_time(text)
    return text


def asy3():
    import asyncio
    import time

    start = time.time()
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(async_func("A"), loop=loop)
    asyncio.ensure_future(async_func("B"), loop=loop)

    done, _ = loop.run_until_complete(asyncio.wait(tasks))
    for fut in done:
        print("return value is {}".format(fut.result()))
    loop.close()
    end = time.time()
    print("Total time: {}".format(end - start))


def asy2():
    import asyncio
    import time

    start = time.time()
    loop = asyncio.get_event_loop()
    tasks = [
        asyncio.ensure_future(async_func("A")),
        asyncio.ensure_future(async_func("B")),
    ]
    done, _ = loop.run_until_complete(asyncio.wait(tasks))
    for fut in done:
        print("return value is {}".format(fut.result()))
    loop.close()
    end = time.time()
    print("Total time: {}".format(end - start))


def asy():
    import asyncio

    @asyncio.coroutine
    def func_normal():
        print('A')
        yield from asyncio.sleep(5)
        print('B')
        return 'saad'

    @asyncio.coroutine
    def func_infinite():
        for i in range(10):
            print("--%d" % i)
        return 'saad2'

    loop = asyncio.get_event_loop()
    tasks = func_normal(), func_infinite()
    a, b = loop.run_until_complete(asyncio.gather(*tasks))
    print("func_normal()={a}, func_infinite()={b}".format(**vars()))
    loop.close()


if __name__ == "__main__":
    # multiproc()
    '''
    input_args = 'hiii'
    res = mproc_res(mproc_func, input_args)
    print("[info] out of mproc")
    print("[info] res")
    '''
    asy2()
