import requests
import sys
from bs4 import BeautifulSoup
import pandas as pd
import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import uuid
from dash import callback_context  
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

today=datetime.today().strftime('%Y-%m-%d')
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
headers = {"User-Agent": "Mozilla/5.0"}

# -- Scraping functions --
def get_recipe(url):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text.strip(), "html.parser")

    try:
        title = soup.find("h1").text.strip()
    except:
        title = "Untitled"

    ingredients = [li.text.strip() for li in soup.select("ul.ingredients-list li")]

    prep, cook = None, None
    time_tags = soup.find_all("div", class_="recipe-cook-and-prep-details__item")
    for tag in time_tags:
        if "Prep" in tag.text:
            prep = tag.text.strip()
        if "Cook" in tag.text:
            cook = tag.text.strip()

    return {
        'id': str(uuid.uuid4()),  # unique ID for AG Grid
        'title': title,
        'prep_time': prep,
        'cook_time': cook,
        'ingredients': "\n".join(ingredients) if ingredients else "N/A",
        'Link':url
    }

def get_urls(query):
    base_url = "https://www.bbcgoodfood.com/search"
    all_urls = set()

    for page in range(1, 3):  # Pages 1 and 2 only
        params = {"q": query, "page": page}
        response = requests.get(base_url, params=params, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        for article in soup.select("article"):
            link = article.find("a", href=True)
            if link and "/recipes/" in link['href']:
                full_url = link['href']
                all_urls.add(full_url)

    recipe_data = []
    for url in sorted(all_urls)[:10]:
        try:
            row = get_recipe(url)
            recipe_data.append(row)
        except Exception as e:
            print(f"Error scraping {url}: {e}")
    return pd.DataFrame(recipe_data)

# -- Dash App --
app = dash.Dash(__name__,external_stylesheets=[dbc.themes.MINTY])
app.title = "Recipe Scraper"

app.layout = dbc.Container([
    dcc.Store(id="stored-results", data=[], storage_type='local'),
    dcc.Store(id="selected-store", data=[], storage_type='local'),
    dcc.Store(id="selected-ingred", data=[], storage_type='local'),
    html.H1("Forkcast",style={'display': 'flex','justifyContent': 'center'}),
    dcc.Input(id="search-input", type="text", placeholder="Enter a recipe keyword (e.g. beans)"),
    dbc.Button("Search", id="search-button", n_clicks=0, color="primary",style={'margin': '5px'}),
    html.Div(id="loading-msg", style={"marginTop": "1em", "color": "gray"}),
    html.Hr(),
    dag.AgGrid(
        id="results-table2",
        columnDefs=[],
        rowData=[],
        dashGridOptions={
            "rowSelection": "multiple",
            "suppressRowClickSelection": True,
            "singleClickEdit": True,
            "animateRows": False,
            "rememberSelected": True,
            "getRowId": {"function": "params.data.id"}
        },csvExportParams={
                "fileName": f"meal_plan_{today}.csv",
            },
         style={'width': '95%',"height": "400px"},
    ),
    html.Hr(),
    dbc.Input(id="email-input", type="email", placeholder="Enter email"),
    dbc.Button("Email me this meal planner", id="email-button-meals", n_clicks=0,style={'margin': '20px'},color='primary'),
    dbc.Button("Download meal planner", id="csv-button-meals", n_clicks=0,style={'margin': '20px'},color='primary'),
    dcc.Download(id="download-csv"),
    dbc.Button("Clear selection", id="clear-button", n_clicks=0,style={'margin': '20px'},color='primary'),
    html.Hr(),
    html.H2("Selected recipes:"),
    html.Pre(id="selected-output"),
    html.Hr(),
    html.H2("Weekly Planner:"),
    dag.AgGrid(
            id="week-grid",
            columnDefs=[{"headerName": day, "field": day, "editable": True} for day in days],
            defaultColDef={"resizable": True, "sortable": False, "filter": False},
            style={'width': '95%'},
            dashGridOptions={"domLayout": "autoHeight"}
        ),

    html.Hr(),
    html.H2("Shopping List:"),
    html.Hr(),
    dag.AgGrid(
        id="shopping-table",
        columnDefs=[],
        rowData=[],
        dashGridOptions={
            "rowSelection": "multiple",
            "suppressRowClickSelection": True,
            "animateRows": False,
            "rememberSelected": True,
            "domLayout": "autoWidth"
        },csvExportParams={
                "fileName": f"shopping_list_{today}.csv",
            },
        style={'width': '95%',"height": "400px"}
    ),html.Button("Download list", id="csv-button-list", n_clicks=0),
    html.Hr(),
   
    ],fluid=True,style={'margin': '20px'},)

# Search button → run scraper
@app.callback(
    Output("loading-msg", "children"),
    Output("results-table2", "rowData"),
    Output("results-table2", "columnDefs"),
    Input("search-button", "n_clicks"),
    State("search-input", "value"),
    prevent_initial_call=True
)
def run_scraper(n_clicks, query):
    if not query:
        return "Please enter a search term.", [], []
    msg = f"Searching BBC Good Food for '{query}'..."
    df = get_urls(query)
    df["AssignedDays"] = ""  # Add empty column initially
    if df.empty:
        return "No results found.", [], []

    columns = [{"checkboxSelection": True, "headerName": "", "width": 40}] + [
        {"field": col, "filter": True, "sortable": True} 
        for col in df.columns if col not in ["id", "AssignedDays"]  # exclude it here
        ] + [
        {
            "headerName": "Assign to Day",  # add it manually below
            "field": "AssignedDays",
            "cellEditor": "agSelectCellEditor",
            "cellEditorParams": {"values": days},
            "editable": True
        }
        ]
    return f"Showing top {len(df)} results for '{query}'.", df.to_dict("records"), columns

@app.callback(
    Output("selected-store", "data"),
    Output("selected-ingred", "data"),
    Output("results-table2", "selectedRows"),
    Input("results-table2", "selectedRows"),
    Input("clear-button", "n_clicks"),
    State("selected-store", "data"),
    State("selected-ingred", "data"),
    prevent_initial_call=True
)
def update_selection(selected_rows, clear_clicks, current_store, current_ingred):
    ctx = dash.callback_context
    triggered_id = ctx.triggered_id

    if triggered_id == "clear-button":
        return [], [], []

    if not selected_rows:
        return current_store, current_ingred, []

    existing_ids = {row['id'] for row in current_store}
    new_rows = [row for row in selected_rows if row['id'] not in existing_ids]

    new_ingred = []
    existing_ingred_ids = {row['id'] for row in current_ingred}

    for row in selected_rows:
        if row['id'] not in existing_ingred_ids and row.get('ingredients'):
            new_ingred.append(row)

    return current_store + new_rows, current_ingred + new_ingred, selected_rows

# Show selected recipe titles
@app.callback(
    Output("selected-output", "children"),
    Input("selected-store", "data")
)
def show_selected_titles(rows):
    if rows:
        return "\n".join([row["title"] for row in rows])#,[{"Meal": row["title"], **{day: "" for day in days}} for row in rows]
    return "No rows selected."#,[{"Meal":""}]

@app.callback(
    Output("stored-results", "data"),
    Input("results-table2", "cellValueChanged"),
    State("results-table2", "rowData"),
    prevent_initial_call=True
)
def update_stored_results(_, row_data):
    # Store the latest edited grid data
    return row_data


@app.callback(
    Output("shopping-table", "rowData"),
    Output("shopping-table", "columnDefs"),
    Input("selected-ingred", "data"),
    Input("selected-store", "data"),
    State("selected-ingred", "data"),

    prevent_initial_call=True)
def update_shopping_list(selected_ingred,planner_rec,current_ingred):
    if not selected_ingred:
        return [],[]

    # Flatten and deduplicate ingredients
    ingredients = []
    selected_ingred=selected_ingred+current_ingred
    for recipe in selected_ingred:
        for line in recipe.get("ingredients", "").split("\n"):
            cleaned = line.strip()
            if cleaned:
                ingredients.append(cleaned)

    unique_ingredients = sorted(set(ingredients))
    row_data = [{"Ingredient": i} for i in unique_ingredients]
    column_defs = [{'headerName': 'Ingredient', 'field': 'Ingredient'}]
    return row_data,column_defs

@app.callback(
    Output("week-grid", "rowData"),
    Input("stored-results", "data"),
    Input("clear-button", "n_clicks"),
    prevent_initial_call=True
)
def update_weekly_grid(data,clear_clicks):
    ctx = dash.callback_context
    triggered_id = ctx.triggered_id

    if triggered_id == "clear-button":
        return []
    if not data:
        return []

    # Create a dictionary with one meal per day
    week_plan = {day: "" for day in days}
    for row in data:
        day = row.get("AssignedDays", "")
        title = row.get("title", "")
        if day in days and title:
            week_plan[day] = title

    return [week_plan]


@app.callback(
    Output("download-csv", "data"),
    Input("csv-button-meals", "n_clicks"),
    State("stored-results", "data"),
    prevent_initial_call=True,
)
def download_csv(n_clicks, stored_data):
    if not stored_data:
        return dash.no_update
    
    df = pd.DataFrame(stored_data)
    csv_string = df.to_csv(index=False, encoding='utf-8-sig')  # adds BOM for Excel

    return dict(
        content=csv_string,
        filename=f"meal_plan_{today}.csv",
        type="text/csv"
    )

@app.callback(
    Output("email-button-meals", "children"),
    Input("email-button-meals", "n_clicks"),
    State("email-input", "value"),
    State('shopping-table', 'rowData'),
    prevent_initial_call=True
)
def send_email(n_clicks, recipient_email,table_data):
    if not recipient_email:
        return "Please enter an email address."

    from_email = "kyrajdavies@gmail.com"
    app_password = "bzcg talb otjl xutg"
    df_from_input = pd.DataFrame(table_data)
    html_body = df_from_input.to_html(index=False, border=1) 

    msg = MIMEText(html_body, "html")
    msg['Subject'] = "Food Planner - Week Commencing {}"
    msg['From'] = from_email
    msg['To'] = recipient_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(from_email, app_password)
            smtp.send_message(msg)
        return f"Email sent to {recipient_email}!"
    except Exception as e:
        return f"Error sending email: {str(e)}"


if __name__ == "__main__":
    app.run(debug=True)
