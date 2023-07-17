import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe

from fetpype.nodes.niftymic import niftymic_segment, niftymic_recon

from nipype.interfaces.ants.segmentation import DenoiseImage
from ..nodes.nesvor import (
    NesvorSegmentation,
    NesvorRegistration,
    NesvorReconstruction,
)

#from nipype import config
#config.enable_debug_mode()

def print_files(files):
    print("Files:")
    print(files)
    return files

def create_nesvor_pipe(name="nesvor_pipe", params={}):
    """Nesvor based segmentation pipeline for fetal MRI

    Processing steps:
    - Masking
    - Registration

    Missing steps:
    - Denoising (?)
    - Actual reconstruction

    Params:
    - name: pipeline name (default = "nesvor_pipe")
    - params: dictionary of parameters to be passed to the pipeline

    Outputs:
    - nesvor_pipe: nipype workflow
    """

    # Creating pipeline
    nesvor_pype = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=["stacks"]), name="inputnode"
    )

    # mask Node
    mask = pe.Node(NesvorSegmentation(no_augmentation_seg=True), name="mask")

    # registration Node
    registration = pe.Node(NesvorRegistration(), name="registration")

    nesvor_pype.connect(
        [
            (inputnode, mask, [("stacks", "input_stacks")]),
            (inputnode, registration, [("stacks", "input_stacks")]),
            #(mask, registration, [("output_stack_masks", "stack_masks")]),
        ]
    )

    # recon Node
    recon = pe.Node(
        NesvorReconstruction(),
        name="reconstruction",
    )

    nesvor_pype.connect(registration, "output_slices", recon, "input_slices")
    #nesvor_pype.connect(registration, "output_slices", recon, "input_slices")

    #TODO Add pre_commands if needed (docker/singularity) for the nesvor nodes
    # Add pre_commands if needed (docker/singularity)
    # if "general" in params.keys():
    #    if "pre_command" in params["general"]:
    #        recon.inputs.pre_command = params["general"]["pre_command"]

    #    if "niftimic_image" in params["general"]:
    #        recon.inputs.niftimic_image = params["general"]["niftimic_image"]

    #else:
    #    recon.inputs.pre_command = ""
    #    recon.inputs.niftimic_image = ""

    # output node
    outputnode = pe.Node(
        niu.IdentityInterface(fields=["output_volume"]), name="outputnode"
    )

    nesvor_pype.connect(recon, "output_volume", outputnode, "output_volume")

    return nesvor_pype


def create_fet_subpipes(name="full_fet_pipe", params={}):
    """
    Create the fetal processing pipeline (sub-workflow).

    Given an input of T2w stacks, this pipeline performs the following steps:
        1. Brain extraction using MONAIfbs (dirty wrapper around NiftyMIC's
           command niftymic_segment_fetal_brains)
        2. Denoising using ANTS' DenoiseImage
        3. Perform reconstruction using NiftyMIC's command
            niftymic_run_reconstruction_pipeline

    Params:
        name:
            pipeline name (default = "full_fet_pipe")
        params:
            dictionary of parameters (default = {}). This
            dictionary contains the parameters given in a JSON
            config file. It specifies which containers to use
            for each step of the pipeline.

    Inputs:
        inputnode:
            stacks:
                list of T2w stacks
    Outputs:
        outputnode:
            recon_files:
                list of reconstructed files

    """

    print("Full pipeline name: ", name)

    # Creating pipeline
    full_fet_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=["stacks"]), name="inputnode"
    )

    # PREPROCESSING
    # 1. Brain extraction
    brain_extraction = pe.Node(
        interface=niu.Function(
            input_names=["raw_T2s", "pre_command", "niftymic_image"],
            output_names=["bmasks"],
            function=niftymic_segment,
        ),
        name="brain_extraction",
    )

    if "general" in params.keys():
        brain_extraction.inputs.pre_command = params["general"].get(
            "pre_command", ""
        )
        brain_extraction.inputs.niftymic_image = params["general"].get(
            "niftymic_image", ""
        )

    full_fet_pipe.connect(inputnode, "stacks", brain_extraction, "raw_T2s")

    # 2. Denoising
    denoising = pe.MapNode(
        interface=DenoiseImage(), iterfield=["input_image"], name="denoising"
    )

    full_fet_pipe.connect(inputnode, "stacks", denoising, "input_image")

    # merge_denoise
    merge_denoise = pe.Node(
        interface=niu.Merge(1, ravel_inputs=True), name="merge_denoise"
    )

    full_fet_pipe.connect(denoising, "output_image", merge_denoise, "in1")

    # RECONSTRUCTION
    recon = pe.Node(
        interface=niu.Function(
            input_names=["stacks", "masks", "pre_command", "niftymic_image"],
            output_names=["recon_files"],
            function=niftymic_recon,
        ),
        name="recon",
    )

    if "general" in params.keys():
        recon.inputs.pre_command = params["general"].get("pre_command", "")
        recon.inputs.niftymic_image = params["general"].get(
            "niftymic_image", ""
        )

    # OUTPUT
    full_fet_pipe.connect(merge_denoise, "out", recon, "stacks")
    full_fet_pipe.connect(brain_extraction, "bmasks", recon, "masks")

    outputnode = pe.Node(
        niu.IdentityInterface(fields=["recon_files"]), name="outputnode"
    )

    full_fet_pipe.connect(recon, "recon_files", outputnode, "recon_files")

    return full_fet_pipe
