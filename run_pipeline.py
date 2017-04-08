#!/usr/bin/env python
import nipype.pipeline.engine as pe
from nipype.interfaces.utility.util import Function, IdentityInterface
from nipype.interfaces.freesurfer import ReconAll, MRIsCombine


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


def get_hemis(pial_list):
    """
    Is there a better way of doing this?
    """
    out = []
    for h in ['rh.pial', 'lh.pial']:
        temp = [p for p in pial_list if p.endswith(h)]
        out += temp
    return out


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
    
    # Combine the two GM surface files into a brain.
    # I assume we want to add something to allow users to combine other labels.
    # TODO: Create nipype mris_convert --combinesurfs interface
    mris = pe.Node(MRIsCombine(),
                   name='to_stl')
    mris.inputs.out_file = 'brain.stl'  # mris_convert may add rh. or lh. to
                                        # beg of out_file
    
    wf.connect(reconall, (get_hemis, 'pial'), mris, 'in_files')
    
    # Last thing it an output thing.
