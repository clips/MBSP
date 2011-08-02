#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# Vincent Van Asch <vincent.vanasch@ua.ac.be>, Tom De Smedt <tom@organisms.be>
# License: GNU General Public License, see LICENSE.txt

### CLIENT ###########################################################################################
# Python interface for MBT and TiMBL clients.
#
# MBT is a memory-based tagger-generator and tagger in one. 
# The tagger-generator part can generate a sequence tagger on the basis of a training set of tagged sequences; 
# the tagger part can tag new sequences. MBT can, for instance, be used to generate part-of-speech taggers or 
# chunkers for natural language processing.
# http://ilk.uvt.nl/mbt/
#
# TiMBL: Memory-Based Learning (MB L) is an elegantly simple and robust machine-learning method 
# applicable to a wide range of tasks in Natural Language Processing (NLP).
# http://ilk.uvt.nl/timbl/
#
# MBSP uses MBT to look for part-of-speech tags and chunk tags, 
# and TiMBL to look for relation tags and preposition tags.
# This module implements a Client class with Timbl and Mbt subclasses.
# Example usage:
# >>> from server import servers
# >>> servers.chunk.start()
# >>> client = Client(port=servers.chunk.port)
# >>> instance = 'Good morning\n'
# >>> print client.tag(instance)
# 'Good/JJ/I-NP morning/NN/I-NP <utt>'
# To disconnect:
# >>> client.disconnect()

import re, socket, threading, time
import config
import cache

from config import LOCALHOST

# Cache the lookup instances, for evaluation or reuse.
# Server requests and responses are only logged when config.log = True.
# Each server (e.g. log[RELATION]) has a separate cache of requests and responses.
# Each server cache is an ordered dictionary, so it's pretty fast.
# A 1000 instances per server (CHUNK / RELATION / PREPOSITION / LEMMA) amounts to roughly 1MB cache.
log = _log = cache.Log()

#--- CLIENT ------------------------------------------------------------------------------------------

class ClientError(Exception):
    def __init__(self, message='', code=None):
        # The additional code field stores the underlying socket.error for ServerConnectionError.
        Exception.__init__(self, message)
        self.code=code
        
class ClientDisconnectedError(ClientError):
    pass
class ClientTimeoutError(ClientError):
    pass
class ServerConnectionError(ClientError):
    pass
class ServerBusyError(ClientError):
    pass

# Possible socket.error codes:
CONNECTION_RESET_BY_PEER = (54, 'Connection reset by peer')
CONNECTION_REFUSED = (61, 'Connection refused')
BROKEN_PIPE = (32, 'Broken pipe')

