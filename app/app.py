import os, requests, json
import streamlit as st
from honeybee.model import Model

from ladybug_display.geometry3d import DisplayFace3D
from ladybug_display.visualization import ContextGeometry, VisualizationSet

import ladybug_vtk

from pollination_streamlit_viewer import viewer
from pollination_streamlit.selectors import get_api_client

from pandas import DataFrame

from pollination_streamlit_io import send_results, get_hbjson, select_cloud_artifact

api_client = get_api_client()

st.header('Sync Model App!')

if 'comparison-report' not in st.session_state:
    st.session_state['comparison-report'] = None

if 'hbjson-a' not in st.session_state:
    st.session_state['hbjson-a'] = None

if 'hbjson-b' not in st.session_state:
    st.session_state['hbjson-b'] = None

project_owner = 'ladybug-tools'
project_name = 'sync-model'

@st.cache
def get_artifact_hbjson(signed_url):
    response = requests.get(signed_url, headers=api_client.headers)

    if response.status_code is 200:
        return json.loads(response.content)
    else :
        return '{}'

# Fetch the artifact contents on selection
def handle_sel_artifact_hbjson():
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

    if st.session_state['hbjson-a'] is not None:
        st.session_state['comparison-report'] = st.session_state['hbjson-a'].comparison_report(model)

def handle_get_hbjson():
    hbjson = st.session_state['get-hbjson-a']

    model = Model.from_dict(hbjson['hbjson'])
    st.session_state['hbjson-a'] = model

    if st.session_state['hbjson-b'] is not None:
        st.session_state['comparison-report'] = model.comparison_report(st.session_state['hbjson-b'])

hbjson_a = get_hbjson(
  'get-hbjson-a',
  options={
            "subscribe" : {
                "show": False,
                "selected": False
            },
            "selection" : {
                "show": True,
                "selected": True
            }
        },
  on_change=handle_get_hbjson,
)

hbjson_b = select_cloud_artifact(
  'get-hbjson-b',
  api_client,
  project_name=project_name,
  project_owner=project_owner,
  study_id='',
  file_name_match='.*hbjson',
  on_change=handle_sel_artifact_hbjson,
)

st.info('Compare a model from Rhino with a model from Pollination Cloud.')

# if st.session_state['hbjson-a'] is not None:
#   st.json(st.session_state['hbjson-a'].to_dict(), expanded=False)

# if st.session_state['hbjson-b'] is not None:
#   st.json(st.session_state['hbjson-b'].to_dict(), expanded=False)

changed = st.session_state['comparison-report']['changed_objects'] if st.session_state['comparison-report'] is not None else None
added = st.session_state['comparison-report']['added_objects'] if st.session_state['comparison-report'] is not None else None
deleted = st.session_state['comparison-report']['deleted_objects'] if st.session_state['comparison-report'] is not None else None

st.selectbox(
  'Change Type',
  ['Changed', 'Added', 'Deleted'],
  key='change-type',
  index=0
)

def generate_face_3d_from_changes(changed_objects):
  faces = []
  key = 'existing_geometry' if st.session_state['change-type'] == 'Changed' else 'geometry'
  for changes in changed_objects:
    faces.extend([DisplayFace3D.from_dict(geo) for geo in changes[key]])
  return faces

def get_geometry():
  to_view = changed
  if(st.session_state['change-type'] == 'Added'):
      to_view = added
  if(st.session_state['change-type'] == 'Deleted'):
      to_view = deleted
  if to_view is None:
      return None
  new_geo = generate_face_3d_from_changes(changed_objects=to_view)
  return new_geo

geometry = get_geometry()

vis_set = None

if geometry is not None:
    vis_set = VisualizationSet(
      'id',
      [
        ContextGeometry(
          'id',
          get_geometry()
        )
      ]
    )

vis_set_dict = None

if vis_set is not None:
    vis_set_dict = vis_set.to_dict()

send_results(
  'send-results',
  results=vis_set_dict,
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

if vis_set is not None:
    vtkjs = vis_set.to_vtkjs('{}/temp'.format(os.path.dirname(__file__)))

# viewer = viewer(
#   'pollination-viewer',
#   content = vtkjs.read_bytes()
# )

with st.expander(label='Changed', expanded=False): 
  changed_data = DataFrame(
    data=changed,
    columns=['element_type', 'element_id', 'element_name']
  )
  st.table(
    changed_data
  )

with st.expander(label='Added', expanded=False):
  added_data = DataFrame(
    data=added,
    columns=['element_type', 'element_id', 'element_name']
  )
  st.table(
    added_data
  )

with st.expander(label='Deleted', expanded=False):
  deleted_data = DataFrame(
    data=deleted,
    columns=['element_type', 'element_id', 'element_name']
  )
  st.table(
    deleted_data
  )

st.json(st.session_state['comparison-report'] or '{}', expanded=False)

