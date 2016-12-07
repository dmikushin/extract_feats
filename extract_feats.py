from __future__ import print_function
import os
import shutil
import stat
import subprocess

# File to extract features (mostly) automatically using the merlin speech
# pipeline

def copytree(src, dst, symlinks=False, ignore=None):
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
                pass  # lchmod not available
        elif os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

# Convenience function to reuse the defined env
def pwrap(args, shell=False):
    p = subprocess.Popen(args, shell=shell, stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                         universal_newlines=True)
    return p

# Print output
# http://stackoverflow.com/questions/4417546/constantly-print-subprocess-output-while-process-is-running
def execute(cmd, shell=False):
    popen = pwrap(cmd, shell=shell)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line

    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


def pe(cmd, shell=False):
    """
    Print and execute command on system
    """
    for line in execute(cmd, shell=shell):
        print(line, end="")

# Source the tts_env_script
env_script = "tts_env.sh"
if os.path.isfile(env_script):
    command = 'env -i bash -c "source %s && env"' % env_script
    for line in execute(command, shell=True):
        key, value = line.split("=")
        # remove newline
        value = value.strip()
        os.environ[key] = value
else:
    raise IOError("Cannot find file %s" % env_script)

festdir = os.environ["FESTDIR"]
festvoxdir = os.environ["FESTVOXDIR"]
estdir = os.environ["ESTDIR"]
# generalize to more than VCTK when this is done...
vctkdir = os.environ["VCTKDIR"]
htkdir = os.environ["HTKDIR"]

