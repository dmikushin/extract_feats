from __future__ import print_function
import subprocess
import shutil
import os
import stat
import time
import hashlib
import ntpath

# This script looks extremely defensive, but *should* let you rerun at
# any stage along the way. Also a lot of code repetition due to eventual support
# for "non-blob" install from something besides the magic kk_all_deps.tar.gz

# Contents of kk_all_deps.tar.gz
kk_all_deps = \
[ \
"http://www.cstr.ed.ac.uk/downloads/festival/2.4/festlex_CMU.tar.gz", \
"http://www.cstr.ed.ac.uk/downloads/festival/2.4/festival-2.4-release.tar.gz", \
"https://www.csie.ntu.edu.tw/~b97020/DSP/HTK-3.4.1.tar.gz", \
"http://www.cstr.ed.ac.uk/downloads/festival/2.4/festlex_POSLEX.tar.gz", \
"http://hts.sp.nitech.ac.jp/archives/2.3/HTS-2.3_for_HTK-3.4.1.tar.bz2", \
"https://datashare.is.ed.ac.uk/bitstream/handle/10283/2119/VCTK-Corpus.tar.gz", \
"http://download2.nust.na/pub4/sourceforge/h/ht/hts-engine/hts_engine%20API/hts_engine_API-1.10/hts_engine_API-1.10.tar.gz", \
"http://www.cstr.ed.ac.uk/downloads/festival/2.4/voices/festvox_cmu_us_slt_cg.tar.gz", \
"http://www.cstr.ed.ac.uk/downloads/festival/2.4/speech_tools-2.4-release.tar.gz", \
"http://festvox.org/festvox-2.7/festvox-2.7.0-release.tar.gz", \
"http://www.cstr.ed.ac.uk/downloads/festival/2.4/festlex_OALD.tar.gz", \
"http://download2.nust.na/pub4/sourceforge/s/project/sp/sp-tk/SPTK/SPTK-3.9/SPTK-3.9.tar.gz", \
"http://hts.sp.nitech.ac.jp/archives/2.2/HTS-demo_CMU-ARCTIC-SLT.tar.bz2", \
"http://104.131.174.95/slt_wav.zip", \
"http://104.131.174.95/slt_arctic_full_data.zip"
]

# We are about to install a lot of things
# 2 primary directories inside base_dir
# all_deps/* will have all zipped dirs
# vctk/VCTK-Corpus will have all the data
# speech_synthesis/* will have a bunch of compiled C++ codebases
# we also set the environment appropriately and write out some helper scripts
starting_dir = os.getcwd()

base_install_dir = starting_dir + "/"
base_vctk_dir = base_install_dir + "vctk/"

vctkdir = base_vctk_dir + "VCTK-Corpus/"
merlindir = base_install_dir + "latest_features/merlin/"
estdir = base_install_dir + "speech_tools/"
festdir = base_install_dir + "festival/"
festvoxdir = base_install_dir + "festvox/"
htkdir = base_install_dir + "htk/"
sptkdir = base_install_dir + "SPTK-3.9/"
htspatchdir = base_install_dir + "HTS-2.3_for_HTL-3.4.1/"
htsenginedir = base_install_dir + "hts_engine_API-1.10/"
htsdemodir = base_install_dir + "HTS-demo_CMU-ARCTIC-SLT/"

# http://www.nguyenquyhy.com/2014/07/create-full-context-labels-for-hts/

env = os.environ.copy()

env["ESTDIR"] = estdir
env["FESTVOXDIR"] = festvoxdir
env["FESTDIR"] = festdir
env["VCTKDIR"] = vctkdir
env["PATH"] = starting_dir + os.pathsep + env["PATH"]
#env["CFLAGS_EXT0"] = "-O0"
#env["CXXFLAGS_EXT0"] = "-O0"
env["CFLAGS_EXT0"] = "-O3"
env["CXXFLAGS_EXT0"] = "-O3"

def copytree(src, dst, symlinks = False, ignore = None):
  if not os.path.exists(dst):
    os.makedirs(dst)
    shutil.copystat(src, dst)
  lst = os.listdir(src)
  if ignore:
    excl = ignore(src, lst)
    lst = [x for x in lst if x not in excl]
  for item in lst:
    s = os.path.join(src, item)
    d = os.path.join(dst, item)
    if symlinks and os.path.islink(s):
      if os.path.lexists(d):
        os.remove(d)
      os.symlink(os.readlink(s), d)
      try:
        st = os.lstat(s)
        mode = stat.S_IMODE(st.st_mode)
        os.lchmod(d, mode)
      except:
        pass # lchmod not available
    elif os.path.isdir(s):
      copytree(s, d, symlinks, ignore)
    else:
      shutil.copy2(s, d)

