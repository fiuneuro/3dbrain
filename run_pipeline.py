#!/usr/bin/env python

from nipype.interfaces.freesurfer import ReconAll, MRIsCombine

reconall = ReconAll()
reconall.inputs.subject_id = 'klb'
reconall.inputs.directive = 'all'
reconall.inputs.subjects_dir = '/home/data/nbc/3dbrain/'
reconall.inputs.T1_files = '/home/data/nbc/3dbrain/klb_brain.nii.gz'
reconall.inputs.openmp = 4
reconall.run()

# TODO: Create nipype mris_convert --combinesurfs interface
mris = MRIsCombine()
mris.inputs.in_files = ['rh.pial', 'lh.pial']
mris.inputs.out_file = 'bh.stl'
mris.run()
