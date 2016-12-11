from __future__ import print_function
import os
import shutil
import stat
import subprocess
import time
import numpy as np

# File to extract features (mostly) automatically using the merlin speech
# pipeline
def subfolder_select(subfolders):
    r = [sf for sf in subfolders if sf == "p294"]
    if len(r) == 0:
        raise ValueError("Error: subfolder_select failed")
    return r

# Need to edit the conf...
def replace_conflines(conf, match, sub):
    replace = None
    for n, l in enumerate(conf):
        if l[:len(match)] == match:
            replace = n
            break
    conf[replace] = "%s: %s\n" % (match, sub)
    return conf

def replace_write(fpath, match, sub):
    with open(fpath, "r") as f:
        conf = f.readlines()
    conf = replace_conflines(conf, match, sub)

    with open(fpath, "w") as f:
        f.writelines(conf)

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

# from merlin
def load_binary_file(file_name, dimension):
    fid_lab = open(file_name, 'rb')
    features = np.fromfile(fid_lab, dtype=np.float32)
    fid_lab.close()
    assert features.size % float(dimension) == 0.0,'specified dimension %s not compatible with data'%(dimension)
    features = features[:(dimension * (features.size / dimension))]
    features = features.reshape((-1, dimension))
    return  features

def array_to_binary_file(data, output_file_name):
    data = np.array(data, 'float32')
    fid = open(output_file_name, 'wb')
    data.tofile(fid)
    fid.close()

def load_binary_file_frame(file_name, dimension):
    fid_lab = open(file_name, 'rb')
    features = np.fromfile(fid_lab, dtype=np.float32)
    fid_lab.close()
    assert features.size % float(dimension) == 0.0,'specified dimension %s not compatible with data'%(dimension)
    frame_number = features.size / dimension
    features = features[:(dimension * frame_number)]
    features = features.reshape((-1, dimension))
    return  features, frame_number


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
    latest_feature_dir = os.getcwd()

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
        # only p294 for now...
        subfolders = subfolder_select(subfolders)
        os.chdir("database/wav")
        for sf in subfolders:
            wav_path = wav_partial_path + sf + "/*.wav"
            pe("cp %s ." % wav_path, shell=True)
        # downsample the files
        convert = estdir + "bin/ch_wave $i -o tmp_$i -itype wav -otype wav -F 16000 -f 48000"
        pe("for i in *.wav; do echo %s; %s; mv tmp_$i $i; done" % (convert, convert), shell=True)

        os.chdir(experiment_dir)
        txt_partial_path = vctkdir + "txt/"
        subfolders = sorted(os.listdir(txt_partial_path))
        # only p294 for now...
        subfolders = subfolder_select(subfolders)
        os.chdir("database/txt")
        for sf in subfolders:
            txt_path = txt_partial_path + sf + "/*.txt"
            pe("cp %s ." % txt_path, shell=True)

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
            subfolders = subfolder_select(subfolders)

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
            pe("cp %s %s/txt.done.data" % (out_path, latest_feature_dir),
               shell=True)
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
                pe("cp %s ." % wav_path, shell=True)
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

    global_config_file = "conf/global_settings.cfg"
    # This madness due to autogen configs...
    pe("bash scripts/setup.sh slt_arctic_full", shell=True)
    pe("bash scripts/prepare_config_files.sh %s" % global_config_file, shell=True)
    pe("bash scripts/prepare_config_files_for_synthesis.sh %s" % global_config_file, shell=True)
    # delete the setup lines from run_full_voice.sh
    pe("sed -i.bak -e '11d;12d;13d' run_full_voice.sh", shell=True)

    pushd = os.getcwd()
    os.chdir("conf")

    replace_write("duration_slt_arctic_full.conf", "training_epochs", "1")
    replace_write("duration_slt_arctic_full.conf", "warmup_epoch", "1")
    replace_write("acoustic_slt_arctic_full.conf", "training_epochs", "1")
    replace_write("acoustic_slt_arctic_full.conf", "warmup_epoch", "1")

    os.chdir(pushd)
    if not os.path.exists("slt_arctic_full_data"):
        pe("bash run_full_voice.sh", shell=True)

    pe("mv run_full_voice.sh.bak run_full_voice.sh", shell=True)

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

    bapdatadir = "acoustic_model/data/bap"
    if not os.path.exists(bapdatadir):
        os.mkdir(bapdatadir)

    lf0datadir = "acoustic_model/data/lf0"
    if not os.path.exists(lf0datadir):
        os.mkdir(lf0datadir)

    mgcdatadir = "acoustic_model/data/mgc"
    if not os.path.exists(mgcdatadir):
        os.mkdir(mgcdatadir)

    # IT USES HTS STYLE LABELS
    copytree(basedir + "text_feat", labeldatadir)
    copytree(basedir + "audio_feat/bap", bapdatadir)
    copytree(basedir + "audio_feat/lf0", lf0datadir)
    copytree(basedir + "audio_feat/mgc", mgcdatadir)
    #pe("cp %s acoustic_model/data" % label_norm_HTS_420.dat)

    while len(os.listdir(mgcdatadir)) < len(os.listdir(basedir + "audio_feat/mgc")):
        print("waiting for mgc file copy to complete...")
        time.sleep(3)

    while len(os.listdir(lf0datadir)) < len(os.listdir(basedir + "audio_feat/lf0")):
        print("waiting for lf0 file copy to complete...")
        time.sleep(3)

    while len(os.listdir(bapdatadir)) < len(os.listdir(basedir + "audio_feat/bap")):
        print("waiting for bap file copy to complete...")
        time.sleep(3)

    os.chdir(expdir)

    global_config_file="conf/global_settings.cfg"
    pe("bash scripts/prepare_config_files.sh %s" % global_config_file, shell=True)
    pe("bash scripts/prepare_config_files_for_synthesis.sh %s" % global_config_file, shell=True)

    replace_write("conf/acoustic_my_new_voice.conf", "dmgc", "60")
    replace_write("conf/acoustic_my_new_voice.conf", "dbap", "1")
    # hack this to add an extra line in the config
    replace_write("conf/acoustic_my_new_voice.conf", "dlf0", "1\ndo_MLPG: False")
    replace_write("conf/acoustic_my_new_voice.conf", "TRAINDNN", "False")
    replace_write("conf/acoustic_my_new_voice.conf", "DNNGEN", "False")
    replace_write("conf/acoustic_my_new_voice.conf", "GENWAV", "False")
    replace_write("conf/acoustic_my_new_voice.conf", "CALMCD", "False")

    replace_write("conf/duration_my_new_voice.conf", "TRAINDNN", "False")
    replace_write("conf/duration_my_new_voice.conf", "DNNGEN", "False")
    replace_write("conf/duration_my_new_voice.conf", "CALMCD", "False")

    pe("sed -i.bak -e '19,20d;30,39d' 03_run_merlin.sh", shell=True)
    pe("bash 03_run_merlin.sh 2>&1", shell=True)
    pe("mv 03_run_merlin.sh.bak 03_run_merlin.sh", shell=True)
    if not os.path.exists(basedir + "final_acoustic_data"):
        os.symlink(os.path.abspath("experiments/my_new_voice/acoustic_model/data"),
                                   basedir + "final_acoustic_data")
    if not os.path.exists(basedir + "final_duration_data"):
        os.symlink(os.path.abspath("experiments/my_new_voice/duration_model/data"),
                                   basedir + "final_duration_data")
    os.chdir(launchdir)


