import requests
from bs4 import BeautifulSoup
import pandas as pd
import dash
from dash import html, dcc, Input, Output, State, dash_table

headers = {"User-Agent": "Mozilla/5.0"}

# -- Scraping functions --
def get_recipe(url):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text.strip(), "html.parser")

    title = soup.find("h1").text.strip()

    ingredients = [li.text.strip() for li in soup.select("ul.ingredients-list__group li")]

    prep, cook = None, None
    time_tags = soup.find_all("div", class_="recipe-cook-and-prep-details__item")
    for tag in time_tags:
        if "Prep" in tag.text:
            prep = tag.text.strip()
        if "Cook" in tag.text:
            cook = tag.text.strip()

    return {
        'title': title,
        'prep_time': prep,
        'cook_time': cook,
        'ingredients': "\n".join(ingredients)
    }

def get_urls(query):
    base_url = "https://www.bbcgoodfood.com/search"
    all_urls = set()

    for page in range(1, 3):  # Pages 1 and 2 only (faster)
        params = {"q": query, "page": page}
        response = requests.get(base_url, params=params, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        for article in soup.select("article"):
            link = article.find("a", href=True)
            if link and "/recipes/" in link['href']:
                full_url = "https://www.bbcgoodfood.com" + link['href']
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
app = dash.Dash(__name__)
app.title = "Recipe Scraper"

app.layout = html.Div([
    html.H2("BBC Good Food Recipe Finder"),
    dcc.Input(id="search-input", type="text", placeholder="Enter a recipe keyword (e.g. beans)", style={"width": "60%"}),
    html.Button("Search", id="search-button", n_clicks=0),
    html.Div(id="loading-msg", style={"marginTop": "1em", "color": "gray"}),
    html.Hr(),
    dash_table.DataTable(
        id="results-table",
        columns=[
            {"name": "Title", "id": "title"},
            {"name": "Prep Time", "id": "prep_time"},
            {"name": "Cook Time", "id": "cook_time"},
            {"name": "Ingredients", "id": "ingredients"},
        ],
        style_cell={"whiteSpace": "pre-line", "textAlign": "left"},
        style_table={"overflowX": "auto"},
    )
], style={"maxWidth": "800px", "margin": "auto", "padding": "2em"})


@app.callback(
    Output("results-table", "data"),
    Output("loading-msg", "children"),
    Input("search-button", "n_clicks"),
    State("search-input", "value"),
    prevent_initial_call=True
)
def run_scraper(n_clicks, query):
    if not query:
        return [], "Please enter a search term."
    msg = f"Searching BBC Good Food for '{query}'..."
    df = get_urls(query)
    if df.empty:
        return [], "No results found."
    return df.to_dict("records"), f"Showing top {len(df)} results for '{query}'."

if __name__ == "__main__":
    app.run_server(debug=True)
