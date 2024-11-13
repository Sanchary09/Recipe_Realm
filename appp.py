import os
import requests
import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from PIL import Image
from fpdf import FPDF

# Load environment variables from .env file
load_dotenv()

# Database setup
DATABASE_URI = 'sqlite:///D:/Receipe_recom/Proj/recipes.db'  # Adjust path as per your setup
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

# Define the base for SQLAlchemy models
Base = declarative_base()


# User model
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)


# Recipe model
class Recipe(Base):
    __tablename__ = 'recipe'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    ingredients = Column(String)
    instructions = Column(String)
    category = Column(String)  # Ensure this line is included


# Discussion model for forum posts
class Discussion(Base):
    __tablename__ = 'discussion'
    id = Column(Integer, primary_key=True)
    username = Column(String)
    content = Column(String)
    image_url = Column(String)  # URL to the uploaded image


# Create the tables if they don't exist or alter them if necessary.
Base.metadata.create_all(engine)


# Function to retrieve all recipes
def get_recipes():
    result = session.execute(text("SELECT * FROM recipe")).fetchall()
    return [Recipe(id=row[0], title=row[1], ingredients=row[2], instructions=row[3], category=row[4]) for row in result]


# Function to add a new recipe
def add_recipe(title, ingredients, instructions, category):
    session.execute(
        text(
            "INSERT INTO recipe (title, ingredients, instructions, category) VALUES (:title, :ingredients, :instructions, :category)"),
        {'title': title, 'ingredients': ingredients, 'instructions': instructions, 'category': category}
    )
    session.commit()


# Function to update an existing recipe
def update_recipe(recipe_id, title, ingredients, instructions):
    session.execute(
        text(
            "UPDATE recipe SET title = :title, ingredients = :ingredients, instructions = :instructions WHERE id = :id"),
        {'id': recipe_id, 'title': title, 'ingredients': ingredients, 'instructions': instructions}
    )
    session.commit()


# Function to delete a recipe
def delete_recipe(recipe_id):
    session.execute(text("DELETE FROM recipe WHERE id = :id"), {'id': recipe_id})
    session.commit()


# Function to search for cooking videos on YouTube
def search_youtube(query, max_results=5):
    youtube_api_key = os.getenv('YOUTUBE_API_KEY')
    if not youtube_api_key:
        st.error("YouTube API key not found. Please set the YOUTUBE_API_KEY environment variable.")
        return []

    youtube_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'q': query + " cooking",  # Ensure "cooking" is included in the search query.
        'type': 'video',
        'key': youtube_api_key,
        'maxResults': max_results
    }

    response = requests.get(youtube_url, params=params)

    if response.status_code == 200:
        return response.json().get('items', [])

    st.error(f"Error fetching data from YouTube API: {response.status_code} - {response.text}")
    return []


# Function to generate recipe ideas using Spoonacular API
def generate_recipe_ideas(user_ingredients):
    api_key = os.getenv('SPOONACULAR_API_KEY')
    if not api_key:
        st.error("API key not found. Please set the SPOONACULAR_API_KEY environment variable.")
        return []

    url = f"https://api.spoonacular.com/recipes/findByIngredients?ingredients={user_ingredients}&apiKey={api_key}&number=5&ranking=2&ignorePantry=true"

    response = requests.get(url)

    if response.status_code != 200:
        st.error(f"Error fetching data from Spoonacular API: {response.status_code} - {response.text}")
        return []

    recipe_ids = [recipe['id'] for recipe in response.json()]

    recipe_details = []

    for recipe_id in recipe_ids:
        details_url = f"https://api.spoonacular.com/recipes/{recipe_id}/information?apiKey={api_key}"
        details_response = requests.get(details_url)
        recipe_details.append(details_response.json())

    return recipe_details


# Function to generate a certificate as a PDF file
def generate_certificate(username):
    pdf = FPDF()
    pdf.add_page()

    # Title and content for the certificate
    pdf.set_font("Arial", size=24)
    pdf.cell(200, 10, txt="Certificate of Achievement", ln=True, align='C')

    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, txt=f"This certifies that {username}", ln=True, align='C')

    pdf.cell(200, 10, txt="has successfully completed the Trivia Quiz with a score of 80% or higher.", ln=True,
             align='C')

    # Save the certificate to a file
    certificate_filename = f"{username}_certificate.pdf"

    # Save PDF file to disk temporarily before downloading.
    pdf.output(certificate_filename)


# Streamlit app setup
st.set_page_config(page_title="Recipe Recommendation App", layout="wide")