class Client:
    
    def __init__(self, host=LOCALHOST, port=6060, name=None, log=False, request=lambda v:v.strip()+'\n', response=lambda v:v):
        """ Creates a new client for communicating with a TiMBL/MBT server.
            - host     : the server address, localhost by default.
            - port     : the server tcp communicating port.
            - name     : the server name, used to reference log entries (host:port by default).
            - log      : log requests sent and answers received from the server?
            - request  : a function used to prepare the request sent to the server.
            - response : a function used to format the response sent from the server.
        """
        self.host = host
        self.port = port
        self.name = name or "%s:%s" % (self.host, self.port)
        self.log  = log
        self.format_request  = request
        self.format_response = response
        self.packet_size = 1024
        self._count = 0
        self._reset = 100 # Reconnect every few tagging jobs.
        self._socket = None
        self.connect()
        # Create a log for this client's requests and responses.
        # The log entry will be empty unless Client.log=True.
        if not self.name in _log:
            _log.create(self.name, size=1000, hashed=False)

    def connect(self):
        """ Connects to the server at the given host:port.
            A ServerConnectionError is raised if the server can not be reached.
        """
        try:
            self._count  = 0
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.getprotobyname('tcp'))
            self._socket.connect((self.host, self.port))
            self._socket.recv(self.packet_size)
        except socket.error, code:
            s = "can't connect to server at %s:%s" % (self.host, self.port)
            raise ServerConnectionError(s, code)

    def _stream(self, timeout=None):
        """ Returns the server response.
        """
        # This is the place where MBSP will spend most of its time.
        # Optimized for speed by using reversed(), and a list instead of += on a string.
        # Since this can be called as a background process, it is a good idea to supply
        # a timeout to ensure the function doesn't hang.
        t = time.time()
        packets = [self._socket.recv(self.packet_size)]
        # "I'm done\n" => check "\nenod m'I" to quickly find the \n.
        while '\n' not in reversed(packets[-1]) or (packets[-1] == "\n" and len(packets) == 1):
            if timeout is not None and time.time()-t > timeout: 
                raise ClientTimeoutError
            time.sleep(0.01)
            packets.append(self._socket.recv(self.packet_size))
        return "".join(packets)

    def send(self, request, timeout=None):
        """ Takes a lookup instance of which the tag must be determined.
            - request : a string, formatted with Client.format_request() before sent.
            - timeout : the time (in seconds) before giving up contacting the server, or None.
            Returns the server's answer as a string, formatted with Client.format_response().
            Lookup instances and the server's response can be inspected in client.log[client.name].
            Can raise ClientDisconnectedError, ClientTimeoutError or ServerConnectionError.
        """
        if request.strip() == "":
            return self.format_response("")
        if self.log and request in _log[self.name]:
            # If we have the request in cache we don't need to contact the server.
            return self.format_response(_log[self.name][request])
        if self._count > self._reset:
            # Reset the client every few tagging jobs.
            self.reconnect()
        Q = self.format_request(request)
        try:
            # Send the request to the server and wait for response.
            self._count += 1
            self._socket.send(Q)
            response = self._stream(timeout)
        except AttributeError: 
            # Raised when Client._socket is None (client is disconnected).
            s = "disconnected from server at %s:%s" % (self.host, str(self.port))
            raise ClientDisconnectedError(s)
        except socket.error, code:
            # Raised when Client._socket.send() can't contact the server.
            s = "can't connect to server at %s:%s" % (self.host, str(self.port))
            raise ServerConnectionError(s, code)
        except ClientTimeoutError:
            # Raised when Client._stream() times out.
            s = "couldn't get a response from server at %s:%s in %s seconds" % (self.host, str(self.port), str(timeout))
            raise ClientTimeoutError(s)
        if response == 'try again later...\n':
            # Raised when the number of allowed connections to a multithreaded server is exceeded.
            s = "restart the server at %s:%s" % (self.host, str(self.port))
            raise ServerBusyError
        if self.log:
            # Cache the request and the response from the server.
            _log[self.name].append((request, response))
        return self.format_response(response)
    tag = send
            
    def reconnect(self):
        self.disconnect()
        self.connect()

    def disconnect(self):
        try:
            self._socket.close()
            self._socket = None
        except:
            pass
            
    @property
    def connected(self):
        return self._socket is not None

    def copy(self):
        client = self.__class__(self.host, self.port, self.name, self.log)
        client.format_request  = self.format_request
        client.format_response = self.format_response
        client.packet_size = self.packet_size
        return client

    def __del__(self):
        self.disconnect()

    def __repr__(self):
        return "<Client host='%s', port='%s'>" % (self.host, str(self.port))

#--- TIMBL & MBT CLIENT ------------------------------------------------------------------------------
# Depending on whether it is a TiMBL or MBT client, requests and responses have a different format.
# We can easily define them in subclasses of Client.

O, F, P, E, N, K, AS, CM, CS, MD, DI, DB  = "o", "f", "p", "e", "n", "k", "as", "cm", "cs", "md", "di", "db"
# The output format of TiMBL depends on the settings of the verbosity feature (+v).
# For example, a server with "+v di+db" also outputs a distance and distribution metric.
# This results in the following response format:
#  CATEGORY {0} DISTRIBUTION { 0 1.00000 } DISTANCE {1.02354}
#  CATEGORY {1} DISTRIBUTION { 1 0.872453, 0 0.127547 } DISTANCE {0.0688261}
# We extract the full response as a (category, distance, distribution dict)-tuple.

RE_CATEGORY     = re.compile(r'CATEGORY \{([^}]+)\}')
RE_DISTANCE     = re.compile(r'DISTANCE \{([^}]+)\}')
RE_DISTRIBUTION = re.compile(r'DISTRIBUTION \{([^}]+)\}')

