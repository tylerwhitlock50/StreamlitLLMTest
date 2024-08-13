import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import datetime as dt
import re
import sqlalchemy
import pandas as pd
from sqlalchemy.sql import text

# Load environment variables
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Current date
now = dt.datetime.now().date()

# Retrieve or create the assistant
assistant_string = 'asst_GmYZrf5g0w8rxwn5pgSpQ9Ko'
assistant = client.beta.assistants.retrieve(assistant_string)

# Streamlit app layout
st.title("Christensen Arms")
st.header("Text to SQL Assistant")
question = st.text_input('What is your question?')

if question:
    thread = client.beta.threads.create()
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role='user',
        content=question
    )
    
    # Poll the run
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )
    
    if run.status == 'completed':
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        
        # Display the response
        for i, m in enumerate(messages):
            if i == 0:
                st.markdown('### Question:')
                st.markdown(f"**{m.content[0].text.value}**")
                data = m.content[0].text.value
                
                # Use regex to isolate SQL code
                sql_match = re.search(r'(?<=```sql)(.*?)(?=```)', data, re.DOTALL)
                if sql_match:
                    sql_code = sql_match.group(0).strip()

                    st.markdown('### Verified SQL Code:')
                    st.code(sql_code, language='sql')

                    # Add a text area for the user to modify the SQL code
                    modified_sql_code = st.text_area("Modify the SQL code below and press Submit to execute:", value=sql_code, height=200)
                    
                    if st.button('Submit and Execute SQL'):
                        # Execute the modified SQL code
                        try:
                            engine = sqlalchemy.create_engine(os.getenv('POSTGRES_DB'))
                            with engine.connect() as conn:
                                st.write("Executing SQL Query:")
                                result = conn.execute(text(modified_sql_code))
                                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                            
                            # Display the DataFrame
                            st.dataframe(df)
                            
                            # Option to download the data as CSV
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="Download data as CSV",
                                data=csv,
                                file_name='query_result.csv',
                                mime='text/csv',
                            )
                        except Exception as e:
                            st.write('Error executing SQL:', e)
                else:
                    st.write('No SQL code found.')