# Navigation bar
st.sidebar.title("Navigation")
page_options = ["Home", "Manage Recipes", "Recipe Ideas", "Search Videos", "Upload Image", "Trivia Quiz",
                "Discussion Forum"]
selected_page = st.sidebar.radio("Go to", page_options)

# Title and Description of the Application
st.markdown("""
## The Recipe Recommendation Application

The Recipe Recommendation Application is an innovative platform that enhances the culinary experience by enabling users to manage,
discover and explore a diverse range of recipes. The application allows users to easily add,
update and delete personalized recipes while categorizing them as vegetarian or non-vegetarian.
""")

# Home page content
if selected_page == "Home":
    st.header("Welcome to the Recipe Recommendation App!")
    # Display top cooking videos with thumbnails
    st.subheader("Top Cooking Videos")
    top_videos = search_youtube("top", max_results=5)  # Fetch top cooking videos

    if top_videos:
        for video in top_videos:
            video_title = video['snippet']['title']
            video_id = video['id']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            thumbnail_url = video['snippet']['thumbnails']['medium']['url']
            col1, col2 = st.columns(2)
            with col1:
                st.image(thumbnail_url)  # Display thumbnail with fixed width
            with col2:
                st.markdown(f"[{video_title}]({video_url})")
    else:
        st.write("No top cooking videos found.")

# Manage Recipes page
elif selected_page == "Manage Recipes":
    st.header("Manage Recipes")

    # Display all recipes and options to edit or delete them
    recipes = get_recipes()
    if recipes:
        for recipe in recipes:
            st.subheader(recipe.title)
            st.write("**Ingredients:**")
            st.write(recipe.ingredients)
            st.write("**Instructions:**")
            st.write(recipe.instructions)

            # Edit Recipe Button
            if st.button(f"Edit {recipe.title}", key=f"edit_{recipe.id}"):
                with st.form(key=f"edit_form_{recipe.id}"):
                    new_title = st.text_input("Title", value=recipe.title)
                    new_ingredients = st.text_area("Ingredients", value=recipe.ingredients)
                    new_instructions = st.text_area("Instructions", value=recipe.instructions)
                    submit_button = st.form_submit_button("Update Recipe")
                    if submit_button:
                        update_recipe(recipe.id, new_title, new_ingredients, new_instructions)
                        st.success(f"{recipe.title} updated successfully!")
                        st.experimental_rerun()  # Refresh the page

            # Delete Recipe Button
            if st.button(f"Delete {recipe.title}", key=f"delete_{recipe.id}"):
                delete_recipe(recipe.id)
                st.success(f"{recipe.title} deleted successfully!")
                st.experimental_rerun()  # Refresh the page

    # Add new recipe section at the end of the list of recipes.
    st.header("Add a New Recipe")
    with st.form(key="add_recipe_form"):
        title = st.text_input("Recipe Title")
        ingredients = st.text_area("Ingredients")
        instructions = st.text_area("Instructions")
        category_options = ["Vegetarian", "Non-Vegetarian"]
        category = st.selectbox("Category", category_options)
        add_button = st.form_submit_button("Add Recipe")
        if add_button:
            if title and ingredients and instructions:
                add_recipe(title, ingredients, instructions, category)
                st.success("Recipe added successfully!")
                st.experimental_rerun()  # Refresh the page

# Recipe Ideas page
elif selected_page == "Recipe Ideas":
    st.header("Get Recipe Ideas")
    user_ingredients = st.text_input("Enter Ingredients (separated by commas)")

    if st.button("Generate Recipe Ideas"):
        if user_ingredients:
            recipe_ideas = generate_recipe_ideas(user_ingredients)
            if recipe_ideas:
                for recipe in recipe_ideas:
                    st.subheader(recipe['title'])
                    st.write(f"**Servings**: {recipe['servings']}")
                    st.write(f"**Preparation Time**: {recipe['readyInMinutes']} minutes")
                    st.write("**Ingredients:**")
                    for ingredient in recipe['extendedIngredients']:
                        st.write(f"- {ingredient['original']}")
                    st.write("**Instructions:**")
                    if 'instructions' in recipe:
                        st.write(recipe['instructions'])
                    else:
                        st.write("No instructions available.")
                    if 'sourceUrl' in recipe:
                        st.write(f"**Source**: [View Recipe]({recipe['sourceUrl']})")
            else:
                st.write("No recipe ideas found with the given ingredients.")
        else:
            st.error("Please enter at least one ingredient.")

