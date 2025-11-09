"""
Mock Data Generator

Generates realistic Dutch postcode data for testing and mocking.
Includes city names, coordinates within proper geographical bounds,
and valid Dutch postcode formats.
"""

import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PostcodeData:
    """Represents a Dutch postcode with location data"""

    postcode: str
    lat: float
    lon: float
    woonplaats: str


class DutchPostcodeGenerator:
    """
    Generate realistic Dutch postcode data.

    Dutch postcodes follow the format: 1234AB
    - 4 digits (1000-9999)
    - 2 letters (A-Z, no spaces)

    Coordinates are within Netherlands geographical bounds.
    """

    # Real Dutch cities with realistic coordinate ranges (WGS84)
    CITIES = {
        "Amsterdam": {"lat_range": (52.30, 52.40), "lon_range": (4.80, 5.00)},
        "Rotterdam": {"lat_range": (51.88, 51.95), "lon_range": (4.40, 4.58)},
        "Utrecht": {"lat_range": (52.05, 52.12), "lon_range": (5.08, 5.15)},
        "Den Haag": {"lat_range": (52.03, 52.12), "lon_range": (4.24, 4.38)},
        "Eindhoven": {"lat_range": (51.40, 51.48), "lon_range": (5.43, 5.52)},
        "Groningen": {"lat_range": (53.18, 53.24), "lon_range": (6.53, 6.61)},
        "Tilburg": {"lat_range": (51.53, 51.59), "lon_range": (5.05, 5.13)},
        "Almere": {"lat_range": (52.34, 52.41), "lon_range": (5.18, 5.29)},
        "Breda": {"lat_range": (51.56, 51.61), "lon_range": (4.74, 4.81)},
        "Nijmegen": {"lat_range": (51.81, 51.87), "lon_range": (5.83, 5.89)},
        "Enschede": {"lat_range": (52.20, 52.25), "lon_range": (6.86, 6.93)},
        "Apeldoorn": {"lat_range": (52.19, 52.24), "lon_range": (5.93, 6.01)},
        "Haarlem": {"lat_range": (52.36, 52.40), "lon_range": (4.61, 4.67)},
        "Arnhem": {"lat_range": (51.96, 52.02), "lon_range": (5.88, 5.94)},
        "Zaanstad": {"lat_range": (52.43, 52.48), "lon_range": (4.78, 4.85)},
        "Amersfoort": {"lat_range": (52.14, 52.18), "lon_range": (5.36, 5.42)},
        "Haarlemmermeer": {"lat_range": (52.28, 52.34), "lon_range": (4.65, 4.75)},
        "Zwolle": {"lat_range": (52.49, 52.54), "lon_range": (6.06, 6.12)},
        "Zoetermeer": {"lat_range": (52.05, 52.09), "lon_range": (4.48, 4.53)},
        "Leiden": {"lat_range": (52.14, 52.18), "lon_range": (4.46, 4.52)},
        "Maastricht": {"lat_range": (50.83, 50.88), "lon_range": (5.66, 5.73)},
        "Dordrecht": {"lat_range": (51.78, 51.83), "lon_range": (4.64, 4.71)},
        "Ede": {"lat_range": (52.02, 52.07), "lon_range": (5.63, 5.70)},
        "Alphen aan den Rijn": {"lat_range": (52.11, 52.15), "lon_range": (4.64, 4.68)},
        "Alkmaar": {"lat_range": (52.61, 52.65), "lon_range": (4.73, 4.78)},
        "Delft": {"lat_range": (51.99, 52.03), "lon_range": (4.34, 4.39)},
        "Deventer": {"lat_range": (52.24, 52.28), "lon_range": (6.14, 6.19)},
        "Leeuwarden": {"lat_range": (53.18, 53.23), "lon_range": (5.76, 5.82)},
        "Venlo": {"lat_range": (51.35, 51.39), "lon_range": (6.14, 6.20)},
        "Roosendaal": {"lat_range": (51.52, 51.55), "lon_range": (4.44, 4.48)},
    }

    # Netherlands geographical bounds (WGS84)
    NL_BOUNDS = {
        "lat_min": 50.75,  # South (Limburg)
        "lat_max": 53.55,  # North (Groningen)
        "lon_min": 3.36,  # West (Zeeland)
        "lon_max": 7.23,  # East (Groningen)
    }

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize generator with optional random seed.

        Args:
            seed: Random seed for reproducible data generation
        """
        if seed is not None:
            random.seed(seed)

    def generate_postcode(self, prefix: Optional[str] = None) -> str:
        """
        Generate a valid Dutch postcode.

        Args:
            prefix: Optional 4-digit prefix (e.g., "1012")

        Returns:
            Valid Dutch postcode (e.g., "1012AB")
        """
        if prefix:
            if len(prefix) != 4 or not prefix.isdigit():
                raise ValueError("Prefix must be 4 digits")
            area = prefix
        else:
            area = str(random.randint(1000, 9999))

        letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
        return f"{area}{letters}"

    def generate_coordinates(
        self, city: Optional[str] = None
    ) -> Tuple[float, float]:
        """
        Generate realistic coordinates within Netherlands or specific city.

        Args:
            city: Optional city name to generate coordinates for

        Returns:
            Tuple of (latitude, longitude) in WGS84 format
        """
        if city and city in self.CITIES:
            bounds = self.CITIES[city]
            lat = random.uniform(*bounds["lat_range"])
            lon = random.uniform(*bounds["lon_range"])
        else:
            # Random location within Netherlands
            lat = random.uniform(self.NL_BOUNDS["lat_min"], self.NL_BOUNDS["lat_max"])
            lon = random.uniform(self.NL_BOUNDS["lon_min"], self.NL_BOUNDS["lon_max"])

        return round(lat, 6), round(lon, 6)

    def generate_city(self) -> str:
        """
        Generate a random Dutch city name.

        Returns:
            City name from predefined list
        """
        return random.choice(list(self.CITIES.keys()))

    def generate_single(
        self, postcode: Optional[str] = None, city: Optional[str] = None
    ) -> PostcodeData:
        """
        Generate a single postcode entry.

        Args:
            postcode: Optional specific postcode to use
            city: Optional specific city to use

        Returns:
            PostcodeData object with all fields populated
        """
        if not city:
            city = self.generate_city()

        if not postcode:
            postcode = self.generate_postcode()

        lat, lon = self.generate_coordinates(city)

        return PostcodeData(
            postcode=postcode, lat=lat, lon=lon, woonplaats=city
        )

    def generate_batch(
        self, count: int, cities: Optional[List[str]] = None
    ) -> List[PostcodeData]:
        """
        Generate a batch of postcode entries.

        Args:
            count: Number of entries to generate
            cities: Optional list of cities to limit generation to

        Returns:
            List of PostcodeData objects
        """
        postcodes = []
        used_postcodes = set()

        target_cities = cities if cities else list(self.CITIES.keys())

        for _ in range(count):
            # Ensure unique postcodes
            max_attempts = 100
            for _ in range(max_attempts):
                city = random.choice(target_cities)
                postcode = self.generate_postcode()

                if postcode not in used_postcodes:
                    used_postcodes.add(postcode)
                    break

            lat, lon = self.generate_coordinates(city)

            postcodes.append(
                PostcodeData(
                    postcode=postcode, lat=lat, lon=lon, woonplaats=city
                )
            )

        return postcodes

    def generate_for_city(self, city: str, count: int) -> List[PostcodeData]:
        """
        Generate postcodes for a specific city.

        Args:
            city: City name
            count: Number of postcodes to generate

        Returns:
            List of PostcodeData objects for the specified city
        """
        if city not in self.CITIES:
            raise ValueError(f"Unknown city: {city}. Must be one of {list(self.CITIES.keys())}")

        return self.generate_batch(count, cities=[city])

    def generate_postcode_range(
        self, start_area: int, end_area: int, postcodes_per_area: int = 5
    ) -> List[PostcodeData]:
        """
        Generate postcodes for a range of area codes.

        Args:
            start_area: Starting area code (e.g., 1000)
            end_area: Ending area code (e.g., 1099)
            postcodes_per_area: Number of postcodes per area code

        Returns:
            List of PostcodeData objects
        """
        postcodes = []

        for area in range(start_area, end_area + 1):
            prefix = str(area)
            for _ in range(postcodes_per_area):
                postcode = self.generate_postcode(prefix)
                city = self.generate_city()
                lat, lon = self.generate_coordinates(city)

                postcodes.append(
                    PostcodeData(
                        postcode=postcode, lat=lat, lon=lon, woonplaats=city
                    )
                )

        return postcodes

    def to_dict(self, data: PostcodeData) -> Dict:
        """
        Convert PostcodeData to dictionary.

        Args:
            data: PostcodeData object

        Returns:
            Dictionary representation
        """
        return {
            "postcode": data.postcode,
            "lat": data.lat,
            "lon": data.lon,
            "woonplaats": data.woonplaats,
        }

    def to_dict_list(self, data_list: List[PostcodeData]) -> List[Dict]:
        """
        Convert list of PostcodeData to list of dictionaries.

        Args:
            data_list: List of PostcodeData objects

        Returns:
            List of dictionaries
        """
        return [self.to_dict(data) for data in data_list]


class CoordinateGenerator:
    """Generate coordinates within specific geographical bounds"""

    @staticmethod
    def netherlands_bounds() -> Dict[str, float]:
        """Get Netherlands geographical bounds"""
        return {
            "lat_min": 50.75,
            "lat_max": 53.55,
            "lon_min": 3.36,
            "lon_max": 7.23,
        }

    @staticmethod
    def random_in_bounds(
        lat_min: float, lat_max: float, lon_min: float, lon_max: float
    ) -> Tuple[float, float]:
        """
        Generate random coordinates within specified bounds.

        Args:
            lat_min: Minimum latitude
            lat_max: Maximum latitude
            lon_min: Minimum longitude
            lon_max: Maximum longitude

        Returns:
            Tuple of (latitude, longitude)
        """
        lat = random.uniform(lat_min, lat_max)
        lon = random.uniform(lon_min, lon_max)
        return round(lat, 6), round(lon, 6)

    @staticmethod
    def offset_coordinates(
        lat: float, lon: float, max_offset_km: float = 1.0
    ) -> Tuple[float, float]:
        """
        Generate coordinates offset from a base point.

        Args:
            lat: Base latitude
            lon: Base longitude
            max_offset_km: Maximum offset in kilometers

        Returns:
            Tuple of (latitude, longitude) offset from base
        """
        # Rough approximation: 1 degree ≈ 111 km
        max_offset_deg = max_offset_km / 111.0

        lat_offset = random.uniform(-max_offset_deg, max_offset_deg)
        lon_offset = random.uniform(-max_offset_deg, max_offset_deg)

        new_lat = lat + lat_offset
        new_lon = lon + lon_offset

        return round(new_lat, 6), round(new_lon, 6)
