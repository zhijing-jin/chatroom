#
# This is the hash function for generating a unique
# Hash ID for each peer.
# Source: http://www.cse.yorku.ca/~oz/hash.html
#
# Concatenate the peer's username, str(IP address),
# and str(Port) to form a string that be the input
# to this hash function
#
def sdbm_hash(instr):
    hash = 0
    for c in instr:
        hash = int(ord(c)) + (hash << 6) + (hash << 16) - hash
    return hash & 0xffffffffffffffff


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
    curr_time = datetime.datetime.now().strftime('%m%d%H%M')

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


if __name__ == "__main__":
    multiproc()