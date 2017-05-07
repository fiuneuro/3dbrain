#!/usr/bin/env python
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
from nipype.interfaces.utility.util import Function, IdentityInterface
from nipype.interfaces.freesurfer import ReconAll, MRIsCombine, MRIsConvert


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


def to_list(f1, f2):
    """
    Simple function to format inputs to MRIsCombine
    """
    return [f1, f2]


def main(dataset, output_dir, sub_ids, work_dir):
    """
    Workflow to create stl file(s) for subject from BIDS dataset.
    """
    wf = pe.Workflow('3dbrain')
    wf.base_dir = work_dir  # With a BIDS App, this will be somewhere
                            # on the image, so...
    wf.config['execution']['crashdump_dir'] = work_dir
    
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
    
    # Convert each pial file to stl format.
    conv_rh = pe.Node(MRIsConvert(), name='conv_rh')
    wf.connect(reconall, (get_rh, 'pial'), conv_rh, 'in_file')
    
    conv_lh = pe.Node(MRIsConvert(), name='conv_lh')
    wf.connect(reconall, (get_lh, 'pial'), conv_lh, 'in_file')
    
    # Combine the two GM surface files into a brain.
    # I assume we want to add something to allow users to combine other labels.
    tolist = pe.Node(Function(function=to_list,
                               input_names=['f1', 'f2'],
                               output_names=['lst']),
                       name='ToList')
    wf.connect(reconall, (get_lh, 'pial'), tolist, 'f1')
    wf.connect(reconall, (get_rh, 'pial'), tolist, 'f2')
    
    comb = pe.Node(MRIsCombine(), name='rh+lh')
    wf.connect(tolist, 'lst', comb, 'in_files')
    
    # Save the relevant data into an output directory
    datasink = pe.Node(nio.DataSink(), name='datasink')
    datasink.inputs.base_directory = output_dir
    wf.connect(conv_rh, 'out_file', datasink, 'rh_stl')
    wf.connect(conv_lh, 'out_file', datasink, 'lh_stl')
    wf.connect(comb, 'out_file', datasink, 'full_stl')
    
    # Run things
    wf.run(plugin='LSF', plugin_args={'bsub_args': '-q PQ_nbc'})
