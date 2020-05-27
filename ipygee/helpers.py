# coding=utf-8


def formatSize(size):
    """ convert the size (in Bytes) parsed into the first unit greater than zero. Return
    the size and the unit.
    For example:
    formatSize(1024) -> 1, KB
    formatSize(1000) -> 1000, Bytes
    formatSize(1024**2) -> 1, MB
    """
    size = float(size)
    #     Bytes = 1024
    #     KB = 1024**2
    #     MB = 1024**3
    #     GB = 1024**4
    #     TB = 1024**5
    Bytes = 1
    KB = 1024
    MB = 1024**2
    GB = 1024**3
    TB = 1024**4
    options = [TB, GB, MB, KB, Bytes]
    names = ['TB', 'GB', 'MB', 'KB', 'Bytes']
    for opt in options:
        s = size/opt
        i = options.index(opt)
        if s<1 and i<len(options)-1:
            continue
        return s, names[i]