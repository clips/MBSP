/* mblem_english_bmt - lemmatize a two-column <word> <tag> file with MBLEM, 
   a memory-based lemmatizer trained on CELEX English morphology

   June 2002, ILK / Tilburg University / Antal van den Bosch

   code assumes TiMBL-MBLEM server running (on <machine>:<port>)
   server startup example: Timbl -mM -w2 -k5 -f em.data -S <port>
  
   syntax: 

   mblem_english_bmt <word-tagfile> <machine> <port> <lexfile> <transtable>

*/

#include<stdio.h>
#include<string.h>
#include<stddef.h>
#include<stdlib.h>
#if !defined(__APPLE__)
#include <malloc.h>
#endif
#include "sockhelp.h"
#include<unistd.h>
#include<time.h>

#define MAXREADLINE 1024
#define WORDLEN     1024
#define CODELEN       16
#define HISTORY       20
#define DEBUG          0
#define CLASSES       90
#define MAXLOOKUP     64
#define LOOKUPLEN   1024
#define BUFSIZE     1024

int main(int argc, char *argv[]) {
    
    FILE *bron,*doel;
    char **lexwf;
    char **lexlem;
    char **lexpos;
    char *part;
    char MACHINE[1024];
    char PORT[1024];
    char LEXFILE[1024];
    char TRFILE[1024];
    char buffer[BUFSIZE];
    char instance[BUFSIZE];
    char wsjclasses[CLASSES][WORDLEN];
    char bncclasses[CLASSES][WORDLEN];
    char classcodes[CLASSES][CODELEN];
    char lookuplemma[MAXLOOKUP][LOOKUPLEN];
    char lookuptag[MAXLOOKUP][LOOKUPLEN];
    char onlytag[MAXLOOKUP][LOOKUPLEN];
    char celex_suffix[MAXLOOKUP][LOOKUPLEN];
    char line[MAXREADLINE];
    char readword[MAXREADLINE];
    char readlemma[MAXREADLINE];
    char readtag[MAXREADLINE];
    char fname[MAXREADLINE];
    char word[MAXREADLINE];
    char memword[MAXREADLINE];
    char lemma[MAXREADLINE];
    char tag[MAXREADLINE];
    char delete[MAXREADLINE];
    char insert[MAXREADLINE];
    char change[MAXREADLINE];
    char more,in,let;
    int  i,j,k=0,l,m,nrlookup,lookup,total=0,nrlex,sock=0,connected=1,sentence=0;
    time_t begintime,beginlemmatime,endtime,midtime;
    void timer(void);
 
    time(&begintime);

    fprintf(stderr,"\n-------------------------------------------------------\n");
    fprintf(stderr,"MBLEM-english - ILK / Tilburg University, June 2002\n");
    fprintf(stderr,"memory-based lemmatization, trained on CELEX\n");
    fprintf(stderr,"Antal van den Bosch / antalb@kub.nl\n");
    fprintf(stderr,"Customization of command line options for Jo Meyhi, April 2005\n");
    fprintf(stderr,"Fixed non-ascii support, January 2008\n");
    fprintf(stderr,"Verb tense disambiguation, April 2010\n");
    timer();

    if (argc!=6) {
        fprintf(stderr,"bad number of arguments. syntax:\nmblem_english_bmt <word-tagfile> <machine> <port> <lexfile> <transtable>\n\n");
        exit(1);
    }

    strcpy(MACHINE,argv[2]);
    strcpy(PORT,argv[3]);
    strcpy(LEXFILE,argv[4]);
    strcpy(TRFILE,argv[5]);
    
    /* initialize stuff */
    bron=fopen(LEXFILE,"r");
    if (bron==NULL) {
        fprintf(stderr,"lexicon file %s appears to be missing.\n\n",LEXFILE);
        exit(1);
    }
    if (DEBUG) fprintf(stderr,"initialising lexicon\n");
    nrlex=0;
    while (!feof(bron)) {
        fgets(line,MAXREADLINE,bron);
        if ((!feof(bron))&&(strlen(line)>1)) nrlex++;
    }
    fclose(bron);
    if (DEBUG) fprintf(stderr,"%d items in lexicon\n",nrlex);
    lexwf=malloc(nrlex*sizeof(char*));
    if (lexwf==NULL) {
        fprintf(stderr,"not enough memory.\n");
        exit(1);
    }
    lexlem=malloc(nrlex*sizeof(char*));
    if (lexlem==NULL) {
        fprintf(stderr,"not enough memory.\n");
        exit(1);
    }
    lexpos=malloc(nrlex*sizeof(char*));
    if (lexpos==NULL) {
        fprintf(stderr,"not enough memory.\n");
        exit(1);
    }
    if (DEBUG) fprintf(stderr,"reading %d items from lexicon\n",nrlex);
    bron=fopen(LEXFILE,"r");
    for (i=0; i<nrlex; i++) {
        if ((DEBUG)&&(i%10000==0)) fprintf(stderr,"%9d items read\n",i);
        fscanf(bron,"%s %s %s ",readword,readlemma,readtag);
        lexwf[i]=malloc((strlen(readword)+1)*sizeof(char));
        if (lexwf[i]==NULL) {
            fprintf(stderr,"not enough memory.\n");
            exit(1);
        }
        strcpy(lexwf[i],readword);
        lexlem[i]=malloc((strlen(readlemma)+1)*sizeof(char));
        if (lexlem[i]==NULL) {
            fprintf(stderr,"not enough memory.\n");
            exit(1);
        }
        strcpy(lexlem[i],readlemma);
        lexpos[i]=malloc((strlen(readtag)+1)*sizeof(char));
        if (lexpos[i]==NULL) {
            fprintf(stderr,"not enough memory.\n");
            exit(1);
        }
        strcpy(lexpos[i],readtag);
    }
    fclose(bron);

    bron=fopen(TRFILE,"r");
    if (bron==NULL) {
        fprintf(stderr,"translation table file %s appears to be missing.\n\n",TRFILE);
        exit(1);
    }
    for (i=0; i<CLASSES; i++) {
        fscanf(bron,"%s %s %s ",wsjclasses[i],classcodes[i],bncclasses[i]);
    }
    fclose(bron);

    /* open two-column file */
    if (argc == 1 || strcmp(argv[1],"-")==0) { 
        bron=stdin; 
    } else {
        bron=fopen(argv[1],"r");
        if (bron==NULL) {
            fprintf(stderr,"%s: no such file.\n\n",argv[1]);
            exit(1);
        }
        fprintf(stderr,"TiMBL-MBLEMing %s\n",argv[1]);
    }

    /* start up communications with the MBMA server */
    ignore_pipe();
    sock=make_connection(PORT,SOCK_STREAM,MACHINE);
    if (sock==-1) { 
        fprintf(stderr,"The MBLEM server is not responding; aborting.\n\n");
        connected=0;
        exit(1);
    }

    /* when connected, cut off the TiMBL server welcome message */
    if (connected) sock_gets(sock,buffer,sizeof(buffer)-1); 

    /* initialise and open two-column file */
    if (argc == 1 || strcmp(argv[1],"-")==0) { 
        doel=stdout; 
    } else {
        strcpy(fname,argv[1]);
        strcat(fname,".tl");
        doel=fopen(fname,"w");
    }
    setbuf(doel,NULL);

    lookup=total=0;
    let=0;
    time(&beginlemmatime);

    /* read all of the words, convert them to instances, classify them, 
       lemmatize them. The works.
    */ 
    while (!feof(bron)) {
        fscanf(bron,"%s ",word);
        strcpy(memword,word);

        /* cut off all words and ignore markers */
        if (word[0]!='<') {
	        fscanf(bron,"%s ",tag);

            if ((sentence==0)&&
               ((strcmp(word,"?")==0)||
                (strcmp(word,".")==0)||
                (strcmp(word,":")==0)||
                (strcmp(word,",")==0)||
                (strcmp(word,"(")==0)||
                (strcmp(word,")")==0)||
                (strcmp(word,"``")==0)||
                (strcmp(word,"\'\'")==0)||
                (strcmp(word,"BREAK")==0)||
                (strcmp(word,"!")==0))) let=1;

            if (((sentence==0)||
                ((sentence==1)&&(let)))&&
                 (word[0]>='A')&&
                 (word[0]<='Z')&&
                 (!strstr(tag,"NNP"))&&
                 (!strstr(word,"BREAK"))) {
                     let=0;
                     word[0]+=32;
                     for (i=1; i<strlen(word); i++) {
                         if ((word[i]>='A')&&(word[i]<='Z')) word[i]+=32; 
                     }
            }

            if (DEBUG) fprintf(stderr,"\nWORD: %s (# %d in sentence)\n",word,sentence);
            total++;
            if (total%1000==0) {
                time(&midtime);
                fprintf(stderr," %6d sec, %9d words lemmatized (%.0f w/s)\n",
                (int) midtime - (int) begintime,total,(1.*total)/(1.*((int) midtime - (int) begintime)));
            }

            /* generate instance */
            strcpy(instance,"c ");
            for (i=0; i<HISTORY; i++) {
                j=((strlen(word)-HISTORY)+i);
                if (j<0) {
                    strcat(instance,"= ");
                } else {
                    strcat(instance," ");
                    instance[strlen(instance)-1]=word[(strlen(word)-HISTORY)+i];
                    strcat(instance," ");
                }
            }
            strcat(instance," ?\n");

            if (DEBUG) fprintf(stderr," instance: %s",instance);

            /* throw the instance at the socket */
            sock_puts(sock,instance);

            /* get the TiMBL server output back */
            if (sock_gets(sock,buffer,sizeof(buffer)) == -1) connected=0;
            if (strlen(buffer)<2) {
                if (sock_gets(sock,buffer,sizeof(buffer)) == -1) connected=0; 
            }
            if (!connected) { 
                fprintf(stderr,"The MBLEM server is not responding; aborting.\n\n");
                connected=0;
                exit(1);
            }

            if (DEBUG) fprintf(stderr," TiMBL reply: %s\n",buffer);
            strcpy(change,"");
            j=0;
            while (buffer[j]!='{') j++;
            j++;
            while (buffer[j]!='}') {
                strcat(change," ");
                change[strlen(change)-1]=buffer[j];
                j++;
            }
            if (DEBUG) printf("change [%s]<p>\n",change);
            nrlookup=0;

            /* are we dealing with simple punctuation? */
            if ((strcmp(word,"?")==0)||
                (strcmp(word,".")==0)||
                (strcmp(word,":")==0)||
                (strcmp(word,",")==0)||
                (strcmp(word,"(")==0)||
                (strcmp(word,")")==0)||
                (strcmp(word,"``")==0)||
                (strcmp(word,"\'\'")==0)||
                (strcmp(word,"BREAK")==0)||
                (strcmp(word,"!")==0)) {
                    strcpy(lookuplemma[0],word);
                    strcpy(lookuptag[0],"PUN");
                    nrlookup=1;
                    lookup++;
            }

            /* look up in the lexicon */
            if (nrlookup==0) {
                i=0;
                while ((i<nrlex)&&(word[0]!=lexwf[i][0])) i++;
                while ((i<nrlex)&&(word[0]==lexwf[i][0])) {
                    if (word[1]==lexwf[i][1])
                    if (strcmp(word,lexwf[i])==0) {
                        strcpy(lookuplemma[nrlookup],lexlem[i]);
                        strcpy(lookuptag[nrlookup],lexpos[i]);
                        if (DEBUG) fprintf(stderr,"lookup %d: %s %s %s\n",nrlookup,word,lexpos[i],lexlem[i]);
                        strcpy(onlytag[nrlookup],"");
                        l=0;
                        /* onlytag variable contains: V-e1S => V */
                        while (lexpos[i][l]!='-') {
                            strcat(onlytag[nrlookup]," ");
                            onlytag[nrlookup][l]=lexpos[i][l];
                            l++;
                        }
                        /* celex_suffix variable contains: V-e1S => e1S */
                        strcpy(celex_suffix[nrlookup],"");
                        m = l+1;
                        while (m < strlen(lexpos[i])) {
                            strcat(celex_suffix[nrlookup]," ");
                            celex_suffix[nrlookup][m-l-1]=lexpos[i][m];
                            m++;
                        }
                        nrlookup++;
                    }
                    i++;
                }
                if (nrlookup>0) lookup++;
            }

            /* not in lexicon? then turn to TiMBL */
            if (nrlookup==0) {
                if (DEBUG) fprintf(stderr,"asking TiMBL\n");
                more=0;
                if (strstr(change,"|")) more=1;
                /* go through all options separately */
                part=strtok(change,"|");
                while (part!=NULL) {
                    strcpy(readtag,"");
                    strcpy(delete,"");
                    strcpy(insert,"");

                    i=0;
                    while ((i<strlen(part))&&(part[i]!='+')) {
                        strcat(readtag," ");
                        readtag[i]=part[i];
                        i++;
                    }
                    while (i<strlen(part)) {
                        i++;
                        if (part[i]=='D') {
                            i++;
                            while ((i<strlen(part))&&(part[i]!='+')) {
                                strcat(delete," ");
                                delete[strlen(delete)-1]=part[i];
                                i++;
                            }
                        }
                        if (part[i]=='I') {
                            i++;
                            while ((i<strlen(part))&&(part[i]!='+')) {
                                strcat(insert," ");
                                insert[strlen(insert)-1]=part[i];
                                i++;
                            }
                        }
                    }
                    
                    /* Delete only the characters of delete that are really in word.
                    This check is necessary because otherwise bytes are lost when using
                    non-ascii encodings. */
                    
                    /*Find the place to stop*/
                    i=strlen(word)-1;
                    j=strlen(delete)-1;
                    l=strlen(word);

                    while (i >= 0 && j >= 0) {
                        if (word[i] == delete[j]) {
                            l--;
                            i--;
                            j--;
                        } else {
                            i=-1;
                        }
                    }

                    /*Make the lemma */
                    strcpy(lemma,"");
                    i=0;
                    while ( i<l ) {
                        strcat(lemma," ");
                        lemma[strlen(lemma)-1]=word[i];
                        i++;
                    }

                    strcat(lemma,insert);
                    strcpy(lookuptag[nrlookup],readtag);
                    strcpy(onlytag[nrlookup],"");
                    l=0;
                    while (readtag[l]!='-') {
                        strcat(onlytag[nrlookup]," ");
                        onlytag[nrlookup][l]=readtag[l];
                        l++;
                    }
                    strcpy(lookuplemma[nrlookup],lemma);
                    if (DEBUG) {
                        fprintf(stderr,"found TiMBL: %s %s\n",lemma,readtag);
                    }
                    nrlookup++;
                    part=strtok(NULL,"|");
                }
            }

            /* so now mix the original line with the candidates */
            
            /* first print the originally read word */
            fprintf(doel,"%s\t",memword);
            if (DEBUG) fprintf(stderr,">> %s\n",word);
            if (DEBUG) {
                fprintf(stderr," tag in input file: %s\n",tag);
                fprintf(stderr," according to MBLEM: ");
                for (l=0; l<nrlookup; l++) {
                    fprintf(stderr,"%s/%s ",lookuplemma[l],onlytag[l]);
                }
                fprintf(stderr,"\n");
            }

            in=0;
            l=0;
            m=-1;
            while ((!in)&&(l<nrlookup)) {
                k=0;
                while ((k<CLASSES)&&(!in)) {
                    if ((strcmp(onlytag[l],classcodes[k])==0) && (strcmp(tag,wsjclasses[k])==0)) {
                        /* We've found a match based on the part-of-speech.
                           However, Penn Treebank "VBD" would match CELEX "V-e1S" since they both start with 'V',
                           but VBD means a verb in the past tense, while "V-e1S" means 1st person singular present.
                           Store this candidate, but continue to look for a "V-a*" which is a better match.
                           This allows us to correctly lemmatize saw/VBD => to see instead of saw/VBD => to saw.
                        */
                        if (m<0) m=l; 
                        in=1;
                    }
                    if (in && strcmp(tag,"VBD")==0 && strncmp(celex_suffix[l],"a",  1)!=0) in=0;
                    if (in && strcmp(tag,"VBG")==0 && strncmp(celex_suffix[l],"pe", 2)!=0) in=0;
                    if (in && strcmp(tag,"VBN")==0 && strncmp(celex_suffix[l],"pa", 2)!=0) in=0;
                    if (in && strcmp(tag,"VBZ")==0 && strncmp(celex_suffix[l],"e3S",3)!=0) in=0;
                    if (in && strcmp(tag,"VBP")==0 && strncmp(celex_suffix[l],"e1S",3)!=0 
                                                   && strncmp(celex_suffix[l],"e2S",3)!=0 
                                                   && strncmp(celex_suffix[l],"eP", 2)!=0) in=0;
                    k++;
                }
                if (!in) l++;
            }
            if (!in && m>=0) {
                l=m; in=1; /* No exact match, but we found a reasonable candidate (see above VBD <=> V-e1S) */
            }
            if (DEBUG) fprintf(stderr,"%d nrlookup, now pointing at %d (%s)\n",nrlookup,l,lookuplemma[l]);
            if (in) {
                fprintf(doel,"%s\t%s\n",tag,lookuplemma[l]);
                if (DEBUG) fprintf(stderr,">> %s\t%s [SUCCESS]\n",tag,lookuplemma[l]);
            } else {
                fprintf(doel,"%s\t%s\n",tag,word);
                if (DEBUG) fprintf(stderr,">> %s %s [FAILURE]\n",tag,word);	  
            }
            sentence++;
        } else { 
            /* copy the <au> etc markers blindly */
            fprintf(doel,"%s\n",word);
            if (DEBUG) fprintf(stderr,">> %s\n",word);
            sentence=0;
        }
    }
    
    fclose(bron);
    close(sock);
    fclose(doel);

    time(&endtime);

    fprintf(stderr,"\r%d words processed\n",total);
    if (argc > 1) { fprintf(stderr,"wrote file %s\n",fname); }
    fprintf(stderr,"%d seconds spent in total; %d on preprocessing, %d on lemmatizing\n",
        (int) endtime - (int) begintime,
        (int) beginlemmatime - (int) begintime,
        (int) endtime - (int) beginlemmatime);
    fprintf(stderr,"ready.\n\n");
    return 0;
}

/* timer - understandable time
*/
void timer(void) { 
    struct tm *curtime;
    time_t bintime;
    time(&bintime);
    curtime = localtime(&bintime);
    fprintf(stderr,"current time: %s\n", asctime(curtime));
}
