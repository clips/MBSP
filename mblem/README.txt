To start MBLEM server:
nohup nice Timbl -mM -w2 -k5 -f $PATH/TO/em.data -S $PORT 2>>$ERRLOGFILE >$LOGFILE &

BUILDING FROM SOURCE
====================

- Delete all files with .o extension and the executable binary 'mblem_english_bmt'.
- From the command line, do 'make' in the /mblem folder.