# Each option has a regular expression parser, a default value and an output formatter:
_verbosity = {
 "category" : (RE_CATEGORY, "", lambda v: v),
          O : (None, None, None), # Most of these still need to be implemented.
          F : (None, None, None), #
          P : (None, None, None), #
          E : (None, None, None), #
          N : (None, None, None), #
          K : (None, None, None), #
         AS : (None, None, None), #
         CM : (None, None, None), #
         CS : (None, None, None), #
         MD : (None, None, None), #
         DI : (RE_DISTANCE,     0.0, lambda v: float(v)),
         DB : (RE_DISTRIBUTION,  "", lambda v: dict([(x.strip().split(" ")[0], 
                                           float(x.strip().split(" ")[1])) for x in v.split(",")])),
}

def timbl_format_request(v):
    """ Ensures that the instance string starts with a "c" and ends with "?\n".
    """
    v = v.strip()
    if not v.startswith("c"): v = "c "+v
    if not v.endswith("?")  : v = v+" ?"
    return v+"\n"
    
def timbl_format_response(v, verbosity=[]):
    """ Extracts the "CATEGORY {}" from the TiMBL response, returns the value.
        When vebosity=None, extracts all verbosity keys that can be found as a dictionary.
        When verbosity is a list of options, returns the values as a list.
    """  
    def _parse(options=[]):
        results = []
        for o in options:
            pattern, default, format = _verbosity[o.lower()]
            x = pattern and pattern.search(v) or None
            x = x and x.group(1) or default
            x = format and format(x) or x
            results.append(x)
        return results
    if verbosity is None:
        # Parse all options that can be extracted from the response.
        return dict(zip(_verbosity.keys(), _parse(options=_verbosity.keys())))
    if len(verbosity) == 0:
        # Parse the category from the response.
        return _parse(options=["category"])[0]
    else:
        # Parse all given options, always starting with the category.
        return _parse(options=["category"]+[k for k in verbosity if k != "category"])

class Timbl(Client):
    
    def __init__(self, host=LOCALHOST, port=6060, name=None, log=False, verbosity=[]):
        """ A client suited for TiMBL requests.
            The different features in the instance must be separated by whitespace.
        """
        Client.__init__(self, host, port, name, log)
        self.verbosity = verbosity
        self.format_request  = timbl_format_request
        self.format_response = lambda v: v

    def send(self, request, timeout=None):
        return timbl_format_response(Client.send(self, request, timeout), self.verbosity)
    tag = send

class TimblPP(Timbl):
    
    def __init__(self, host=LOCALHOST, port=6060, name=None, log=False, verbosity=[DI,DB]):
        """ A client suited for TiMBL PP-attachment 
            (see mbsp._find_pp_attachments()).
        """
        Timbl.__init__(self, host, port, name, log, verbosity)

class Mbt(Client):
    
    def __init__(self, host=LOCALHOST, port=6060, name=None, log=False):
        """ A client with request and response formatters suited for MBT chunking.
            (see mbsp._chunk()).
        """
        Client.__init__(self, host, port, name, log)
        self.format_request  = lambda v: v.strip()+'\n'
        self.format_response = lambda v: v[:-len("<utt>")-1].strip().replace("//","/")

#### CLIENT TOOLS ####################################################################################

#--- ASYNCHRONOUS REQUEST ---------------------------------------------------------------------------

class AsynchronousRequest:
    
    def __init__(self, function, *args, **kwargs):
        """ Executes the function in the background.
            AsynchronousRequest.done is False as long as it is busy, but the program will not halt in the meantime.
            AsynchronousRequest.value contains the function's return value once done.
            AsynchronousRequest.error contains the Exception raised by an erronous function.
            For example, this is useful for running live web request while keeping an animation running.
            For good reasons, there is no way to interrupt a background process (i.e. Python thread).
            You are responsible for ensuring that the given function doesn't hang.
        """
        self._response = None # The return value of the given function.
        self._error    = None # The exception (if any) raised by the function.
        self._time     = time.time()
        self._thread   = threading.Thread(target=self._fetch, args=(function,)+args, kwargs=kwargs)
        self._thread.start()
        
    def _fetch(self, function, *args, **kwargs):
        try: 
            self._response = function(*args, **kwargs)
        except Exception, e:
            self.error = e

    def now(self):
        """ Waits for the function to finish and yields its return value.
        """
        self._thread.join(); return self._response

    @property
    def elapsed(self):
        return time.time() - self._time
    @property
    def done(self):
        return not self._thread.isAlive()
    @property
    def value(self):
        return self._response
    @property
    def error(self):
        return self._error

