from datetime import date

import pandas as pd


class Cohorts:

    LAST_DATE = date(2026, 3, 31)

    @staticmethod
    def map_product(val) -> str:
        if pd.isna(val):
            return 'Other'
        v = str(val).upper()
        if 'HEAT_PUMP' in v:       return 'HP'
        if 'BOILER_GAS' in v:      return 'Boiler'
        if 'AIR_CONDITIONER' in v: return 'AC'
        if 'STOVE' in v:           return 'Stove'
        return 'Other'

    YEARS = [2024, 2025, 2026]

    YEARS_COLORS = {
        2024: 'steelblue',
        2025: 'tomato',
        2026: 'mediumseagreen'
    }

    QUARTERS_TO_SHOW = 5
    QUARTERS_COLORS = [
        'steelblue',
        'mediumseagreen',
        'darkorange',
        'tomato',
        'purple'
    ]

    MIN_CUSTOMERS = 50  # minimum per agency×product to plot

    MAX_WEEKS = 24

    # Focus on the 4 main diagonal segments
    MAIN_SEGMENTS = [
        'BOILER_GAS → BOILER_GAS',
        'STOVE → STOVE',
        'AIR_CONDITIONER → AIR_CONDITIONER',
        'HEAT_PUMP → HEAT_PUMP'
    ]

    MAIN_SEGMENT_MAP = {
        'BOILER_GAS': 'Boiler',
        'STOVE': 'Stove',
        'AIR_CONDITIONER': 'AC',
        'HEAT_PUMP': 'Heat Pump'
    }

    MAIN_SEGMENT_LABELS = {
        'BOILER_GAS → BOILER_GAS': 'Boiler',
        'STOVE → STOVE': 'Stove',
        'AIR_CONDITIONER → AIR_CONDITIONER': 'AC',
        'HEAT_PUMP → HEAT_PUMP': 'Heat Pump'
    }

    MAIN_SEGMENT_COLORS = {
        'BOILER_GAS → BOILER_GAS': 'steelblue',
        'STOVE → STOVE': 'tomato',
        'AIR_CONDITIONER → AIR_CONDITIONER': 'mediumseagreen',
        'HEAT_PUMP → HEAT_PUMP': 'darkorange'
    }

    # Top 4 switcher segments only
    TOP_SWITCHERS = [
        'HEAT_PUMP → OTHER',
        'OTHER → HEAT_PUMP',
        'BOILER_GAS → HEAT_PUMP',
        'HEAT_PUMP → STOVE'
    ]

    TOP_SWITCHER_COLORS = {
        'HEAT_PUMP → OTHER': 'darkorange',
        'OTHER → HEAT_PUMP': 'steelblue',
        'BOILER_GAS → HEAT_PUMP': 'mediumseagreen',
        'HEAT_PUMP → STOVE': 'tomato'
    }

    DIAGONAL_MAP = {
        'Boiler': 'BOILER_GAS → BOILER_GAS',
        'Stove': 'STOVE → STOVE',
        'AC': 'AIR_CONDITIONER → AIR_CONDITIONER',
        'HP': 'HEAT_PUMP → HEAT_PUMP'
    }

    SEGMENT_LABELS = {
        'BOILER_GAS → BOILER_GAS': 'Boiler → Boiler',
        'STOVE → STOVE': 'Stove → Stove',
        'AIR_CONDITIONER → AIR_CONDITIONER': 'AC → AC',
        'HEAT_PUMP → HEAT_PUMP': 'Heat Pump → Heat Pump',
        'HEAT_PUMP → OTHER': 'Heat Pump → Other',
        'OTHER → HEAT_PUMP': 'Other → Heat Pump',
        'BOILER_GAS → HEAT_PUMP': 'Boiler → Heat Pump',
        'HEAT_PUMP → STOVE': 'Heat Pump → Stove',
    }

    OUTPUT_DIR = "pipeline_data"