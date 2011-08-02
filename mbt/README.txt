You should place a working copy of the Mbt executable in this folder.
The included binary is for Mac OS X 10.5.
http://ilk.uvt.nl/mbt/

Current version: 3.1.3

BUILDING FROM SOURCE
====================

To build MBT from source, it is required that you first build TiMBL (see MBSP/Timbl/README).
Uncompress the MBT source code from mbt-3.1.3.tar.
>>> cd mbt-3.1.3
>>> ./configure --enable-shared=no --enable-static=no --prefix=[FOLDER]
>>> make install

- This will install MBT in the given folder. 
  Use the same [FOLDER] path as where you built TiMBL (MBT requires TiMBL as a dependency).
- The --enable-shared and --enable-static arguments ensure we get everything bundled 
  inside one nice executable which we can include with MBSP.
- The 'Mbt' executable file will be in the [FOLDER]/bin subfolder and should be around 900KB in size.
  Copy it to MBSP/Mbt folder.