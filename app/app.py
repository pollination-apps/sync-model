import os
import streamlit as st
from honeybee.model import Model

from ladybug_display.geometry3d import DisplayFace3D
from ladybug_display.visualization import ContextGeometry, VisualizationSet

import ladybug_vtk

from pollination_streamlit_viewer import viewer

from pandas import DataFrame

st.write("Welcome! Start writing your Pollination app here.")

model_1_path = '{}/samples/existing_model.hbjson'.format(os.path.dirname(__file__))
model_2_path = '{}/samples/updated_model.hbjson'.format(os.path.dirname(__file__))
model_1 = Model.from_hbjson(model_1_path)
model_2 = Model.from_hbjson(model_2_path)

comparison_report = model_1.comparison_report(model_2)

st.json(comparison_report, expanded=False)

# changes = comparison_report['changed_objects'][0]['existing_geometry']

changed = comparison_report['changed_objects']
added = comparison_report['added_objects']
deleted = comparison_report['deleted_objects']

def generate_face_3d_from_changes(changed_objects):
  faces = []
  for changes in changed_objects:
    faces.extend([DisplayFace3D.from_dict(geo) for geo in changes['existing_geometry']])
  return faces

new_geo = generate_face_3d_from_changes(changed_objects=changed)

visualization_set = VisualizationSet(
  'id',
  [
    ContextGeometry(
      'id',
      new_geo
    )
  ]
)

vtkjs = visualization_set.to_vtkjs('{}/temp'.format(os.path.dirname(__file__)))

viewer = viewer(
  'pollination-viewer',
  content = vtkjs.read_bytes()
)

st.subheader('Changed')
changed_data = DataFrame(
  data=changed,
  columns=['element_type', 'element_id', 'element_name', 'geometry_changed']
)

st.table(
  changed_data
)


st.subheader('Added')
added_data = DataFrame(
  data=added,
  columns=['element_type', 'element_id', 'element_name', 'geometry_changed']
)

st.table(
  added_data
)

st.subheader('Deleted')
deleted_data = DataFrame(
  data=deleted,
  columns=['element_type', 'element_id', 'element_name', 'geometry_changed']
)

st.table(
  deleted_data
)