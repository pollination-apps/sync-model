import os, requests, json
import streamlit as st
from honeybee.model import Model

from ladybug_display.geometry3d import DisplayFace3D
from ladybug_display.visualization import ContextGeometry, VisualizationSet

import ladybug_vtk

from pollination_streamlit_viewer import viewer
from pollination_streamlit.selectors import get_api_client

from pandas import DataFrame
from st_aggrid import AgGrid, GridOptionsBuilder

from pollination_streamlit_io import send_results, get_hbjson, select_cloud_artifact

api_client = get_api_client()
project_owner = 'ladybug-tools'
project_name = 'sync-model'
st.header('Sync Model App!')

def initialize():
    """Initialize all of the session state variables"""
    if 'hbjson-a' not in st.session_state:
        st.session_state['hbjson-a'] = None
    if 'hbjson-b' not in st.session_state:
        st.session_state['hbjson-b'] = None
    if 'vis-set' not in st.session_state:
        st.session_state['vis-set'] = None
    if 'changed' not in st.session_state:
        st.session_state['changed'] = []
    if 'added' not in st.session_state:
        st.session_state['added'] = []
    if 'deleted' not in st.session_state:
        st.session_state['deleted'] = []


initialize()


st.checkbox(
    'Ignore Added',
    value=False,
    key='ignore-added-toggle'
)

st.checkbox(
    'Ignore Deleted',
    value=False,
    key='ignore-deleted-toggle'
)

@st.cache
def get_artifact_hbjson(signed_url):
    """Get a HBJSON from Pollination platform"""
    response = requests.get(signed_url, headers=api_client.headers)

    if response.status_code is 200:
        return json.loads(response.content)
    else :
        return '{}'


def generate_face_3d_from_changes(changed_objects):
    """Get DisplayFace3D from a sub-section of the ComparisonReport"""
    
    if changed_objects is None:
        return
    
    faces = []
    for changes in changed_objects:
        faces.extend([DisplayFace3D.from_dict(geo) for geo in changes['geometry']])
    return faces

def get_geometry(
  id_filter = []
):
    """Get the geometry associated with a particular change type."""

    objects = []

    objects.extend([
      change for change in st.session_state['changed'] if len(id_filter) == 0 or change['element_id'] in id_filter
    ])

    objects.extend([
      change for change in st.session_state['added'] if len(id_filter) == 0 or change['element_id'] in id_filter
    ])

    objects.extend([
      change for change in st.session_state['deleted'] if len(id_filter) == 0 or change['element_id'] in id_filter
    ])

    return generate_face_3d_from_changes(changed_objects=objects)

def recreate_vis_set(geometry):
    if not geometry:
        return

    st.session_state['vis-set'] = VisualizationSet(
      'id',
      [
        ContextGeometry(
          'id',
          geometry
        )
      ]
    )

def recreate_comparison_report(model_a, model_b):
    """Generate a ComparisonReport between two models."""
    comparison_report = model_a.comparison_report(
      model_b,
      ignore_deleted=st.session_state['ignore-deleted-toggle'],
      ignore_added=st.session_state['ignore-added-toggle']
    )
    if comparison_report is None: 
        return

    st.session_state['changed'] = comparison_report['changed_objects']
    st.session_state['added'] = comparison_report['added_objects'] \
        if 'added_objects' in comparison_report else []
    st.session_state['deleted'] = comparison_report['deleted_objects'] \
        if 'deleted_objects' in comparison_report else []

    geometry = get_geometry()

    recreate_vis_set(geometry)

    return comparison_report

# get model_a
def handle_get_hbjson():
    """Get the base Model from the CAD plugin."""
    hbjson = st.session_state['get-hbjson-a']

    model = Model.from_dict(hbjson['hbjson'])
    st.session_state['hbjson-a'] = model

    if model is not None and st.session_state['hbjson-b'] is not None:
        recreate_comparison_report(model, st.session_state['hbjson-b'])

