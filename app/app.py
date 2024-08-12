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

def show_json(obj):
    st.json(json.loads(obj.model_dump_json()))

# Current date
now = dt.datetime.now().date()

# Retrieve or create the assistant
assistant_string = 'asst_GmYZrf5g0w8rxwn5pgSpQ9Ko'
assistant = client.beta.assistants.retrieve(assistant_string)
if assistant:
    st.write('Assistant already exists')
else:
    st.write('Creating assistant')
    assistant = client.beta.assistants.create(
        name=f'Text to SQL Assistant {now}',
        instructions='Your purpose is to create SQL queries that are based on the documentation uploaded. The user will ask a question and you will respond with SQL that answers that question.',
        model='gpt-4o-mini'
    )

# Streamlit app layout
st.title("Text to SQL Assistant")
question = st.text_input('What is your question?')

if question:
    # Create a new thread
    thread = client.beta.threads.create()
    
    # Show thread JSON
    #show_json(thread)
    
    # Send the user question to the assistant
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
        #show_json(messages)
        
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

                    #st.code(sql_code, language='sql')
                    st.write('Verifying SQL against table structure...')
                    verifier = client.beta.assistants.retrieve('asst_8cKm1qGPFzDpuTIqLNHaOsvC')
                    ver_thread = client.beta.threads.create()
                    ver_message = client.beta.threads.messages.create(
                        thread_id=ver_thread.id,
                        role='user',
                        content=sql_code
                    )
                    ver_run = client.beta.threads.runs.create_and_poll(
                        thread_id=ver_thread.id,
                        assistant_id=verifier.id,
                    )
                    ver_messages = client.beta.threads.messages.list(thread_id=ver_thread.id)
                    for i, ver_m in enumerate(ver_messages):
                        if i == 0:
                            st.markdown('### Verified SQL Code:')
                            sql_code = ver_m.content[0].text.value
                            sql_match = re.search(r'(?<=```sql)(.*?)(?=```)', sql_code, re.DOTALL)
                            if sql_match:
                                sql_code = sql_match.group(0).strip()
                            else:
                                sql_code = sql_code
                            st.code(sql_code, language='sql')

                    # Execute the SQL code
                    try:
                        engine = sqlalchemy.create_engine(os.getenv('POSTGRES_DB'))
                        with engine.connect() as conn:
                            st.write("Executing SQL Query:", sql_code)
                            result = conn.execute(text(sql_code))
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
