#### MEMORY-BASED SHALLOW PARSER ######################################################################

# Copyright (c) 2003-2010 University of Antwerp, Belgium and Tilburg University, The Netherlands
# Vincent Van Asch <vincent.vanasch@ua.ac.be>, Tom De Smedt <tom@organisms.be>
# License: GNU General Public License, see LICENSE.txt

### SETUP ############################################################################################
# On Unix systems, attempts to build MBLEM, TiMBL and MBT executables from source,
# following the steps described in README.txt.

import os, sys, glob, shutil, urllib, tarfile
import config

MBLEM  = config.paths['mblem']
TIMBL  = config.paths['timbl']
MBT    = config.paths['mbt']
BUILD  = os.path.join(config.MODULE, 'build')

downloads = {
    TIMBL: 'http://ilk.uvt.nl/downloads/pub/software/timbl-6.1.5.tar.gz',
      MBT: 'http://ilk.uvt.nl/downloads/pub/software/mbt-3.1.3.tar.gz'
}

path, folder, filename, files, copy, shell = (
    os.path.join, os.path.dirname, os.path.basename, glob.glob, shutil.copyfile, os.system)

def delete(path):
    """ Removes the given path (either a file, folder, or search path).
    """
    for f in glob.glob(path):
        if os.path.isdir(f): shutil.rmtree(f); return
        os.remove(f)

def download(url, path):
    """ Places the downloaded file at the given path.
    """
    path = os.path.join(path, os.path.basename(url))
    path = path.endswith('.tar.gz') and path.rstrip('.gz') or path
    path = urllib.urlretrieve(url, path)[0]
    return path
    
def extract(archive, path):
    """ Extracts all files in the archive (.tar) into the given path.
    """
    tarfile.open(archive).extractall(path)

#--- BUILD MBLEM -------------------------------------------------------------------------------------

# Remove existing MBLEM executable and any dependencies (.o files).
# Build new MBLEM executable.
delete(MBLEM)
delete(path(folder(MBLEM), '*.o'))
shell('cd %s; make' % folder(MBLEM))
config._executable(MBLEM)

#--- BUILD TIMBL & MBT -------------------------------------------------------------------------------

# Remove any previous (i.e. unfinished) build and create the build folder.
# TiMBL and MBT are unpacked and compiled in this folder.
delete(BUILD)
os.mkdir(BUILD)

for name, executable, url in (('Timbl', TIMBL, downloads[TIMBL]), ('Mbt', MBT, downloads[MBT])):
    delete(executable)
    # Unzip the bundled archive to the BUILD folder.
    # If multiple archives are present, pick the last one (assumed to have the higher version number).
    # If no archive is bundled, download a known stable version.
    try:
        archive = files(path(folder(executable), '*.tar'))[-1]
    except:
        archive = download(url, BUILD)
    extract(archive, BUILD)
    # Configure and build new executable.
    shell('cd '+path(BUILD, filename(archive)[:-4])+';' + \
          './configure --enable-shared=no --enable-static=no --prefix='+BUILD+';' + \
          'make install')
    copy(path(BUILD, 'bin', name), executable)
    config._executable(executable)
    
# Remove the build folder.
delete(BUILD)

#--- INSTALL -----------------------------------------------------------------------------------------

if "install" in sys.argv:
    # Move the MBSP folder to Python's standard module location.
    from distutils.sysconfig import get_python_lib
    shutil.copytree(config.MODULE, path(get_python_lib(), "MBSP"))