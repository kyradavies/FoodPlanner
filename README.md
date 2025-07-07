🍴 Forkcast – BBC Good Food Meal Planner App
Forkcast is an interactive web application built with Dash that allows users to:
- Search for recipes from BBC Good Food
- Select meals to create a personalized weekly planner
- Generate and download a shopping list
- Email the meal plan and shopping list to themselves

🔧 Features
🔍 Search Recipes: Enter a keyword (e.g., "beans") and the app scrapes top BBC Good Food recipes.
✅ Select Meals: Choose meals from the list to add to your weekly planner.
📅 Assign to Days: Allocate selected meals to specific days of the week.
🛒 Generate Shopping List: Automatically compile ingredients from selected recipes.
📥 Download: Export the meal planner and shopping list as CSV files.
📧 Email: Send the shopping list directly to your email.

🧪 Tech Stack
- Python
- Dash (Plotly)
- Dash AG Grid
- BeautifulSoup (for web scraping)
- Pandas
- SMTP (email sending)

✉️ Email Functionality
To send emails from the app:
Replace the from_email and app_password values in the code with your own Gmail credentials.
You must enable App Passwords in your Google account and use that password in the script.

📁 File Overview
recipe_data_collection.py – Main Dash app with all logic, callbacks, and layout
Scraper uses BBC Good Food’s public HTML structure (no API)
Shopping list and planner data stored locally in Dash Stores

📝 Future Improvements
Save meal plans per user session
Support additional websites or APIs
Ingredient categorization or tagging
Responsive mobile-friendly design
