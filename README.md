# IST356-final-project
This final project is a travel-planning application designed to support users in organizing a customized European vacation. The tool is structured into two primary components, each serving a distinct function within the trip-planning process.

The first component allows users to build a travel route by selecting multiple cities or destinations they plan to visit. As users add locations, the application constructs a complete route. Upon completion, the program generates an interactive map visualizing the full itinerary and provides a downloadable CSV file containing all selected destinations, enabling users to save, review, or further analyze their travel plans.

The second component focuses on in-city exploration. Users enter a selected city, after which a set of category filters (such as restaurants, landmarks, or attractions) becomes available. An interactive city map is displayed, allowing users to pan and zoom to explore points of interest. When a category is selected, the map dynamically filters results to show only relevant locations within that city. Users may save individual places of interest, creating a personalized list. Once finished, the application generates a downloadable file containing all saved locations.

Together, these two components provide an end-to-end travel-planning solution that integrates route creation, geographic visualization, interactive filtering, and data export to support informed and organized travel decision-making.

Acknowledgment

This project was developed as part of an academic assignment by a student at Syracuse University. Certain components of the repository draw upon instructional materials provided through the course, as well as guidance and code assistance generated using Gemini AI within the Visual Studio Code environment. While external resources informed aspects of the implementation, the overall design, integration, and final output of the project represent the student’s original work.


### Requirements

The packages necessary to run the code here are found in `requirements.txt` install using `pip` or `uv`as follows:

1. From VS Code, open a terminal: menu => Terminal => New Terminal
2. In the terminal, enter `uv pip install -r requirements.txt`
3. Alternatively `uv pip install --system -r requirements.txt`
4. for mac users  `uv pip install -r requirements.txt --system --python=3.11`
