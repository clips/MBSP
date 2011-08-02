/*
 *  This file is provided for use with the unix-socket-faq.  It is public
 *  domain, and may be copied freely.  There is no copyright on it.  The
 *  original work was by Vic Metcalfe (vic@brutus.tlug.org), and any
 *  modifications made to that work were made with the understanding that
 *  the finished work would be in the public domain.
 *
 *  If you have found a bug, please pass it on to me at the above address
 *  acknowledging that there will be no copyright on your work.
 *
 *  The most recent version of this file, and the unix-socket-faq can be
 *  found at http://www.interlog.com/~vic/sock-faq/.
 */

#include "sockhelp.h"
/* #include <iostream.h> */

/* Take a service name, and a service type, and return a port number.  If the
   service name is not found, it tries it as a decimal number.  The number
   returned is byte ordered for the network. */
int atoport(char *service,char *proto)
{
  int port;
  long int lport;
  struct servent *serv;
  char *errpos;

  /* First try to read it from /etc/services */
  serv = getservbyname(service, proto);
  if (serv != NULL)
    port = serv->s_port;
  else { /* Not in services, maybe a number? */
    lport = strtol(service,&errpos,0);
    if ( (errpos[0] != 0) || (lport < 1) || (lport > 65535) )
      return -1; /* Invalid port address */
    port = htons(lport);
  }
  return port;
}

/* Converts ascii text to in_addr struct.  NULL is returned if the address
   can not be found. */
struct in_addr *atoaddr(char *address)
{
  struct hostent *host;
  static struct in_addr saddr;

  /* First try it as aaa.bbb.ccc.ddd. */
  saddr.s_addr = inet_addr(address);
  if (saddr.s_addr != -1) {
    return &saddr;
  }
  host = gethostbyname(address);
  if (host != NULL) {
    return (struct in_addr *) *host->h_addr_list;
  }
  return NULL;
}

/* This function listens on a port, and returns connections.  It forks
   returns off internally, so your main function doesn't have to worry
   about that.  This can be confusing if you don't know what is going on.
   The function will create a new process for every incoming connection,
   so in the listening process, it will never return.  Only when a connection
   comes in, and we create a new process for it will the function return.
   This means that your code that calls it should _not_ loop.

   The parameters are as follows:
     socket_type: SOCK_STREAM or SOCK_DGRAM (TCP or UDP sockets)
     port: The port to listen on.  Remember that ports < 1024 are
       reserved for the root user.  Must be passed in network byte
       order (see "man htons").
     listener: This is a pointer to a variable for holding the file
       descriptor of the socket which is being used to listen.  It
       is provided so that you can write a signal handler to close
       it in the event of program termination.  If you aren't interested,
       just pass NULL.  Note that all modern unixes will close file
       descriptors for you on exit, so this is not required. */
int get_connection(int socket_type,u_short port,int *listener)
{
  struct sockaddr_in address;
  int listening_socket;
  int connected_socket = -1;
  int new_process;
  int reuse_addr = 1;

  /* Setup internet address information.  
     This is used with the bind() call */
  memset((char *) &address, 0, sizeof(address));
  address.sin_family = AF_INET;
  address.sin_port = port;
  address.sin_addr.s_addr = htonl(INADDR_ANY);

  listening_socket = socket(AF_INET, socket_type, 0);
  if (listening_socket < 0) {
    perror("socket");
    exit(EXIT_FAILURE);
  }

  if (listener != NULL)
    *listener = listening_socket;

  setsockopt(listening_socket, SOL_SOCKET, SO_REUSEADDR, (char*) &reuse_addr, 
    sizeof(reuse_addr));

  if (bind(listening_socket, (struct sockaddr *) &address, 
    sizeof(address)) < 0) {
    perror("bind");
    close(listening_socket);
    exit(EXIT_FAILURE);
  }

  if (socket_type == SOCK_STREAM) {
    listen(listening_socket, 5); /* Queue up to five connections before
                                  having them automatically rejected. */

    while(connected_socket < 0) {
      connected_socket = accept(listening_socket,NULL, NULL);
      if (connected_socket < 0) {
        /* Either a real error occured, or blocking was interrupted for
           some reason.  Only abort execution if a real error occured. */
        if (errno != EINTR) {
          perror("accept");
          close(listening_socket);
          exit(EXIT_FAILURE);
        } else {
          continue;    /* don't fork - do the accept again */
        }
      }


      new_process = fork();
      if (new_process < 0) {
        perror("fork");
        close(connected_socket);
        connected_socket = -1;
      }
      else { /* We have a new process... */
        if (new_process == 0) {
          /* This is the new process. */
          close(listening_socket); /* Close our copy of this socket */
	  if (listener != NULL)
	          *listener = -1; /* Closed in this process.  We are not 
				     responsible for it. */
        }
        else {
          /* This is the main loop.  Close copy of connected socket, and
             continue loop. */
          close(connected_socket);
          connected_socket = -1;
        }
      }
    }
    return connected_socket;
  }
  else
    return listening_socket;
}

