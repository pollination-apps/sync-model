import os
import streamlit as st
from honeybee.model import Model

st.write("Welcome! Start writing your Pollination app here.")


model_1_path = '{}/samples/existing_model.hbjson'.format(os.path.dirname(__file__))
model_2_path = '{}/samples/updated_model.hbjson'.format(os.path.dirname(__file__))
model_1 = Model.from_hbjson(model_1_path)
model_2 = Model.from_hbjson(model_2_path)

st.json(model_1.comparison_report(model_2))
