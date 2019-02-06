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