# get model_b
# Fetch the artifact contents on selection
def handle_sel_artifact_hbjson():
    """Get the changed HBJSON from the cloud or a file."""
    artifact = st.session_state['get-hbjson-b']
    
    if artifact is None:
        st.session_state['hbjson'] = None
        return
    
    request_params = {
      'path': artifact['key']
    }

    request_path = [
        'projects',
        project_owner,
        project_name,
        'artifacts'
    ]
    url = "/".join(request_path)

    signed_url = api_client.get(path=f'/{url}/download', params=request_params)

    model = Model.from_dict(get_artifact_hbjson(signed_url))
    st.session_state['hbjson-b'] = model

    if st.session_state['hbjson-a'] is not None and model is not None:
        recreate_comparison_report(st.session_state['hbjson-a'], model)

get_hbjson(
  'get-hbjson-a',
  options={
            "subscribe" : {
                "show": False,
                "selected": False
            },
            "selection" : {
                "show": True,
                "selected": False
            }
        },
  on_change=handle_get_hbjson,
)

select_cloud_artifact(
    'get-hbjson-b',
    api_client,
    project_name=project_name,
    project_owner=project_owner,
    study_id='',
    file_name_match='.*hbjson',
    on_change=handle_sel_artifact_hbjson
)

st.info('Compare a model from Rhino with a model from Pollination Cloud.')

columns=['element_id', 'element_type', 'element_name']

# changed
if len(st.session_state['changed']) > 0:
    changed_data = DataFrame(
      data=st.session_state['changed'],
      columns=columns
    )

    gb_changed = GridOptionsBuilder.from_dataframe(changed_data)
    gb_changed.configure_selection('multiple', use_checkbox=True)
    grid_options_changed = gb_changed.build()

    AgGrid(
      changed_data,
      gridOptions=grid_options_changed,
      fit_columns_on_grid_load=True,
      key='changed-aggrid'
    )

# added
if len(st.session_state['added']) > 0:

    added_data = DataFrame(
      data=st.session_state['added'],
      columns=columns
    )

    gb_added = GridOptionsBuilder.from_dataframe(added_data)
    gb_added.configure_selection('multiple', use_checkbox=True)
    grid_options_added = gb_added.build()

    AgGrid(
      added_data,
      gridOptions=grid_options_added,
      fit_columns_on_grid_load=True,
      key='added-aggrid'
    )

# deleted
if len(st.session_state['deleted']) > 0:

    deleted_data = DataFrame(
      data=st.session_state['deleted'],
      columns=columns
    )

    gb_deleted = GridOptionsBuilder.from_dataframe(deleted_data)
    gb_deleted.configure_selection('multiple', use_checkbox=True)
    grid_options_deleted = gb_deleted.build()

    AgGrid(
      deleted_data,
      gridOptions=grid_options_deleted,
      fit_columns_on_grid_load=True,
      key='deleted-aggrid'
    )

id_filter = []

if 'changed-aggrid' in st.session_state and st.session_state['changed-aggrid'] is not None:
    # st.json(st.session_state['changed-aggrid'], expanded=False)
    id_filter.extend([c['element_id'] for c in st.session_state['changed-aggrid']['selectedRows']])

if 'added-aggrid' in st.session_state and st.session_state['added-aggrid'] is not None:
    # st.json(st.session_state['added-aggrid'], expanded=False)
    id_filter.extend([c['element_id'] for c in st.session_state['added-aggrid']['selectedRows']])

if 'deleted-aggrid' in st.session_state and st.session_state['deleted-aggrid'] is not None:
    # st.json(st.session_state['deleted-aggrid'], expanded=False)
    id_filter.extend([c['element_id'] for c in st.session_state['deleted-aggrid']['selectedRows']])


st.write(id_filter)

geometry = get_geometry(id_filter)
recreate_vis_set(geometry)

send_results(
    'send-results',
    results=st.session_state['vis-set'].to_dict() if st.session_state['vis-set'] is not None else '{}',
    option='subscribe-preview',
    options={
        'add': False,
        'delete': False,
        'preview': False,
        'clear': True,
        'subscribe-preview': True
    },
    label='Preview Changes'
)