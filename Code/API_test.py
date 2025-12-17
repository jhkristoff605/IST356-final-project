import googlemaps

gmaps = googlemaps.Client(key="AIzaSyCTYnU0WUrcYaSe7I2a37Z4XD56-wrhj60")

geocode = gmaps.geocode("Paris, France")
print(geocode[0]["geometry"]["location"])