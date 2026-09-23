import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import pandas as pd
import os

pages_dir = "./pages/"

def main():
    st.set_page_config(page_title="Firm Report List", initial_sidebar_state="collapsed")
    st.title("Blockhouse Equity Report Generator")
    st.write("Click one of the following firm names to generate their Equity Report:")
    try:
        summary_report = pd.read_csv("summary_report.csv")
    except Exception as e:
        st.error("ERROR: Missing summary_report.csv")
    
    btn_array = []

    for i in range(len(summary_report['FileName'])):
        btn_val = st.button(summary_report['FileName'][i])
        btn_array.append((btn_val, summary_report['FileName'][i]))

    for i in range(len(btn_array)):
        firm_name = btn_array[i][1]
        if btn_array[i][0]:
            try:
                switch_page(firm_name)
            except Exception as e:
                create_page(firm_name)

def create_page(firm_name):
    file_name = pages_dir + firm_name.replace(' ', '_') + '.py'
    if not os.path.exists(file_name):
        # Create a new Python file
        with open(pages_dir + "template.txt", 'r') as file:
            content = file.read()
        updated_content = content.replace("FIRM_NAME_HERE", firm_name)
        with open(file_name, 'w') as file:
            file.write(updated_content)
        st.success(f"Created a new page for {firm_name} because it didn't exist. Press the button again to navigate to the new page.")
    else:
        st.error(f"ERROR: File already exists for {firm_name}")

if __name__ == "__main__":
    main()