def save_numpy_features():
    n_ins = 420
    n_outs = 63  # 187

    feature_dir = "latest_features/"
    with open(feature_dir + "file_id_list_full.scp") as f:
        file_list = [l.strip() for l in f.readlines()]

    speaker_set = [x[:4] for x in file_list]
    speaker_set = sorted(list(set(speaker_set)))
    speaker_dict = {x: i + 1 for i, x in enumerate(speaker_set)}

    text_file = feature_dir + 'txt.done.data'

    with open(text_file) as f:
        text_data = [l.strip() for l in f.readlines()]
    text_ids = [td.split(" ")[1] for td in text_data]
    text_utts = [td.split('"')[1] for td in text_data]
    text_tups = list(zip(text_ids, text_utts))
    text_lu = {k: v for k, v in text_tups}
    text_rlu = {v: k for k, v in text_lu.items()}

    monophone_path = os.path.abspath("latest_features/monophones") + "/"
    if not os.path.exists(monophone_path):
        os.symlink(os.path.abspath("latest_features/merlin/misc/scripts/alignment/phone_align/cmu_us_slt_arctic/lab"), monophone_path)

    launchdir = os.getcwd()
    phone_files = {gl[:-4]: monophone_path + gl for gl in os.listdir(monophone_path)
                if gl[-4:] == ".lab"}

    error_files = [
        (i, x) for i, x in enumerate(text_ids) if x not in file_list]

    # Solve corrupted files issues
    cont = 0
    for i, x in error_files:
        print("Removing error files %s" % text_data.pop(i - cont))
        cont += 1

    assert len(text_tups) == len(file_list)
    assert sum([ti not in file_list for ti in text_ids]) == 0

    char_set = sorted(list(set(''.join(text_utts).lower())))
    char2code = {x: i + 1 for i, x in enumerate(char_set)}
    code2char = {v: k for k, v in char2code.items()}

    phone_set = tuple('sil',)
    for fid in file_list:
        with open(phone_files[fid]) as f:
            phonemes = [p.strip() for p in f.readlines()]
        phonemes = [x.strip().split(' ') for x in phonemes[1:]]
        durations, phonemes = zip(*[[float(x), z] for x, y, z in phonemes])
        phone_set = tuple(sorted(list(set(phone_set + phonemes))))
    phone2code = {x: i + 1 for i, x in enumerate(phone_set)}
    code2phone = {v: k for k, v in phone2code.items()}

    label_files_path = os.path.abspath("latest_features/final_acoustic_data/nn_no_silence_lab_420") + "/"
    audio_files_path = os.path.abspath("latest_features/final_acoustic_data/nn_mgc_lf0_vuv_bap_63") + "/"
    label_files = {lf[:-4]: label_files_path + lf for lf in os.listdir(label_files_path) if lf[-4:] == ".lab"}
    audio_files = {af[:-4]: audio_files_path + af for af in os.listdir(audio_files_path) if af[-4:] == ".cmp"}

    order = range(len(file_list))
    np.random.seed(1)
    np.random.shuffle(order)

    all_in_features = []
    all_out_features = []
    all_phonemes = []
    all_durations = []
    all_text = []
    all_ids = []
    for i, idx in enumerate(order):
        fid = file_list[idx]
        #if i % 100 == 0:
        #    print(i)
        in_features, lab_frame_number = load_binary_file_frame(
            label_files[fid], n_ins)
        out_features, out_frame_number = load_binary_file_frame(
            audio_files[fid], n_outs)

        #print(lab_frame_number)
        #print(out_frame_number)
        if lab_frame_number != out_frame_number:
            print("WARNING: misaligned frame size for %s, using min" % fid)
            mf = min(lab_frame_number, out_frame_number)
            in_features = in_features[:mf]
            out_features = out_features[:mf]

        with open(phone_files[fid]) as f:
            phonemes = f.readlines()

        phonemes = [x.strip().split(' ') for x in phonemes[1:]]
        durations, phonemes = zip(*[[float(x), z] for x, y, z in phonemes])

        # first non pause phoneme
        first_phoneme = next(
            k - 1 for k, x in enumerate(phonemes) if x != 'pau')

        last_phoneme = len(phonemes) - next(
            k - 1 for k, x in enumerate(phonemes[::-1]) if x != 'pau')

        phonemes = phonemes[first_phoneme:last_phoneme]
        durations = durations[first_phoneme:last_phoneme]

        assert phonemes[0] == 'pau'
        assert phonemes[-1] == 'pau'
        # assert 'pau' not in phonemes[1:-1]
        phonemes = phonemes[1:-1]

        durations = np.array(durations)
        durations = durations * 200
        durations = durations - durations[0]
        durations = durations[1:] - durations[:-1]
        durations = durations[:-1]
        durations = np.round(durations, 0).astype('int32')
        phonemes = np.array([phone2code[x] for x in phonemes], dtype='int32')
        all_in_features.append(in_features)
        all_out_features.append(out_features)
        all_phonemes.append(phonemes)
        all_durations.append(durations)
        all_text.append(text_lu[fid])
        all_ids.append(fid)

    assert len(all_in_features) == len(all_out_features)
    assert len(all_in_features) == len(all_phonemes)
    assert len(all_in_features) == len(all_durations)
    assert len(all_in_features) == len(all_text)
    assert len(all_in_features) == len(all_ids)

    if not os.path.exists("latest_features/numpy_features"):
        os.mkdir("latest_features/numpy_features")

    for i in range(len(all_ids)):
        print("Saving %s" % all_ids[i])
        save_dict = {"file_id": all_ids[i],
                    "phonemes": all_phonemes[i],
                    "durations": all_durations[i],
                    "text_features": all_in_features[i],
                    "audio_features": all_out_features[i],
                    "mgc_extent": 60,
                    "lf0_idx": 60,
                    "vuv_idx": 61,
                    "bap_idx": 62,
                    "phone2code": phone2code,
                    "char2code": char2code,
                    "speaker2code": speaker_dict,
                    }

        np.savez_compressed("latest_features/numpy_features/%s.npz" % all_ids[i],
                            kwargs=save_dict)


if __name__ == "__main__":
    if not os.path.exists("latest_features"):
        extract_intermediate_features()
    elif os.path.exists("latest_features"):
        if not os.path.exists("latest_features/text_feat") and not os.path.exists("latest_features/audio_feat"):
            print("Redoing feature extraction")
            os.chdir("latest_features")
            if os.path.exists("merlin"):
                shutil.rmtree("merlin")
            if os.path.exists("text_feat"):
                os.remove("text_feat")
            if os.path.exists("audio_feat"):
                os.remove("audio_feat")
            extract_intermediate_features()

    if not os.path.exists("latest_features/final_duration_data") or not os.path.exists("latest_features/final_acoustic_data"):
        extract_final_features()
    if not os.path.exists("latest_features/numpy_features"):
        save_numpy_features()
    print("Feature extraction complete!")
