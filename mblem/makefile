# Uncomment the following line for Solaris
# C_LINK = -lnsl

# Uncomment this for SCO.  (Note, this has only been reported to work with
# Revision 3.2.4 with the "SCO TCP/IP Development System" package installed.
# Please let me know if you have any other SCO success stories.
# C_LINK = -lsocket

# Comment the following line if you are not using the gnu c compiler
C_ARGS = -O2 -Wall

# You might have to change this if your c compiler is not cc
CC = gcc

# You shouldn't need to make any more changes below this line.

all:	mblem_english_bmt

sockhelp.o:	sockhelp.c
	$(CC) $(C_ARGS) $(C_LINK) -c sockhelp.c

mblem_english_bmt.o:	mblem_english_bmt.c  
	$(CC) $(C_ARGS) -c $<

mblem_english_bmt:	mblem_english_bmt.o sockhelp.o
	$(CC) -o $@ $^ $(C_LINK)

clean:
	rm -rf *.o mblem_english_bmt