def asynchronous(function, *args, **kwargs):
    return AsynchronousRequest(function, *args, **kwargs)

#--- BATCH ------------------------------------------------------------------------------------------

def define(client, host=LOCALHOST, port=6060, name=None, log=False):
    """ Used to create the 'client' parameter of the batch() function.
    """
    return (client, host, port, name, log)

def batch(instances, client, timeout=None, retries=1):
    """ Sends a batch of requests to a server while keeping the creation of clients to a minimum.
        Multithreading can be used by enabling it in config.py (TimblServer 1.0.0+ is recommended).
        - instances : a list of requests, each will be sent with Client.send().
        - client    : a (Client, host, port, name, log)-tuple for when a client object needs to be created.
        - timeout   : the amount of time per request before giving up.
        - retries   : the number of retries after a ServerConnectionError before giving up.
    """
    if config.threading and len(instances) > 1:
        return batch_multithreaded(instances, client, timeout, retries)
    else:
        return batch_singlethreaded(instances, client, timeout, retries)

_clients = {}
def batch_singlethreaded(instances, client, timeout=None, retries=1):
    Client, host, port, name, log = client
    grace = True
    i = 0
    while i < 1 + retries:
        try:
            global _clients
            if not _clients.get(name, None):
                _clients[name] = Client(host, port, name, log)
            return [_clients[name].send(x, timeout) for x in instances]
        except ClientDisconnectedError, e:
                _clients[name] = None
        except ServerConnectionError, e:
            if _clients.get(name, None):
                _clients[name].disconnect()
                _clients[name] = None
            if e.code[0] == CONNECTION_RESET_BY_PEER[0] and grace: 
                # If the servers have stopped (or restarted), 
                # any clients in the cache become invalid (e.g. outdated) and raise a CONNECTION_RESET_BY_PEER.
                # Refreshing these doesn't really count as an error, so we get an extra try afterwards.
                i -= 1; grace = False
            i += 1
    # Server is down, raise the ServerConnectionError.
    s = "can't connect to server '%s' at %s:%s" % (name, host, port)
    raise ServerConnectionError(s)

def batch_multithreaded(instances, client, timeout=None, retries=1):
    Client, host, port, name, log = client
    grace = True
    i, n, v = 0, 10, []
    while i < len(instances) / float(n):
        # Create a queue of 10 asynchronous Client.send() calls, started simultaneously.
        # Wait until all of them have finished. Append the return values to the v list.
        clients, jobs = [], []
        for x in instances[i*n:i*n+n]:
            clients.append(Client(host, port, name, log))
            jobs.append(asynchronous(clients[-1].send, x, timeout))
            time.sleep(0.01)
        done = False
        while not done:
            done  = len([job for job in jobs if not job.done]) == 0
            error = ([job.error for job in jobs if job.error] or [None])[0]
            if error:
                done = True
                if isinstance(error, ServerConnectionError) and \
                   error.code[0] == CONNECTION_RESET_BY_PEER[0] and grace:
                    # See batch_singlethreaded() above.
                    i -= 1; grace = False; error = None; jobs = None
            time.sleep(0.01)
        for client in clients:
            client.disconnect()
        if error:
            raise error
        if jobs is not None:
            v.extend([job.value for job in jobs])
        i += 1
    return v

######################################################################################################

#from time import time
#t = time()
#
#jobs = ["' How do you know I 'm mad ? ' said Alice .", 
#        "' You must be , ' said the Cat , ' or you would n't have come here . '",]
#print batch(jobs, client=(Mbt, 'localhost', 6061, "chunk", False), retries=1)
#print time()-t