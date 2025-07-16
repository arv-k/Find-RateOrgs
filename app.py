import streamlit as st
import pandas as pd
from pipeline import run_pipeline # Import the main function

st.set_page_config(layout="wide", page_title="Doorlist Outreach Targeter")

st.title("🧠 Doorlist Outreach Targeter for MSU")
st.markdown("Student organizations scored by their likelihood of needing an event management tool.")

# --- Caching ---
# Cache the data to avoid re-running the entire pipeline on every interaction.
@st.cache_data(ttl=3600) # Cache for 1 hour
def load_data():
    """Loads data from the pipeline and caches it."""
    results_df = run_pipeline()
    return results_df

# --- Main App ---
if 'results_df' not in st.session_state:
    st.session_state.results_df = pd.DataFrame()

if st.button("🚀 Run Analysis Pipeline", type="primary"):
    with st.spinner("Running pipeline... This may take a minute or two."):
        st.session_state.results_df = load_data()
    st.success("Analysis complete!")
    # Clear cache if you want the button to always re-run fresh
    # st.cache_data.clear()

if not st.session_state.results_df.empty:
    df = st.session_state.results_df
    
    st.header("Top Organization Targets")
    
    # Display results in a more detailed format
    for index, row in df.iterrows():
        st.markdown("---")
        score_color = "green" if row['score'] >= 8 else "orange" if row['score'] >= 4 else "red"
        
        st.markdown(f"""
        ### {row['name']}
        **Score: <span style='color:{score_color}; font-size: 1.2em; font-weight:bold;'>{row['score']}/10</span>**
        """, unsafe_allow_html=True)
        
        st.info(f"**Justification:** {row['reason']}")
        
        with st.expander("Show Details"):
            st.markdown(f"**CampusLabs Description:** {row['description']}")
            if pd.notna(row['instagram_url']):
                st.markdown(f"**Instagram:** [{row['instagram_url']}]({row['instagram_url']})")
            else:
                st.markdown("**Instagram:** Not Found")

else:
    st.info("Click the button above to start the analysis.")
