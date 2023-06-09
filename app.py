from dash import dash, html, dcc, dash_table, Input, Output, State
import dash_bootstrap_components as dbc
import re
import pandas as pd
from datetime import datetime, timedelta
import base64
import json

table_columns = ['p_code', 'checkin', 'checkout', 'credit_sum', 'softtime', 'n_days', 'block_sum','tafb','flight_data']
display_columns = ['Code','Check-In','Check-out','Credit','Soft','Days','Block','TAFB','Flight Data']

flight_columns = ['Day', 'Flt', 'Dep', 'D.Local', 'Arr', 'A.Local', 'Turn', 'Eqp', 'Block']

def format_timedelta(td):
    total_hours = td.total_seconds() // 3600
    hours = int(total_hours)  # Hours within a day
    minutes = int((td.total_seconds() // 60) % 60)  # Minutes
    return f"{hours:03d}:{minutes:02d}"

def format_timedelta_alt(td):
    days = td.days
    hours = td.seconds // 3600
    minutes = (td.seconds // 60) % 60
    return f"{days} days, {hours:02d}:{minutes:02d}"

# Create the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LITERA])
app.title = 'Parser'
server = app.server

import dash_bootstrap_components as dbc

app.layout = dbc.Container(
    fluid=True,
    className='container',
    children=[
        dbc.Row(
            [
                html.H1("Pairings Parser"),
                dcc.Store(id='selected_row_store'),
                dcc.Markdown(
                            '''
                            This web app is designed to provide an interactive interface for exploring pairing data. 
                            Pairings are displayed on the left and can be filtered and sorted. 
                            Full details appear on the right when you click on a row. 
                            Feel free to get started with the preloaded data, or upload your own.
                            '''
                        ),
            ],
            className='row',
            style={'textAlign':'center'}
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Store(id='upload-data-store'),
                        dcc.Upload(
                                id='upload-data',
                                children=html.Div([
                                    'Drag and Drop or ',
                                    html.A('Select Files')
                                ]),
                                style={
                                    'width': '95%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '1px',
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'textAlign': 'center',
                                    'margin': '10px'
                                },
                                multiple=False
                            ),
                        html.Div(
                                id='output-data-upload',
                                style={
                                    'margin': '10px'
                                    }
                            ),
                        html.Div(
                            [
                                "Select date range: ",
                                dcc.DatePickerRange(
                                    id='my-date-picker-range',
                                    clearable=True,
                                    minimum_nights=0,
                                    start_date_placeholder_text="Start Date",
                                    end_date_placeholder_text="End Date"
                                ),
                            ],
                            style={'margin':'10px'}
                        ),
                        html.Div(
                            [
                                "Select number of days:",
                                dcc.RangeSlider(
                                        id='range-slider',
                                        value=[1, 5],
                                        step=1,
                                        marks={i: str(i) for i in range(1,6)},
                                        allowCross=False,
                                        updatemode='drag'
                                    ),
                            ],
                            style={'margin':'10px'}
                        ),
                        html.Div(
                            id='output-data-table',
                            children=dash_table.DataTable(
                                id='datatable',
                                columns=[{"name": col, "id": col_id} for col, col_id in zip(display_columns[0:5],table_columns[0:5])],
                                data=[],
                                sort_action='native',
                                sort_mode='multi',
                                style_data_conditional=[]
                                )
                            )
                    ],
                    className='col-md-5'
                ),
                dbc.Col(
                    [
                        html.Div(
                            [],
                            id='selected_row_info'
                        ),
                    ],
                    className='col-md-7'
                ),
            ],
            className='row',
        ),
        dbc.Row(
            [
                html.Div(
                            [
                                dcc.Markdown(
                                    '''
                                    For more information about this project you can visit its [GitHub repo](https://github.com/ryan-j-pratt/pairings-parser/tree/main).
                                    '''
                                ),
                            ],
                            className='about-section',
                            style={'margin':'10px'}
                        ),
            ],
            className='row',
            style={'textAlign':'center'}
        ),
    ],
)

