# Speech audio feature extraction processor by Kyle Kastner

Extract features with HTK/speech\_tools/festival/merlin.

This is a fork of gist [https://gist.github.com/kastnerkyle/cc0ac48d34860c5bb3f9112f4d9a0300](https://gist.github.com/kastnerkyle/cc0ac48d34860c5bb3f9112f4d9a0300)

The data is processed using [Merlin](http://www.cstr.ed.ac.uk/projects/merlin/). From each audio clip the vocoder features are extracted using the [WORLD](https://github.com/mmorise/World) vocoder. The resulting dataset will be located under subfolder ```data``` as follows:

```
loop
├── data
    └── vctk
        ├── norm_info
        │   ├── norm.dat
        ├── numpy_feautres
        │   ├── p294_001.npz
        │   ├── p294_002.npz
        │   └── ...
        └── numpy_features_valid
```

## Prerequsites

```
sudo apt-get install tcl-snack sox doxygen xsltproc graphviz texlive texinfo texi2html libncurses5-dev csh
sudo pip install theano matplotlib bandmat wget lxml
```

Note pip modules are to be installed for Python 2.7.

## Deployment

First, build all the necessary tools and utilities:

```
python ./install_tts.py
```

Then run the feature extraction script itself:

```
python ./extract_feats.py -w ./vctk/VCTK-Corpus/wav48/p225 -t ./vctk/VCTK-Corpus/txt/p225
```
