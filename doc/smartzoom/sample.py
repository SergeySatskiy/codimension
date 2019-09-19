from socket import socket, error, AF_INET, SOCK_STREAM, gethostbyname, gaierror
import sys

def createSocket():
    """Creates a socket"""
    try:
        s = socket(AF_INET, SOCK_STREAM)
    except error as err:
        print("Socket creation failed")
        print(str(err))
        return None
    except:
        print("Unknown error")
    return s

# First create a socket
s = createSocket()
if s is None:
    sys.exit(1)

try:
    hostIP = gethostbyname('www.google.com')
except gaierror:
    # Could not resolve the host
    print("Host resolving error")
    sys.exit()

# Connecting to the google server
s.connect((hostIP, 80))