@app.callback([Output('upload-data-store','data'), Output('output-data-upload','children')], [Input('upload-data','contents')], [State('upload-data', 'filename')])
def process_uploaded_file(contents, filename):
    if contents is not None:
        # Read the file contents
        file_content = contents.encode("utf8").split(b";base64,")[1]
        decoded_content = base64.b64decode(file_content).decode("utf8")
        
        # Remove line breaks and create a continuous string
        file_contents = decoded_content.replace("\n", "")
        
        pairings = file_contents.split('----------------------------------------------------------------------------------------------------')
        del pairings[0]
        del pairings[-1]

        table_data = pd.DataFrame(columns=table_columns)

        for pairing in pairings:

            flight_data = []
            obs = pd.DataFrame(columns=table_columns)
            p_code = ""
            n_days = 0
            credit_sum = timedelta()
            block_sum = timedelta()
            softtime = timedelta()
            tafb = timedelta()
            my = datetime.now()
            d = []
            checkins = []
            checkouts = []   
            
            flight_data = re.findall(r'(\d)?(?:\s+|\s+[A-Z]{2}\s+)(\w+)\s+(\w{3})\s+(\d{2}:\d{2})\s+(\w{3})\s+(\d{2}:\d{2})\s*(\d{3}:\d{2})?\s*(\w*)?\s+(\d{3}:\d{2})', pairing)

            # Extract other variables of interest

            ## From the top line pull the pairing code and the number of days of the pairing

            p_code = re.findall(r'\w\d{1,2}[A-Z]?\d{2}', pairing)
            p_code = p_code[0]

            n_days = re.findall(r'(\d+)-Day', pairing)
            n_days = int(n_days[0])

            ## Near the bottom pull both the total credit and sum of the block times and use it to calculate the soft time. Plus record time away from base

            credit_sum = re.findall(r'Credit:\s(\d{3}:\d{2})', pairing)
            credit_sum = credit_sum[0]
            hours, minutes = map(int, credit_sum.split(':'))
            credit_sum = timedelta(hours=hours, minutes=minutes)

            block_sum = re.findall(r'\w\s{40}(\d{3}:\d{2})', pairing)
            block_sum = block_sum[0]
            hours, minutes = map(int, block_sum.split(':'))
            block_sum = timedelta(hours=hours, minutes=minutes)

            softtime = credit_sum - block_sum

            tafb = re.findall(r'TAFB:\s(\d{3}:\d{2})', pairing)
            tafb = tafb[0]
            hours, minutes = map(int, tafb.split(':'))
            tafb = timedelta(hours=hours, minutes=minutes)

            credit_sum = format_timedelta(credit_sum)
            block_sum = format_timedelta(block_sum)
            softtime = format_timedelta(softtime)
            tafb = format_timedelta_alt(tafb)

            ## Here, we concern ourselves with dates. We want the dates in the calendar on the right to match with the month and year above the calendar.

            my = re.findall(r'[A-Z]{3}\s\d{4}', pairing)
            my = datetime.strptime(my[0],"%b %Y")

            d = list()
            d_list = re.findall(r'\|(\d{2})\s|\s(\d{2})\s', pairing)

            d = [int(num) for tup in d_list for num in tup if num]
            mdy = [my + timedelta(days=item-1) for item in d]

            ## Further, we want check in and checkout times to be associated with these dates.

            checkin = re.findall(r'Check-In\s(\d{2}:\d{2})', pairing)
            checkin = datetime.strptime(checkin[0], "%H:%M")
            checkins = []
            for checkin_date in mdy:
                checkin_datetime = datetime.combine(checkin_date.date(), checkin.time())
                checkins.append(checkin_datetime)

            checkout = re.findall(r'Check-Out\s(\d{2}:\d{2})', pairing)
            checkout = datetime.strptime(checkout[0], "%H:%M")
            checkouts = []
            for checkout_date in mdy:
                checkout_datetime = datetime.combine(checkout_date.date(), checkout.time()) + timedelta(days=n_days - 1)
                checkouts.append(checkout_datetime)

            ## Now all that remains is to make our table_data with all pairings. But because we want to filter by dates, we actually make an observation for each date a pairing is offered as well.

            checkinouts = []
            for item1, item2 in zip(checkins, checkouts):
                checkinouts.append((item1, item2))

            for checkinout in checkinouts:
                checkin, checkout = checkinout
                obs = pd.DataFrame([[p_code, checkin, checkout, credit_sum, softtime, n_days, block_sum, tafb, flight_data]], columns = table_columns)
                table_data = pd.concat([table_data, obs], ignore_index=True)

            table_data['flight_data'] = table_data['flight_data'].astype(str)
            data_list = table_data.to_dict(orient='records')
            output_message = f'{filename} processed successfully. {len(pairings)} found.'

        return data_list, output_message

    else: 
        # Set a default value if no file is uploaded
        # Read the JSON file
        with open('default_data.json', 'r') as file:
            serialized_data = file.read()

        # Deserialize the JSON data
        data_list = json.loads(serialized_data)

        # Create a dataframe from the data
        table_data = pd.DataFrame(data_list)
        table_data['checkin'] = pd.to_datetime(table_data['checkin'], unit='ms')
        table_data['checkout'] = pd.to_datetime(table_data['checkout'], unit='ms')
        data_list = table_data.to_dict(orient='records')

        output_message = 'Default data used.'

        return data_list, output_message