def extract_intermediate_features():
    basedir = os.getcwd()
    latest_feature_dir = "latest_features"
    if not os.path.exists(latest_feature_dir):
        os.mkdir(latest_feature_dir)

    os.chdir(latest_feature_dir)

    if not os.path.exists("merlin"):
        clone_cmd = "git clone https://github.com/kastnerkyle/merlin"
        pe(clone_cmd, shell=True)

    os.chdir("merlin")
    merlin_dir = os.getcwd()
    os.chdir("egs/build_your_own_voice/s1")
    experiment_dir = os.getcwd()

    if not os.path.exists("database"):
        print("Creating database and copying in VCTK files")
        pe("bash 01_setup.sh my_new_voice", shell=True)

        # Copy in wav files
        wav_partial_path = vctkdir + "wav48/"
        subfolders = sorted(os.listdir(wav_partial_path))
        # only p225 for now...
        subfolders = subfolders[:1]
        os.chdir("database/wav")
        for sf in subfolders:
            wav_path = wav_partial_path + sf + "/*.wav"
            p = pe("cp %s ." % wav_path, shell=True)
        # downsample the files
        convert = estdir + "bin/ch_wave $i -o tmp_$i -itype wav -otype wav -F 16000 -f 48000"
        pe("for i in *.wav; do echo %s; %s; mv tmp_$i $i; done" % (convert, convert), shell=True)

        os.chdir(experiment_dir)
        txt_partial_path = vctkdir + "txt/"
        subfolders = sorted(os.listdir(txt_partial_path))
        # only p225 for now...
        subfolders = subfolders[:1]
        os.chdir("database/txt")
        for sf in subfolders:
            txt_path = txt_partial_path + sf + "/*.txt"
            p = pe("cp %s ." % txt_path, shell=True)

    do_state_align = False
    if do_state_align:
        raise ValueError("Replace these lies with something that points at the right place")
        os.chdir(merlin_dir)
        os.chdir("misc/scripts/alignment/state_align")
        pe("bash setup.sh", shell=True)

        with open("config.cfg", "r") as f:
            config_lines = f.readlines()

        # replace FESTDIR with the correct path
        festdir_replace_line = None
        for n, l in enumerate(config_lines):
            if "FESTDIR=" in l:
                festdir_replace_line = n
                break

        config_lines[festdir_replace_line] = "FESTDIR=%s\n" % festdir

        # replace HTKDIR with the correct path
        htkdir_replace_line = None
        for n, l in enumerate(config_lines):
            if "HTKDIR=" in l:
                htkdir_replace_line = n
                break

        config_lines[htkdir_replace_line] = "HTKDIR=%s\n" % htkdir

        with open("config.cfg", "w") as f:
            f.writelines(config_lines)

        pe("bash run_aligner.sh config.cfg", shell=True)
    else:
        os.chdir(merlin_dir)
        if not os.path.exists("misc/scripts/alignment/phone_align/full-context-labels/full"):
            os.chdir("misc/scripts/alignment/phone_align")
            pe("bash setup.sh", shell=True)

            with open("config.cfg", "r") as f:
                config_lines = f.readlines()

            # replace ESTDIR with the correct path
            estdir_replace_line = None
            for n, l in enumerate(config_lines):
                if "ESTDIR=" in l and l[0] == "E":
                    estdir_replace_line = n
                    break

            config_lines[estdir_replace_line] = "ESTDIR=%s\n" % estdir

            # replace FESTDIR with the correct path
            festdir_replace_line = None
            for n, l in enumerate(config_lines):
                # EST/FEST
                if "FESTDIR=" in l and l[0] == "F":
                    festdir_replace_line = n
                    break

            config_lines[festdir_replace_line] = "FESTDIR=%s\n" % festdir

            # replace FESTVOXDIR with the correct path
            festvoxdir_replace_line = None
            for n, l in enumerate(config_lines):
                if "FESTVOXDIR=" in l:
                    festvoxdir_replace_line = n
                    break

            config_lines[festvoxdir_replace_line] = "FESTVOXDIR=%s\n" % festvoxdir

            with open("config.cfg", "w") as f:
                f.writelines(config_lines)

            with open("run_aligner.sh", "r") as f:
                run_aligner_lines = f.readlines()

            replace_line = None
            for n, l in enumerate(run_aligner_lines):
                if "cp ../cmuarctic.data" in l:
                    replace_line = n
                    break

            run_aligner_lines[replace_line] = "cp ../txt.done.data etc/txt.done.data\n"

            # Make the txt.done.data file
            def format_info_tup(info_tup):
                return "( " + str(info_tup[0]) + ' "' + info_tup[1] + '" )\n'

            # Now we need to get the text info
            txt_partial_path = vctkdir + "txt/"
            cwd = os.getcwd()
            out_path = "txt.done.data"
            out_file = open(out_path, "w")
            subfolders = sorted(os.listdir(txt_partial_path))
            # TODO: Avoid this truncation and have an option to select subfolder(s)...
            subfolders = subfolders[:1]

            txt_ids = []
            for sf in subfolders:
                print("Processing subfolder %s" % sf)
                txt_sf_path = txt_partial_path + sf + "/"
                for txtpath in os.listdir(txt_sf_path):
                    full_txtpath = txt_sf_path + txtpath
                    with open(full_txtpath, 'r') as f:
                        r = f.readlines()
                        assert len(r) == 1
                        # remove txt extension
                        name = txtpath.split(".")[0]
                        text = r[0].strip()
                        info_tup = (name, text)
                        txt_ids.append(name)
                        out_file.writelines(format_info_tup(info_tup))
            out_file.close()
            os.chdir(cwd)

            replace_line = None
            for n, l in enumerate(run_aligner_lines):
                if "cp ../slt_wav/*.wav" in l:
                    replace_line = n
                    break

            run_aligner_lines[replace_line] = "cp ../wav/*.wav wav\n"

            # Put wav file in the correct place
            wav_partial_path = experiment_dir + "/database/wav"
            subfolders = sorted(os.listdir(wav_partial_path))
            if not os.path.exists("wav"):
                os.mkdir("wav")
            cwd = os.getcwd()
            os.chdir("wav")
            for sf in subfolders:
                wav_path = wav_partial_path + "/*.wav"
                p = pe("cp %s ." % wav_path, shell=True)
            os.chdir(cwd)

            replace_line = None
            for n, l in enumerate(run_aligner_lines):
                if "cat cmuarctic.data |" in l:
                    replace_line = n
                    break

            run_aligner_lines[replace_line] = 'cat etc/txt.done.data | cut -d " " -f 2 > file_id_list.scp\n'

            with open("edit_run_aligner.sh", "w") as f:
                f.writelines(run_aligner_lines)

            pe("bash edit_run_aligner.sh config.cfg", shell=True)


# compile vocoder
    os.chdir(merlin_dir)
    os.chdir("tools")
    if not os.path.exists("SPTK-3.9"):
        pe("bash compile_tools.sh", shell=True)

