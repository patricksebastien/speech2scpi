LIBSENT=./julius-4.3.1/libsent
LIBJULIUS=./julius-4.3.1/libjulius

CC=gcc
CFLAGS=-g -O2 

####
#### When using system-installed libraries
####
#CPPFLAGS=`libjulius-config --cflags` `libsent-config --cflags`
#LDFLAGS=`libjulius-config --libs` `libsent-config --libs`

####
#### When using within-package libraries
####
CPPFLAGS=-I$(LIBJULIUS)/include -I$(LIBSENT)/include  `$(LIBSENT)/libsent-config --cflags` `$(LIBJULIUS)/libjulius-config --cflags` `pkg-config --cflags liblo`
LDFLAGS= -L$(LIBJULIUS) `$(LIBJULIUS)/libjulius-config --libs` -L$(LIBSENT) `$(LIBSENT)/libsent-config --libs` `pkg-config --libs liblo`

############################################################

all: speechreco

speechreco:speechreco.c
	$(CC) $(CFLAGS) $(CPPFLAGS) -o speechreco speechreco.c $(LDFLAGS)

clean:
	$(RM) *.o *.bak *~ core TAGS

distclean:
	$(RM) *.o *.bak *~ core TAGS
	$(RM) speechreco