/* This is a generic function to make a connection to a given server/port.
   service is the port name/number,
   type is either SOCK_STREAM or SOCK_DGRAM, and
   netaddress is the host name to connect to.
   The function returns the socket, ready for action.*/
int make_connection(char *service,int type,char *netaddress)
{
  /* First convert service from a string, to a number... */
  int port = -1;
  struct in_addr *addr;
  int sock, connected;
  struct sockaddr_in address;

  if (type == SOCK_STREAM) 
    port = atoport(service, "tcp");
  if (type == SOCK_DGRAM)
    port = atoport(service, "udp");
  if (port == -1) {
    fprintf(stderr,"make_connection:  Invalid socket type.\n");
    return -1;
  }
  addr = atoaddr(netaddress);
  if (addr == NULL) {
    fprintf(stderr,"make_connection:  Invalid network address.\n");
    return -1;
  }
 
  memset((char *) &address, 0, sizeof(address));
  address.sin_family = AF_INET;
  address.sin_port = (port);
  address.sin_addr.s_addr = addr->s_addr;

  sock = socket(AF_INET, type, 0);

  /* printf("Connecting to %s on port %d.\n",inet_ntoa(*addr),htons(port)); */

  if (type == SOCK_STREAM) {
    connected = connect(sock, (struct sockaddr *) &address, 
      sizeof(address));
    if (connected < 0) {
      perror("connect");
      return -1;
    }
    return sock;
  }
  /* Otherwise, must be for udp, so bind to address. */
  if (bind(sock, (struct sockaddr *) &address, sizeof(address)) < 0) {
    perror("bind");
    return -1;
  }
  return sock;
}

/* This is just like the read() system call, accept that it will make
   sure that all your data goes through the socket. */
int sock_read(int sockfd,char *buf,size_t count)
{
  size_t bytes_read = 0;
  int this_read;

  while (bytes_read < count) {
    do
      this_read = read(sockfd, buf, count - bytes_read);
    while ( (this_read < 0) && (errno == EINTR) );
    if (this_read < 0)
      return this_read;
    else if (this_read == 0)
      return bytes_read;
    bytes_read += this_read;
    buf += this_read;
  }
  return count;
}

/* This is just like the write() system call, accept that it will
   make sure that all data is transmitted. */
int sock_write(int sockfd,const char *buf,size_t count)
{
  size_t bytes_sent = 0;
  int this_write;

  while (bytes_sent < count) {
    do
      this_write = write(sockfd, buf, count - bytes_sent);
    while ( (this_write < 0) && (errno == EINTR) );
    if (this_write <= 0)
      return this_write;
    bytes_sent += this_write;
    buf += this_write;
  }
  return count;
}

/* This function reads from a socket, until it recieves a linefeed
   character.  It fills the buffer "str" up to the maximum size "count".

   This function will return -1 if the socket is closed during the read
   operation.

   Note that if a single line exceeds the length of count, the extra data
   will be read and discarded!  You have been warned. */
int sock_gets(int sockfd,char *str,size_t count)
{
  int bytes_read;
  int total_count = 0;
  char *current_position;
  char last_read = 0;

  current_position = str;
  while (last_read != 10) {
    bytes_read = read(sockfd, &last_read, 1);
    if (bytes_read <= 0) {
      /* The other side may have closed unexpectedly */
      return -1; /* Is this effective on other platforms than linux? */
    }
    if ( (total_count < (signed) count) && (last_read != 10) && (last_read !=13) ) {
      current_position[0] = last_read;
      current_position++;
      total_count++;
    }
  }
  if (count > 0)
    current_position[0] = 0;
  return total_count;
}

/* This function writes a character string out to a socket.  It will 
   return -1 if the connection is closed while it is trying to write. */
int sock_puts(int sockfd,const char *str)
{
  return sock_write(sockfd, str, strlen(str));
}

/* This ignores the SIGPIPE signal.  This is usually a good idea, since
   the default behaviour is to terminate the application.  SIGPIPE is
   sent when you try to write to an unconnected socket.  You should
   check your return codes to make sure you catch this error! */
void ignore_pipe(void)
{
  struct sigaction sig;

  sig.sa_handler = SIG_IGN;
  sig.sa_flags = 0;
  sigemptyset(&sig.sa_mask);
  sigaction(SIGPIPE,&sig,NULL);
}
