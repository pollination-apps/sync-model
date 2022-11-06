import uuid
from pathlib import Path
import streamlit as st
from honeybee.model import Model

from ladybug_display.geometry3d import DisplayFace3D
from ladybug_display.visualization import ContextGeometry, VisualizationSet

from pollination_streamlit_io import send_results, get_hbjson

project_owner = 'ladybug-tools'
project_name = 'sync-model'
st.header('Sync Model!')

def initialize():
    """Initialize all of the session state variables"""
    # user session
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())[:8]
    if 'target_folder' not in st.session_state:
        st.session_state.target_folder = Path(__file__).parent
    # model session
    if 'hb_model_a' not in st.session_state:
        st.session_state['hb_model_a'] = None
    if 'hb_model_b' not in st.session_state:
        st.session_state['hb_model_b'] = None
    if 'comparison_report' not in st.session_state:
        st.session_state['comparison_report'] = None
    if 'vis_set' not in st.session_state:
        st.session_state['vis_set'] = None
    if 'sync_instructions' not in st.session_state:
        st.session_state['sync_instructions'] = None


def new_model_a():
    """Process a newly set Honeybee Model A file."""
    st.session_state.comparison_report = None
    if 'hbjson' in st.session_state['hbjson_a_data']:
        hbjson_data = st.session_state['hbjson_a_data']['hbjson']
        st.session_state.hb_model = Model.from_dict(hbjson_data)


def get_model_a():
    """Get the base Model from the CAD environment or upload."""
    hbjson_data = get_hbjson(
        label='Get Base Model', key='hbjson_a_data', on_change=new_model_a, options={
            "subscribe" : {
                "show": False,
                "selected": False
            },
            "selection" : {
                "show": True,
                "selected": False
            }
        })
    if st.session_state.hb_model_a is None and hbjson_data is not None \
            and 'hbjson' in hbjson_data:
        st.session_state.hb_model_a = Model.from_dict(hbjson_data['hbjson'])


def new_model_b():
    """Process a newly set Honeybee Model B file."""
    st.session_state.comparison_report = None
    hbjson_b_file = st.session_state.hbjson_b_data
    if hbjson_b_file:
        # save the HBJSON to a file
        hbjson_b_path = Path(
            f'./{st.session_state.target_folder}/data/'
            f'{st.session_state.user_id}/{hbjson_b_file.name}'
        )
        hbjson_b_path.parent.mkdir(parents=True, exist_ok=True)
        hbjson_b_path.write_bytes(hbjson_b_file.read())
        # load the model from the file
        st.session_state.hb_model_b = Model.from_file(hbjson_b_path.as_posix())
    else:
        st.session_state.hb_model_b = None


def get_model_b():
    """Get the updated model with changes for comparison."""
    st.file_uploader(
        'Get Comparison Model', type=['hbjson', 'json'],
        key='hbjson_b_data', on_change=new_model_b,
        help='Select a Model file to be compared to the first model.')


def run_comparison():
    """Generate the ComparisonReport between the two models."""
    # check to be sure there is a model
    model_a, model_b = st.session_state.hb_model_a, st.session_state.hb_model_b
    if not model_a or not model_b or st.session_state.comparison_report is not None:
        return

    # run the report if the button is pressed
    button_holder = st.empty()
    if button_holder.button('Run Comparison'):
        comp_report = model_a.comparison_report(model_b)
        st.session_state.comparison_report = comp_report
        button_holder.write('')


def update_vis_set():
    """Update the visualization set with new selection."""
    if st.session_state.comparison_report is None or 'changed_objects' \
            not in st.session_state.comparison_report:
        return

    vis_objects = []
    if 'changed_objects' in st.session_state.comparison_report:
        changed = st.session_state.comparison_report['changed_objects']
        for change in changed:
            st_var = st.session_state['{}_preview'.format(change['element_id'])]
            if st_var:
                vis_objects.extend(change['geometry'])
    faces = []
    for vo in vis_objects:
        faces.append(DisplayFace3D.from_dict(vo))
    st.session_state.vis_set = VisualizationSet(
        'preview_objects', [ContextGeometry('preview_objects', faces)]
    )


def build_tables():
    """Build the tables of model differences from the comparison report."""
    if st.session_state.comparison_report is None:
        return
    
    # build up a table of all the changed objects
    if 'changed_objects' in st.session_state.comparison_report:
        st.write('## Changed Objects')
        changed = st.session_state.comparison_report['changed_objects']
        col_names = ['**Preview**', '**Name**', '**Type**', '**Geometry**', '**Energy**']
        columns = st.columns([1, 2, 1, 1, 1])
        for name, col in zip(col_names, columns):
            col.write(name)
        for change in changed:
            col_0, col_1, col_2, col_3, col_4 = st.columns([1, 2, 1, 1, 1])
            col_0.checkbox(
                key='{}_preview'.format(change['element_id']), label='',
                value=False, on_change=update_vis_set)
            col_1.write(change['element_name'])
            col_2.write(change['element_type'])
            dis_geo = not change['geometry_changed']
            col_3.checkbox(
                key='{}_geo'.format(change['element_id']), label='',
                value=False, disabled=dis_geo)
            dis_en = not change['energy_changed']
            col_4.checkbox(
                key='{}_energy'.format(change['element_id']), label='',
                value=False, disabled=dis_en)


def preview_vis_set():
    """Preview any VisualizationSets created from the selection table."""
    preview_opt = {
        'add': False,
        'delete': False,
        'preview': False,
        'clear': True,
        'subscribe-preview': True
    }
    if st.session_state.vis_set is None:
        send_results(
            key='send-results', results=[],
            option='subscribe-preview',
            options=preview_opt, label='Preview Selection')
    else:
        send_results(
            key='send-results', results=st.session_state['vis_set'].to_dict(),
            option='subscribe-preview',
            options=preview_opt, label='Preview Selection'
        )


# run the main steps of the app
initialize()
get_model_a()
get_model_b()
run_comparison()
build_tables()
preview_vis_set()
