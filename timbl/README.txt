You should place a working copy of the TiMBL executable in this folder.
The included binary is for Mac OS X 10.5.
http://ilk.uvt.nl/timbl/

Current version: 6.1.5

BUILDING FROM SOURCE
====================

Uncompress the TiMBL source code from timbl-6.1.5.tar.
>>> cd timbl-6.1.5
>>> ./configure --enable-shared=no --enable-static=no --prefix=[FOLDER]
>>> make install

- This will install TiMBL in the given folder. 
- The --enable-shared and --enable-static arguments ensure we get everything bundled 
  inside one nice executable which we can include with MBSP.
- If you omit the --prefix argument, TiMBL will just install itself in /usr/local/.
  However, for MBSP we only need the executable so it's a good idea to pick another, temporary folder.
  The 'Timbl' executable file will be in the [FOLDER]/bin subfolder and should be around 900KB in size.
  Copy it to MBSP/Timbl folder.
- Don't throw away the installed build just yet if you also want to build MBT from source.
  MBT needs a TiMBL build, and we'll install it in the same folder.