# Convenience function to reuse the defined env
def pwrap(args, pwrap_env, shell=False):
    p = subprocess.Popen(args, shell=shell, stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE, stderr=subprocess.PIPE, env=pwrap_env,
                         universal_newlines=True)
    return p


# Don't use piped log printing here, as it tends to hang/deadlock
# (Ubuntu 18.04, dash terminal)
def pe(cmd, pwrap_env=env, shell=False):
    print("cd %s && %s" % (os.getcwd(), " ".join(cmd)))
    popen = pwrap(cmd, pwrap_env=pwrap_env, shell=shell)

    output = popen.communicate()[0]
    exitCode = popen.returncode

    if (exitCode == 0):
        return output
    else:
        print("%s" % output)
        raise subprocess.CalledProcessError(exitCode, cmd)


def sha256_checksum(filename, block_size=65536):
    sha256 = hashlib.sha256()
    with open(filename, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()
    
# Downloads parts of sources bundle
dep_dir = "all_deps/"
print("Downloading dependencies ...")
if not os.path.exists(base_install_dir + dep_dir):
    os.mkdir(base_install_dir + dep_dir)
os.chdir(base_install_dir + dep_dir)
for dep in kk_all_deps:
    download = True
    if os.path.exists(ntpath.basename(dep)):
        if os.path.exists(ntpath.basename(dep) + ".sha256sum"):
            checksum_file = open(ntpath.basename(dep) + ".sha256sum", "r")
            checksum, filename = checksum_file.readline().split()
            if (checksum == sha256_checksum(ntpath.basename(dep))):
                download = False
                print("Skipping already downloaded file %s" % ntpath.basename(dep))
            else:
                print("Wrong sha256sum for file %s - remove and redownload!" % ntpath.basename(dep))
                os.remove(ntpath.basename(dep))
    
    if not download:
        continue

    wget_cmd = ["wget", "--quiet", dep]
    print("Downloading %s ..." % dep)
    pe(wget_cmd)

    checksum = sha256_checksum(ntpath.basename(dep))
    checksum_file = open(ntpath.basename(dep) + ".sha256sum", "w")
    checksum_file.write("%s\t%s" % (checksum, ntpath.basename(dep)))
    checksum_file.close()

print("Download complete!")

# Start unpacking things
full_dep_dir = base_install_dir + dep_dir

# Unpack vctk
# Install dir for vctk
os.chdir(base_install_dir)
if not os.path.exists(base_vctk_dir):
    os.mkdir(base_vctk_dir)

# symlink
os.chdir(base_vctk_dir)
vctk_pkg = "VCTK-Corpus.tar.gz"
vctk_pkg_path = base_vctk_dir + vctk_pkg
if not os.path.exists(vctk_pkg_path):
    os.symlink(base_install_dir + dep_dir + vctk_pkg, vctk_pkg_path)

if not os.path.exists(vctkdir):
    print("Unpacking vctk...")
    untar_cmd = ["tar", "xzf", vctk_pkg_path]
    pe(untar_cmd)

os.chdir(base_install_dir)
speech_tools_pkg = "speech_tools-2.4-release.tar.gz"
speech_tools_pkg_path = base_install_dir + speech_tools_pkg
if not os.path.exists(speech_tools_pkg_path):
    os.symlink(full_dep_dir + speech_tools_pkg, speech_tools_pkg_path)

os.chdir(base_install_dir)
if not os.path.exists(estdir):
    print("Unpacking speech_tools...")
    untar_cmd = ["tar", "xzf", speech_tools_pkg_path]
    pe(untar_cmd)

# rough check if speech_tools is built or not, if not build it
if not os.path.exists(estdir + "bin/siod"):
    # apparently we expect exist status 2???
    os.chdir(estdir)
    configure_cmd = ["./configure"]
    pe(configure_cmd)
    make_cmd = ["make", "-j", "4"]
    env_est = env
    # Special g++ flags to workaround segmentation fault
    # as described here: https://aur.archlinux.org/packages/festival-patched-hts/
    env_est["CFLAGS_EXT0"] = "-O0"
    env_est["CFLAGS_EXT1"] = "-fno-delete-null-pointer-checks"
    env_est["CFLAGS_EXT2"] = "-std=gnu++98"
    env_est["CXXFLAGS_EXT0"] = "-O0"
    env_est["CXXFLAGS_EXT1"] = "-fno-delete-null-pointer-checks"
    env_est["CXXFLAGS_EXT2"] = "-std=gnu++98"
    make_cmd = ["make", "-j", "4"]
    pe(make_cmd, env_est)

# Install festival
os.chdir(base_install_dir)
festival_pkg = "festival-2.4-release.tar.gz"
festival_pkg_path = base_install_dir + festival_pkg
if not os.path.exists(festival_pkg_path):
    os.symlink(full_dep_dir + festival_pkg, festival_pkg_path)

if not os.path.exists(festdir):
    untar_cmd = ["tar", "xzf", festival_pkg_path]
    pe(untar_cmd)

if not os.path.exists(festdir + "bin/festival"):
    os.chdir(festdir)
    configure_cmd = ["./configure"]
    pe(configure_cmd)
    make_cmd = ["make"]
    env_festival = env
    # Special g++ flags to workaround segmentation fault
    # as described here: https://aur.archlinux.org/packages/festival-patched-hts/
    env_festival["CFLAGS_EXT0"] = "-O0"
    env_festival["CFLAGS_EXT1"] = "-fno-delete-null-pointer-checks"
    env_festival["CFLAGS_EXT2"] = "-std=gnu++98"
    env_festival["CXXFLAGS_EXT0"] = "-O0"
    env_festival["CXXFLAGS_EXT1"] = "-fno-delete-null-pointer-checks"
    env_festival["CXXFLAGS_EXT2"] = "-std=gnu++98"
    pe(make_cmd, env_festival)

# Install festival addons
# festlex_CMU
# festlex_OALD
# festlex_POSLEX
# festvox_cmu_us_slt_cg.tar.gz
cmu_lex_pkg = "festlex_CMU.tar.gz"
cmu_lex_pkg_path = base_install_dir + cmu_lex_pkg
if not os.path.exists(cmu_lex_pkg_path):
    os.symlink(full_dep_dir + cmu_lex_pkg, cmu_lex_pkg_path)

oald_pkg = "festlex_OALD.tar.gz"
oald_pkg_path = base_install_dir + oald_pkg
if not os.path.exists(oald_pkg_path):
    os.symlink(full_dep_dir + oald_pkg, oald_pkg_path)

poslex_pkg = "festlex_POSLEX.tar.gz"
poslex_pkg_path = base_install_dir + poslex_pkg
if not os.path.exists(poslex_pkg_path):
    os.symlink(full_dep_dir + poslex_pkg, poslex_pkg_path)

slt_cg_pkg = "festvox_cmu_us_slt_cg.tar.gz"
slt_cg_pkg_path = base_install_dir + slt_cg_pkg
if not os.path.exists(slt_cg_pkg_path):
    os.symlink(full_dep_dir + slt_cg_pkg, slt_cg_pkg_path)

os.chdir(base_install_dir)
if not os.path.exists(festdir + "lib/voices"):
    # if no voice dir install all the lex stuff...
    untar_cmd = ["tar", "xzf", slt_cg_pkg_path]
    pe(untar_cmd)
    untar_cmd = ["tar", "xzf", poslex_pkg_path]
    pe(untar_cmd)
    untar_cmd = ["tar", "xzf", oald_pkg_path]
    pe(untar_cmd)
    untar_cmd = ["tar", "xzf", cmu_lex_pkg_path]
    pe(untar_cmd)

# Install festvox
os.chdir(base_install_dir)
festvox_pkg = "festvox-2.7.0-release.tar.gz"
festvox_pkg_path = base_install_dir + festvox_pkg
if not os.path.exists(festvox_pkg_path):
    os.symlink(full_dep_dir + festvox_pkg, festvox_pkg_path)

if not os.path.exists(festvoxdir):
    untar_cmd = ["tar", "xzf", festvox_pkg_path]
    pe(untar_cmd)

# build it
if not os.path.exists(festvoxdir + "src/ehmm/bin/ehmm"):
    os.chdir(festvoxdir)
    configure_cmd = ["./configure"]
    pe(configure_cmd)
    make_cmd = ["make"]
    pe(make_cmd)

# Install htk
# patch for HTS
os.chdir(base_install_dir)
htk_pkg = "HTK-3.4.1.tar.gz"
htk_pkg_path = base_install_dir + htk_pkg
if not os.path.exists(htk_pkg_path):
    os.symlink(full_dep_dir + htk_pkg, htk_pkg_path)

if not os.path.exists(htkdir):
    untar_cmd = ["tar", "xzf", htk_pkg_path]
    pe(untar_cmd)

if not os.path.exists(htkdir + "HTKTools/HSGen"):
    # HTS patchfile
    os.chdir(base_install_dir)
    hts_patch_pkg = "HTS-2.3_for_HTK-3.4.1.tar.bz2"
    patch_dir = "hts_patch/"
    hts_patch_dir = base_install_dir + patch_dir
    hts_patch_path = hts_patch_dir + hts_patch_pkg
    if not os.path.exists(hts_patch_pkg):
        if not os.path.exists(hts_patch_dir):
            os.mkdir(hts_patch_dir)
        if not os.path.exists(hts_patch_path):
            os.symlink(full_dep_dir + hts_patch_pkg, hts_patch_path)

    full_patch_path = hts_patch_dir + "HTS-2.3_for_HTK-3.4.1.patch"
    os.chdir(hts_patch_dir)
    untar_cmd = ["tar", "xjf", hts_patch_path]
    pe(untar_cmd)
    os.chdir(htkdir)
    try:
        pe("patch -p1 -d . -f < %s" % full_patch_path, shell=True)
    except subprocess.CalledProcessError:
        # we expect the patch to partially fail :/
        pass

    os.chdir(htkdir)
    pe(["./configure", "--disable-hlmtools", "--disable-hslab"])
    pe(["make"])

os.chdir(base_install_dir)
sptk_pkg = "SPTK-3.9.tar.gz"
sptk_subdir = base_install_dir + "sptk/"
sptk_pkg_path = sptk_subdir + sptk_pkg
if not os.path.exists(sptk_subdir):
    os.mkdir(sptk_subdir)

if not os.path.exists(sptk_pkg_path):
    os.symlink(full_dep_dir + sptk_pkg, sptk_pkg_path)

# Install sptk
if not os.path.exists(sptkdir):
    os.chdir(sptk_subdir)
    untar_cmd = ["tar", "xzf", "SPTK-3.9.tar.gz"]
    pe(untar_cmd)
    os.chdir("SPTK-3.9")
    os.mkdir("out")
    pe(["./configure", "--prefix=%s" % sptk_subdir + "SPTK-3.9/out"])
    pe(["make"])
    os.chdir(sptk_subdir + "SPTK-3.9")
    pe(["make install"], shell=True)
    os.chdir(base_install_dir)
    os.mkdir("SPTK-3.9")
    copytree("sptk/SPTK-3.9/out", "SPTK-3.9")

os.chdir(base_install_dir)
hts_engine_pkg = "hts_engine_API-1.10.tar.gz"
hts_engine_pkg_path = base_install_dir + hts_engine_pkg
if not os.path.exists(hts_engine_pkg_path):
    os.symlink(full_dep_dir + hts_engine_pkg, hts_engine_pkg_path)

if not os.path.exists(htsenginedir):
    untar_cmd = ["tar", "xzf", hts_engine_pkg_path]
    pe(untar_cmd)

# Install hts engine
os.chdir(htsenginedir)
if not os.path.exists(htsenginedir + "bin/hts_engine"):
    configure_cmd = ["./configure"]
    pe(configure_cmd)
    make_cmd = ["make"]
    pe(make_cmd)

os.chdir(base_install_dir)
hts_demo_pkg = "HTS-demo_CMU-ARCTIC-SLT.tar.bz2"
hts_demo_pkg_path = base_install_dir + hts_demo_pkg
if not os.path.exists(hts_demo_pkg_path):
    os.symlink(full_dep_dir + hts_demo_pkg, hts_demo_pkg_path)

# Unpack HTS demo
if not os.path.exists(htsdemodir):
    untar_cmd = ["tar", "xjf", hts_demo_pkg_path]
    pe(untar_cmd)

if not os.path.exists(htsdemodir + "data/lf0/cmu_us_arctic_slt_a0001.lf0"):
    os.chdir(htsdemodir)
    configure_cmd = ["./configure"]
    configure_cmd += ["--with-fest-search-path=%s" % (festdir + "examples")]
    configure_cmd += ["--with-sptk-search-path=%s" % (sptkdir + "bin")]
    configure_cmd += ["--with-hts-search-path=%s" % (htkdir + "HTKTools")]
    configure_cmd += ["--with-hts-engine-search-path=%s" % (htsenginedir + "bin")]
    pe(configure_cmd)

print("Typing 'make' in %s will run a speech sythesis demo, but it takes a long time" % htsdemodir)
print("Also dumping a helper source script to %stts_env.sh" % base_install_dir)
# http://www.nguyenquyhy.com/2014/07/create-full-context-labels-for-hts/
lns = ["export ESTDIR=%s\n" % estdir]
lns.append("export FESTDIR=%s\n" % festdir)
lns.append("export FESTVOXDIR=%s\n" % festvoxdir)
lns.append("export VCTKDIR=%s\n" % vctkdir)
lns.append("export HTKDIR=%s\n" % htkdir)
lns.append("export SPTKDIR=%s\n" % sptkdir)
lns.append("export HTSENGINEDIR=%s\n" % htsenginedir)
lns.append("export HTSDEMODIR=%s\n" % htsdemodir)
lns.append("export HTSPATCHDIR=%s\n" % htspatchdir)
lns.append("export MERLINDIR=%s\n" % merlindir)

os.chdir(base_install_dir)
with open("tts_env.sh", "w") as f:
    f.writelines(lns)
