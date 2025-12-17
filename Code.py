import pandas as pd
import numpy as np
import streamlit as st

st.title("European Cities Data Cleaning")

Euro_city = pd.read_csv('Euro_city.csv')
Euro_city = Euro_city.dropna()