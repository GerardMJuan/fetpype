"""
Nodes that implement the dHCP pipeline for fetal data.

Version from https://github.com/GerardMJuan/dhcp-structural-pipeline
, which is a fork of the original dataset
https://github.com/BioMedIA/dhcp-structural-pipeline
with several fixes and changes

The docker image, where everything works "well", is:
https://hub.docker.com/r/gerardmartijuan/dhcp-pipeline-multifact

TODO: specify the changes from one version to another.
"""

import os
from nipype.interfaces.base import (
    BaseInterfaceInputSpec,
    TraitedSpec,
    File,
    Directory,
    traits,
    SimpleInterface,
    BaseInterface,
)
import shutil
import glob

class DHCPInputSpec(BaseInterfaceInputSpec):
    """
    Input specification for the DHCP pipeline.

    Attributes
    ----------
    T2 : File
        Input T2 image.
    mask : File
        Input brain mask.
    gestational_age : float
        Gestational age in weeks.
    pre_command : str
        Pre-command for running the pipeline.
    dhcp_image : str
        Docker or Singularity image for the pipeline.
    threads : int, optional
        Number of threads for running the pipeline. Defaults to the system default.
    flag : str, optional
        Flags for running the pipeline. Defaults to an empty string.
    """
    T2 = File(exists=True, desc="Input T2 image", mandatory=True)
    mask = File(exists=True, desc="Input brain mask", mandatory=True)
    gestational_age = traits.Float(
        desc="Gestational age in weeks", mandatory=True
    )
    pre_command = traits.Str(
        desc="Pre-command for running the pipeline", mandatory=True
    )
    dhcp_image = traits.Str(
        desc="Docker or Singularity image for the pipeline", mandatory=True
    )
    threads = traits.Int(
        desc="Number of threads for running the pipeline", usedefault=True
    )
    flag = traits.Str(
        desc="Flags for running the pipeline", usedefault=True
    )


class DHCPOutputSpec(TraitedSpec):
    """
    Specifies the output of the DHCP pipeline.

    Attributes:
        output_dir (str): The output directory of the DHCP pipeline.

    TODO: Specify the outputs better? or just leave it as it is?
    """
    output_dir = Directory(
        exists=True, desc="Output directory of the dhcp pipeline"
    )

    output_seg_all_labels = File(
        exists=True, desc="Output segmentation of all labels"
    )

    output_surf_wb_spec = File(
        exists=True, desc="Output surface workbench spec"
    )

class dhcp_node(BaseInterface):
    """Run the dhcp segmentation pipeline on a single subject.
    The script needs to create the output folders and put the mask
    there so that the docker image can find it and doesn't run bet.
    """

    input_spec = DHCPInputSpec
    output_spec = DHCPOutputSpec

    def _run_interface(self, runtime):

        output_dir = os.path.abspath("dhcp_output")
        os.makedirs(output_dir, exist_ok=True)

        # Basename of the T2 file
        recon_file_name = os.path.basename(self.inputs.T2)

        # Copy T2 to output dir
        shutil.copyfile(
            self.inputs.T2, os.path.join(output_dir, recon_file_name)
        )

        # Copy mask to output dir with the correct name
        os.makedirs(
            os.path.join(output_dir, "segmentations"), exist_ok=True
        )

        # check if mask file exists. If not, create it
        shutil.copyfile(
            self.inputs.mask,
            os.path.join(
                output_dir,
                "segmentations",
                f"{recon_file_name.replace('.nii.gz', '')}_brain_mask.nii.gz",
            ),
        )

        if "docker" in self.inputs.pre_command:
            cmd = self.inputs.pre_command
            cmd += (
                f"-v {output_dir}:/data "
                f"{self.inputs.dhcp_image} "
                f"/data/{recon_file_name} "
                f"{self.inputs.gestational_age} "
                "-data-dir /data "
                f"-t {self.inputs.threads} "
                "-c 0 "
                f"{self.inputs.flag} "
            )

        elif "singularity" in self.inputs.pre_command:
            # Do we need FSL for this pipeline? add in the precommand
            cmd = self.inputs.pre_command + self.inputs.dhcp_image
            cmd += (
                f"/usr/local/src/structural-pipeline/fetal-pipeline.sh "
                f"{self.inputs.T2} "
                f"{self.inputs.gestational_age} "
                f"-data-dir "
                f"{output_dir} "
                f"-t {self.inputs.threads} "
                "-c 0 "
                f"{self.inputs.flag} "
            )

        else:
            raise ValueError(
                "pre_command must either contain docker or singularity."
            )

        # Check if the output files exist
        # if not, rerun the pipeline directly here
        segmentation = os.path.join(
            output_dir,
            "segmentations",
            f"{recon_file_name.replace('.nii.gz', '')}_all_labels.nii.gz",
        )

        surface = os.path.join(
            output_dir,
            "surfaces",
            f"{recon_file_name.replace('.nii.gz', '')}_all_labels",
            "workbench",
            f"{recon_file_name.replace('.nii.gz', '')}_all_labels.native.wb.spec",
        )

        # depending on inputs.flag, we will check for different files
        if self.inputs.flag in ["-all", "surf"]:
            file_to_check = surface
        else:
            file_to_check = segmentation

        max_tries = 10
        tries = 0

        while not os.path.exists(file_to_check) and tries < max_tries:
            print("Running dhcp pipeline")
            print("Try number: ", tries)
            print(cmd)
            os.system(cmd)
            tries += 1

        return runtime

    def _list_outputs(self):
        outputs = {}
        outputs["output_dir"] = os.path.abspath("dhcp_output")
        outputs["output_seg_all_labels"] = glob.glob(os.path.abspath(
            "dhcp_output/segmentations/*_all_labels.nii.gz"
        ))[0]
        outputs["output_surf_wb_spec"] = glob.glob(os.path.abspath(
            "dhcp_output/surfaces/*/workbench/*.native.wb.spec"
        ))[0]
        return outputs