@app.callback(
    Output('datatable', 'data'),
    Input('upload-data-store', 'data'),
    Input('my-date-picker-range', 'start_date'), Input('my-date-picker-range', 'end_date'),
    Input('range-slider', 'value')
)
def filter_table(data_list, start_date, end_date, range_values):
    # Create a dataframe from the data
    table_data = pd.DataFrame(data_list)


    # Convert millisecond timestamps to datetime objects
    table_data['checkin'] = pd.to_datetime(table_data['checkin'])
    table_data['checkout'] = pd.to_datetime(table_data['checkout'])



    if range_values is not None:
        filtered_data = table_data.loc[(table_data['n_days'] >= range_values[0]) & (table_data['n_days'] <= range_values[1])]
    else:
        filtered_data = table_data.copy()  # Create a copy of the original table_data

    if start_date is not None and end_date is not None:
        start_date_object = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_object = datetime.strptime(end_date, '%Y-%m-%d')

        filtered_data['checkin'] = pd.to_datetime(filtered_data['checkin'])
        filtered_data['checkout'] = pd.to_datetime(filtered_data['checkout'])

        filtered_data = filtered_data[
            (filtered_data['checkin'].dt.date >= start_date_object.date()) &
            (filtered_data['checkout'].dt.date <= end_date_object.date())
        ]

    filtered_data.loc[:, 'checkin'] = filtered_data['checkin'].dt.strftime('%m/%d, %H:%M')
    filtered_data.loc[:, 'checkout'] = filtered_data['checkout'].dt.strftime('%m/%d, %H:%M')


    return filtered_data.to_dict('records')

@app.callback(
    Output('selected_row_store', 'data'),
    Output('selected_row_info', 'children'),
    Input('datatable', 'active_cell'),
    Input('datatable', 'data'),
    State('datatable', 'derived_virtual_indices')
)
def update_selected_row(active_cell, table_data, derived_virtual_indices):
    table_data = pd.DataFrame(table_data)
    selected_row_index = active_cell['row'] if active_cell else None
    selected_row_info = None

    if selected_row_index is not None:
        if derived_virtual_indices and selected_row_index >= len(derived_virtual_indices):
            selected_row_index = None

        if selected_row_index is not None:
            if derived_virtual_indices:
                selected_row_index = derived_virtual_indices[selected_row_index]
            else:
                selected_row_index = None

            if selected_row_index is not None:
                selected_data = table_data.iloc[selected_row_index]

                selected_p_code = selected_data['p_code']
                selected_checkin = selected_data['checkin']
                selected_checkout = selected_data['checkout']
                selected_tafb = selected_data['tafb']
                selected_credit = selected_data['credit_sum']
                selected_block = selected_data['block_sum']
                selected_soft = selected_data['softtime']

                selected_atts = f"Code: {selected_p_code}\nCheck-In: {selected_checkin} \u2014 Check-Out: {selected_checkout}\nTAFB: {selected_tafb}\nCredit: {selected_credit} - Block: {selected_block} = Soft: {selected_soft}"

                selected_table = selected_data['flight_data']
                selected_df = pd.DataFrame(eval(selected_table), columns=flight_columns)
                selected_row_table = dash_table.DataTable(
                    columns=[{"name": col, "id": col} for col in flight_columns],
                    data=selected_df.to_dict('records'),
                    style_table={'overflowX': 'auto'}
                )
                selected_row_info = [
                    html.H4('Pairing Info'),
                    html.Div(selected_atts, style={'white-space': 'pre-wrap'}),
                    html.H5('Flight Table'),
                    selected_row_table,
                ]

    return selected_row_index, selected_row_info

if __name__ == '__main__':
    app.run_server(debug=True)