# Search Videos page
elif selected_page == "Search Videos":
    st.header("Search Cooking Videos")
    dish_name = st.text_input("Enter Dish Name")

    if st.button("Search"):
        if dish_name:
            youtube_results = search_youtube(dish_name)

            if youtube_results:
                for video in youtube_results:
                    video_title = video['snippet']['title']
                    video_id = video['id']['videoId']
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    thumbnail_url = video['snippet']['thumbnails']['medium']['url']

                    col1, col2 = st.columns(2)
                    with col1:
                        col1.image(thumbnail_url)  # Display thumbnail with fixed width
                    with col2:
                        col2.markdown(f"[{video_title}]({video_url})")

            else:
                matching_recipes_query_result = session.execute(text(
                    "SELECT * FROM recipe WHERE title LIKE :title"), {'title': f'%{dish_name}%'})
                matching_recipes = matching_recipes_query_result.fetchall()

                if matching_recipes:
                    for row in matching_recipes:
                        title_match = row[1]
                        ingredients_match = row[2]
                        instructions_match = row[3]

                        col1, col2 = st.columns(2)

                        with col1:
                            col1.subheader(title_match)
                            col1.write('**Ingredients:**')
                            col1.write(ingredients_match)
                            col1.write('**Instructions:**')
                            col1.write(instructions_match)

                else:
                    # If no related cooking videos or recipes found.
                    st.write("No related cooking videos or recipes found.")
        else:
            # If no dish name is entered.
            st.error("Please enter a dish name.")

# Upload image page
elif selected_page == "Upload Image":
    uploaded_file = st.file_uploader('Choose an image...', type='jpg')

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        image.thumbnail((300, 300))  # Display uploaded image.

        col1, col2 = st.columns(2)

        with col1:
            col1.image(image, captions='Uploaded Image', use_column_width=True)

        with col2:
            pass

            # Placeholder logic for prediction functionality.
        if (st.button('Predict')):
            predicted_food_item = 'Predicted Food Item'  # Placeholder prediction result
            col2.write(f'Predicted Food Item : **{predicted_food_item}**')

        # Trivia Quiz Page Implementation Below
elif selected_page == "Trivia Quiz":
    questions_and_answers = {
        "What is the main ingredient in guacamole?": "Avocado",
        "Which herb is commonly used in Italian cuisine?": "Basil",
        "What type of pasta is shaped like small rice grains?": "Orzo",
        "What is traditionally used to make hummus?": "Chickpeas",
        "Which fruit is known as the king of fruits?": "Durian"
    }

    score = 0  # To keep track of correct answers.
    total_questions = len(questions_and_answers)  # Total number of questions.

    for question, answer in questions_and_answers.items():
        user_answer = st.text_input(question)  # Get user input for each question.

        if user_answer and user_answer.lower() == answer.lower():
            score += 1  # Increment score for correct answer.

    if total_questions > 0 and score > 0:
        percentage = (score / total_questions) * 100  # Calculate percentage score.

        if percentage >= 80:
            certificate_message = f"Congratulations! You have passed the quiz with an **80%** score!"
            certificate_message += "\n\nYou are now eligible for a certificate!"

            download_button = st.download_button(label="Download Certificate",
                                                 data=f"{certificate_message}\n\n--- Certificate ---\nYour Name:\nDate:\nSignature:",
                                                 file_name="certificate.txt")
            if download_button:
                pass

        else:
            percentage_message = f"You scored **{percentage:.2f}%**, keep trying!"
            st.warning(percentage_message)

# Discussion Forum Section Implementation Below
elif selected_page == "Discussion Forum":
    st.header('Discussion Forum')

    discussion_content = []

    discussions = session.execute(text('SELECT * FROM discussion')).fetchall()

    for discussion in discussions:
        discussion_content.append(discussion[1])  # Assuming username is at index 1.
        discussion_content.append(discussion[2])  # Assuming content is at index 2.

    discussion_input = st.text_area('Share your thoughts or questions about cooking:')

    uploaded_image_for_discussion = None

    uploaded_image_for_discussion = st.file_uploader('Upload an image related to your question:', type=['jpg', 'png'])

    if (st.button('Post')):
        image_url = None

        if uploaded_image_for_discussion is not None:
            image_url = f"{uploaded_image_for_discussion.name}"  # Store image name or URL.

        session.execute(text(
            'INSERT INTO discussion (username , content , image_url ) VALUES (:username , :content , :image_url )'),
            {'username': 'User', 'content': discussion_input,
             'image_url': image_url})  # Replace 'User' with actual username.

        session.commit()

        discussion_content.append(discussion_input)

        for content in discussion_content:
            st.write(content)

# Close the session when the app ends.
session.close()