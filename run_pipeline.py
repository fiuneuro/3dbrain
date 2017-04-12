#!/usr/bin/env python
import nipype.pipeline.engine as pe
from nipype.interfaces.utility.util import Function, IdentityInterface
from nipype.interfaces.freesurfer import ReconAll, MRIsCombine, MRITessellate


def get_niftis(subject_id, data_dir):
    """
    DataGrabber function from 
    https://miykael.github.io/nipype_tutorial/notebooks/basic_data_input_bids.html
    """
    from bids.grabbids import BIDSLayout
    
    layout = BIDSLayout(data_dir)
    t1s = [f.filename for f in layout.get(subject=subject_id, type='T1w',
                                          extensions=['nii', 'nii.gz'])]
    return t1s


def get_rh(pial_list):
    """
    Is there a better way of doing this?
    """
    for p in pial_list:
        if p.endswith('rh.pial'):
            return p


def get_lh(pial_list):
    """
    Is there a better way of doing this?
    """
    for p in pial_list:
        if p.endswith('lh.pial'):
            return p


def main(dataset, output_dir, sub_ids, work_dir):
    """
    Workflow to create stl file(s) for subject from BIDS dataset.
    """
    wf = pe.Workflow('3dbrain')
    wf.base_dir = work_dir  # With a BIDS App, this will be somewhere
                            # on the image, so...
    
    # Enter subjects into workflow
    subj_iterable = pe.Node(IdentityInterface(fields=['subject_id'],
                                              mandatory_inputs=True),
                            name='subj_iterable')
    subj_iterable.iterables = ('subject_id', sub_ids)
    
    # Grab T1w files from BIDS dataset
    BIDSDataGrabber = pe.MapNode(Function(function=get_niftis,
                                          input_names=['subject_id', 'data_dir'],
                                          output_names=['T1_files']),
                                 iterfield=['subject_id'],
                                 name='BIDSDataGrabber')
    BIDSDataGrabber.inputs.data_dir = dataset
    
    wf.connect(subj_iterable, 'subject_id', BIDSDataGrabber, 'subject_id')
    
    # Perform reconall on T1w files
    reconall = pe.Node(ReconAll(directive='all', openmp=4),
                       name='reconall')
    reconall.inputs.subjects_dir = output_dir  # Should this be the working directory?
    
    wf.connect(subj_iterable, 'subject_id', reconall, 'subject_id')
    wf.connect(BIDSDataGrabber, 'T1_files', reconall, 'T1_files')
    
    # Tessellate corpus callosum
    # Not sure if we need pretess
    tess = pe.Node(MRITessellate(label_value=86))
    wf.connect(reconall, 'aseg', tess, 'in_file')
    
    # Combine the two GM surface files and the corpus callosum into a brain.
    # I assume we want to add something to allow users to combine other labels.
    comb1 = pe.Node(MRIsCombine(), name='lh+cc')
    
    # TODO: Figure out how to create in_files list from reconall and tess
    wf.connect(reconall, (get_lh, 'pial'), comb1, 'in_file1')
    wf.connect(tess, 'out_file', comb1, 'in_file2')
    
    # TODO: Figure out how to create in_files list from reconall and mris1
    comb2 = pe.Node(MRIsCombine(), name='lh+cc+rh')
    comb2.inputs.out_file = 'brain.stl'  # or something
    
    wf.connect(comb1, 'out_file', comb2, 'in_file1')
    wf.connect(reconall, (get_rh, 'pial'), comb2, 'in_file2')
    
    # Datasink maybe?
