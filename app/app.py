import uuid, json
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
    if 'synced_model' not in st.session_state:
        st.session_state['synced_model'] = None

    if 'default_preview_chng' not in st.session_state:
        st.session_state['default_preview_chng'] = False


def new_model_a():
    """Process a newly set Honeybee Model A file."""
    st.session_state.comparison_report = None
    data=st.session_state.synced_model = None
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
    data=st.session_state.synced_model = None
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


def setup_select_all(container):
    """Setup check boxes to select all values."""
    if st.session_state.comparison_report is None or 'changed_objects' not in \
            st.session_state.comparison_report:
        return
    col_0, _, _, col_3, col_4 = container.columns([1, 2, 1, 1, 1])
    col_0.checkbox(key='preview_chng', label='Changed', value=True)
    col_3.checkbox(key='geo_all', label='All', value=True)
    col_4.checkbox(key='energy_all', label='All', value=True)


def build_changes_tables(table_container):
    """Build the tables of model differences from the comparison report."""
    if st.session_state.comparison_report is None:
        return
    
    # build up a table of all the changed objects
    if 'changed_objects' in st.session_state.comparison_report:
        # write the top row with the labels
        table_container.write('## Changed Objects')
        changed = st.session_state.comparison_report['changed_objects']
        col_names = ['**Preview**', '**Name**', '**Type**', '**Geometry**', '**Energy**']
        columns = table_container.columns([1, 2, 1, 1, 1])
        for name, col in zip(col_names, columns):
            col.write(name)
        # write a row for each change detected in the model
        for change in changed:
            col_0, col_1, col_2, col_3, col_4 = table_container.columns([1, 2, 1, 1, 1])
            def_prev_val = change['geometry_changed'] \
                if st.session_state.preview_chng else False
            col_0.checkbox(
                key='{}_preview'.format(change['element_id']), label='',
                value=def_prev_val, on_change=update_vis_set)
            col_1.write(change['element_name'])
            col_2.write(change['element_type'])
            dis_geo = not change['geometry_changed']
            def_accept_geo = st.session_state.geo_all
            col_3.checkbox(
                key='{}_geo'.format(change['element_id']), label='',
                value=def_accept_geo, disabled=dis_geo)
            dis_en = not change['energy_changed']
            def_accept_energy = st.session_state.energy_all
            col_4.checkbox(
                key='{}_energy'.format(change['element_id']), label='',
                value=def_accept_energy, disabled=dis_en)

        if st.session_state.preview_chng != st.session_state.default_preview_chng:
            update_vis_set()
            st.session_state.default_preview_chng = st.session_state.preview_chng


def build_merged_model():
    """Build the merged model from the sync instructions."""
    # check to be sure there is a model
    if st.session_state.comparison_report is None:
        return

    # run the report if the button is pressed
    button_holder = st.empty()
    if button_holder.button('Merge Models'):
        # generate the SyncInstructions
        sync_instructions = {}
        if 'changed_objects' in st.session_state.comparison_report:
            changed = st.session_state.comparison_report['changed_objects']
            sync_changes = []
            for change in changed:
                up_geo = st.session_state['{}_geo'.format(change['element_id'])]
                up_energy = st.session_state['{}_energy'.format(change['element_id'])]
                sync_obj = {
                    'element_id': change['element_id'],
                    'element_name': change['element_name'],
                    'element_type': change['element_type'],
                    'update_geometry': up_geo,
                    'update_energy': up_energy
                }
                sync_changes.append(sync_obj)
            sync_instructions['changed_objects'] = sync_changes

        # generate the merged model with the instructions
        button_holder.write('')
        new_model = Model.from_sync(
            st.session_state.hb_model_a, st.session_state.hb_model_b, sync_instructions)
        st.session_state.synced_model = json.dumps(new_model.to_dict())
    
    if st.session_state.synced_model:
        st.download_button(
            label='Get Synced Model', data=st.session_state.synced_model,
            file_name='synced_model.hbjson')


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


# initialize variables and run the comparison
initialize()
get_model_a()
get_model_b()
run_comparison()

# generate tables of changed objects
change_table_container = st.container()  # container to hold the table
change_sel_all_container = st.container()  # container to hold the tables
setup_select_all(change_sel_all_container)
build_changes_tables(change_table_container)

# build a new model and manage the Rhino scene preview
build_merged_model()
preview_vis_set()
