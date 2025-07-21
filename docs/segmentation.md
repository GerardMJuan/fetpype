
# Segmentation

Fetpype currently provides two state-of-the-art segmentation methods for fetal brain MRI: BOUNTI [@uus2023bounti] and the dHCP structural pipeline [@makropoulos2018developing]. Both methods operate on super-resolution reconstructed volumes, so [Reconstruction](reconstruction.md) is required before segmentation.

- **[BOUNTI](#bounti-segmentation)**: Deep learning-based brain segmentation optimized for fetal MRI
- **[dHCP Pipeline](#dhcp-structural-pipeline)**: Comprehensive structural analysis pipeline adapted for fetal brains

## BOUNTI Segmentation

BOUNTI (Brain vOlumetry and aUtomated parcellatioN for 3D feTal MRI) is a state-of-the-art deep learning-based segmentation method specifically designed for fetal brain MRI. It provides automated brain tissue segmentation and parcellation for reconstructed fetal brain volumes. You can find the original implementation [here](https://github.com/SVRTK/auto-proc-svrtk).

BOUNTI performs comprehensive brain segmentation on super-resolution reconstructed fetal brain MRI volumes

### Key Features

- **Automated Segmentation**: No manual intervention required
- **Multi-tissue Classification**: Segments 19 brain tissues and structures
- **Container-based**: Runs in Docker/Singularity for reproducibility

### Labels

```
Label ID,Anatomy
1,eCSF Left
2,eCSF Right
3,Cortical GM Left
4,Cortical GM Right
5,Fetal WM Left
6,Fetal WM Right
7,Lateral Ventricle Left
8,Lateral Ventricle Right
9,Cavum septum pellucidum
10,Brainstem
11,Cerebellum Left
12,Cerebellum Right
13,Cerebellar Vermis
14,Basal Ganglia Left
15,Basal Ganglia Right
16,Thalamus Left
17,Thalamus Right
18,Third Ventricle
19,Fourth Ventricle
```

### Configuration

The configuration file for BOUNTI is as follows:

- Docker:

```yaml
pipeline: "bounti"
docker: 
  cmd: "docker run --rm <mount>
    fetalsvrtk/segmentation:general_auto_amd 
    bash /home/auto-proc-svrtk/scripts/auto-brain-bounti-segmentation-fetal.sh 
    <input_dir> <output_dir>"
singularity:
  cmd: "singularity exec -u --bind <singularity_mount> --bind <tmp_dir>:/home/tmp_proc --nv
    <singularity_path>/bounti.sif
    bash /home/auto-proc-svrtk/scripts/auto-brain-bounti-segmentation-fetal.sh 
    <input_dir> <output_dir>"
path_to_output: "<basename>-mask-brain_bounti-19.nii.gz"
```

### Note regarding Singularity

The image have can have some incompatibilities with an HPC environment, as the code inside the image uses /home/tmp_proc as a temporary directory. To solve this, you need to define a <tmp_dir> in the yaml main config file. This will be used to store temporary files. The example configuration files already include the tag.

### Output

**Primary Output**: `<input_basename>-mask-brain_bounti-19.nii.gz`
- Multi-label segmentation map with 19 different brain structures
- Integer labels (0-19) corresponding to specific anatomical regions

**BIDS Output**: `sub-<subject>_ses-<session>_rec-<reconstruction>_seg-bounti_dseg.nii.gz`

---

## dHCP Structural Pipeline

The [dHCP (developing Human Connectome Project)](https://www.developingconnectome.org/) structural pipeline is a comprehensive framework originally designed for neonatal brain MRI analysis, adapted for fetal brain imaging. This pipeline provides advanced brain segmentation, surface extraction, and cortical analysis capabilities. The original implementation is [here](https://github.com/BioMedIA/dhcp-structural-pipeline), while a custom implementation with updated packages, which is the one being used in Fetpype, can be found [here](https://github.com/gerardmartijuan/dhcp-pipeline-multifact).

### Overview

The dHCP pipeline represents a state-of-the-art approach to structural brain analysis in the developing brain context. It provides detailed segmentation and surface-based analysis capabilities specifically optimized for the developing brain anatomy.

### Key Capabilities

- **Multi-tissue Segmentation**: Comprehensive brain tissue classification, including 9 tissue types and 87 cortical and subcortical regions.
- **Surface Extraction**: Generation of white matter and pial surfaces  .
- **Cortical Analysis**: Thickness, curvature, and surface-based measurements.
- **Gestational Age Integration**: Requires and utilizes gestational age information.

### Configuration

```yaml
pipeline: "dhcp"
docker:
  cmd: "docker run <mount> gerardmartijuan/dhcp-pipeline-multifact 
    <input_srr> <gestational_age> -data-dir <output_dir> -all"
singularity:
  cmd: "singularity exec --env PREPEND_PATH=/home/gmarti/LIB/fsl/bin --bind <singularity_mount> <singularity_path>/dhcp-pipeline-multifact.sif 
    /usr/local/src/structural-pipeline/fetal-pipeline.sh 
    <input_srr> <gestational_age> -data-dir <output_dir> -all"
path_to_output: "" # Leave it out so that the whole path and files are copied
```

### Gestational Age Requirement

The dHCP pipeline requires gestational age information, which can be provided through the `participants.tsv` file in the root of the BIDS dataset:

```tsv
participant_id    gestational_age
sub-01           28.5
sub-02           32.1
sub-03           25.8
```

### Processing Stages

You can choose to run only the segmentation, the surface reconstruction, or both. The default is to run both. The following options are available, and you should add them to the "cmd" field of the configuration file:

#### `-seg` (Segmentation Only)
- Brain tissue segmentation using age-appropriate priors
- White matter, gray matter, and CSF classification
- Fastest processing option

#### `-surf` (Surface Reconstruction)
- White matter and pial surface generation
- Topology correction and smoothing
- Enables surface-based analysis

#### `-all` (Complete Processing)
- Full segmentation and surface pipeline
- Cortical thickness computation
- Surface-based analysis metrics

### Known dHCP issues

The pipeline has been shown to fail in specific systems. We are still investigating the cause of this issue, but if the pipeline fails with the following error in logs/<image_name>-tissue-em-err.log:

```
10%...Error: draw-em command returned non-zero exit status -8
```

Try to run the pipeline in a different system or, if you are in an HPC, in a different node. If the problem persists, please open an issue on the [GitHub repository](https://github.com/gerardmartijuan/dhcp-pipeline-multifact/issues) with the characteristics of the system you are using.