# slt_arctic stuff
    os.chdir(merlin_dir)
    os.chdir("egs/slt_arctic/s1")
    if not os.path.exists("slt_arctic_full_data"):
        pe("bash run_full_voice.sh", shell=True)

    os.chdir(merlin_dir)
    os.chdir("misc/scripts/vocoder/world")

    with open("extract_features_for_merlin.sh", "r") as f:
        ex_lines = f.readlines()

    ex_line_replace = None
    for n, l in enumerate(ex_lines):
        if "merlin_dir=" in l:
            ex_line_replace = n
            break

    ex_lines[ex_line_replace] = 'merlin_dir="%s"' % merlin_dir

    ex_line_replace = None
    for n, l in enumerate(ex_lines):
        if "wav_dir=" in l:
            ex_line_replace = n
            break

    ex_lines[ex_line_replace] = 'wav_dir="%s"' % (experiment_dir + "/database/wav")

    with open("edit_extract_features_for_merlin.sh", "w") as f:
        f.writelines(ex_lines)

    pe("bash edit_extract_features_for_merlin.sh", shell=True)

    os.chdir(basedir)
    os.chdir("latest_features")
    os.symlink(merlin_dir + "/egs/slt_arctic/s1/slt_arctic_full_data/feat", "audio_feat")
    os.symlink(merlin_dir + "/misc/scripts/alignment/phone_align/full-context-labels/full", "text_feat")

    print("Audio features in %s (and %s)" % (os.getcwd() + "/audio_feat", merlin_dir + "/egs/slt_arctic/s1/slt_arctic_full_data/feat"))
    print("Text features in %s (and %s)" % (os.getcwd() + "/text_feat", merlin_dir + "/misc/scripts/alignment/phone_align/full-context-labels/full"))
    os.chdir(basedir)


def extract_final_features():
    launchdir = os.getcwd()
    os.chdir("latest_features")
    basedir = os.path.abspath(os.getcwd()) + "/"
    text_files = os.listdir("text_feat")
    audio_files = os.listdir("audio_feat/bap")
    os.chdir("merlin/egs/build_your_own_voice/s1")
    expdir = os.getcwd()

    # make the file list
    file_list_base = "experiments/my_new_voice/duration_model/data/"
    if not os.path.exists(file_list_base):
        os.mkdir(file_list_base)

    file_list_path = file_list_base + "file_id_list_full.scp"
    with open(file_list_path, "w") as f:
        f.writelines([tef.split(".")[0] + "\n" for tef in text_files])

    if not os.path.exists(basedir + "file_id_list_full.scp"):
        os.symlink(os.path.abspath(file_list_path), os.path.abspath(basedir + "file_id_list_full.scp"))

    # make the file list
    file_list_base = "experiments/my_new_voice/acoustic_model/data/"
    if not os.path.exists(file_list_base):
        os.mkdir(file_list_base)

    file_list_path = file_list_base + "file_id_list_full.scp"
    with open(file_list_path, "w") as f:
        f.writelines([tef.split(".")[0] + "\n" for tef in text_files])

    if not os.path.exists(basedir + "file_id_list_full.scp"):
        os.symlink(os.path.abspath(file_list_path), os.path.abspath(basedir + "file_id_list_full.scp"))

    file_list_base = "experiments/my_new_voice/test_synthesis/"
    if not os.path.exists(file_list_base):
        os.mkdir(file_list_base)

    file_list_path = file_list_base + "test_id_list.scp"
    # debug with no test utterances
    with open(file_list_path, "w") as f:
        f.writelines(["\n",])
        #f.writelines([tef.split(".")[0] + "\n" for tef in text_files[:20]])

    if not os.path.exists(basedir + "test_id_list.scp"):
        os.symlink(os.path.abspath(file_list_path), os.path.abspath(basedir + "test_id_list.scp"))


    # now copy in the data - don't symlink due to possibilities of inplace
    # modification
    os.chdir(expdir)
    basedatadir = "experiments/my_new_voice/"
    os.chdir(basedatadir)

    labeldatadir = "duration_model/data/label_phone_align"
    if not os.path.exists(labeldatadir):
        os.mkdir(labeldatadir)

    # IT USES HTS STYLE LABELS
    copytree(basedir + "text_feat", labeldatadir)

    labeldatadir = "acoustic_model/data/label_phone_align"
    if not os.path.exists(labeldatadir):
        os.mkdir(labeldatadir)

    # IT USES HTS STYLE LABELS
    copytree(basedir + "text_feat", labeldatadir)

    os.chdir(launchdir)


if __name__ == "__main__":
    if not os.path.exists("latest_features"):
        extract_intermediate_features()
    elif os.path.exists("latest_features"):
        if not os.path.exists("latest_features/text_feat") and not os.path.exists("latest_features/audio_feat"):
            print("Unable to find features, redoing feature extraction")
            os.chdir("latest_features")
            if os.path.exists("merlin"):
                shutil.rmtree("merlin")
            if os.path.exists("text_feat"):
                os.remove("text_feat")
            if os.path.exists("audio_feat"):
                os.remove("audio_feat")
            extract_intermediate_features()
        extract_final_features()
        print("NEXT STEP?")
