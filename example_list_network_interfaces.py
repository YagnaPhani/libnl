#!/usr/bin/env python
"""Shows all Netlink-compatible network interfaces on the host.

This is a pure-Python port of the C program available here:
    github.com/Robpol86/libnl/blob/master/example_c/list_network_interfaces.c

Derived from a Python test of libnl available here (URL split in two lines):
    github.com/Robpol86
    /libnl/blob/master/tests/linux_private/test_rtnetlink_rtattr.py#L12

This script is a showcase for the Linux Netlink libnl Python library, ported
from the C library with the same name. Using libnl, Python scripts/applications
can communicate with the Linux kernel and device drivers directly just like
C/C++ programs do, without having to call a binary on the system.

More information about the Python libnl is available here:
    https://github.com/Robpol86/libnl

Debug messages are available with the -v option, and even more debug messages
are available by setting the NLCB environment variable to either 'verbose' or
'debug' like so:
    NLCB=debug example_list_network_interfaces.py print -v

Usage:
    example_list_network_interfaces.py print [options]
    example_list_network_interfaces.py -h | --help

Options:
    -v --verbose    Print debug messages to stderr.
"""

import logging
import signal
import socket
import sys

from docopt import docopt
from libnl.handlers import NL_CB_CUSTOM, NL_CB_VALID, NL_OK
from libnl.linux_private.if_link import IFLA_IFNAME, IFLA_RTA
from libnl.linux_private.netlink import NETLINK_ROUTE, NLM_F_DUMP, NLM_F_REQUEST
from libnl.linux_private.rtnetlink import RTA_DATA, RTA_NEXT, RTM_GETLINK, ifinfomsg, rtgenmsg
from libnl.msg import nlmsg_data, nlmsg_hdr
from libnl.nl import nl_connect, nl_recvmsgs_default, nl_send_simple
from libnl.socket_ import nl_socket_alloc, nl_socket_modify_cb

OPTIONS = docopt(__doc__) if __name__ == '__main__' else dict()


def callback(msg, _):
    """Callback function called by libnl upon receiving messages from the kernel.

    Positional arguments:
    msg -- nl_msg class instance containing the data sent by the kernel.

    Returns:
    An integer, value of NL_OK. It tells libnl to proceed with processing the next kernel message.
    """
    # First convert `msg` into something more manageable.
    nlh = nlmsg_hdr(msg)
    iface = ifinfomsg.from_buffer(nlmsg_data(nlh))

    # Now iterate through each rtattr stored in `iface`.
    for hdr in RTA_NEXT(IFLA_RTA(iface)):
        # Each rtattr (which is what hdr is) instance is only one type. Looping through all of them until we run into
        # the ones we care about.
        if hdr.rta_type == IFLA_IFNAME:
            print('Found network interface {0}: {1}'.format(iface.ifi_index, str(RTA_DATA(hdr).decode('ascii'))))
    return NL_OK


def main():
    """Main function called upon script execution."""
    # First open a socket to the kernel. Same one used for sending and receiving.
    sk = nl_socket_alloc()  # Creates an `nl_sock` instance.
    nl_connect(sk, NETLINK_ROUTE)  # Create file descriptor and bind socket.

    # Next we send the request to the kernel.
    rt_hdr = rtgenmsg(rtgen_family=socket.AF_PACKET)
    ret = nl_send_simple(sk, RTM_GETLINK, NLM_F_REQUEST | NLM_F_DUMP, rt_hdr)
    print('Sent {0} bytes to the kernel.'.format(ret))

    # Finally we'll retrieve the kernel's answer, process it, and call any callbacks attached to the `nl_sock` instance.
    nl_socket_modify_cb(sk, NL_CB_VALID, NL_CB_CUSTOM, callback, None)  # Add callback to the `nl_sock` instance.
    nl_recvmsgs_default(sk)  # Get kernel's answer, and call attached callbacks.


def setup_logging():
    """Called when __name__ == '__main__' below. Sets up logging library.

    All logging messages go to stderr, from DEBUG to CRITICAL. This script uses print() for regular messages.
    """
    fmt = 'DBG<0>%(pathname)s:%(lineno)d  %(funcName)s: %(message)s'

    handler_stderr = logging.StreamHandler(sys.stderr)
    handler_stderr.setFormatter(logging.Formatter(fmt))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler_stderr)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))  # Properly handle Control+C
    if OPTIONS.get('--verbose'):
        setup_logging()
    main()