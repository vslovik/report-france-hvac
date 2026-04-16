from datetime import date

import pandas as pd


class Cohorts:

    # ── Single knob: update this date when new data arrives ──────────
    LAST_DATE = date(2026, 3, 31)

    # Rolling window sizes — change these to widen/narrow the report
    YEARS_TO_SHOW    = 3   # how many calendar years to include
    QUARTERS_TO_SHOW = 5   # how many quarters in quarterly comparison plots

    # Derived — do not edit manually
    YEARS       = list(range(LAST_DATE.year - YEARS_TO_SHOW + 1, LAST_DATE.year + 1))
    START_MONTH = f'{YEARS[0]}-01'
    END_MONTH   = LAST_DATE.strftime('%Y-%m')

    _YEAR_COLOR_PALETTE = ['steelblue', 'tomato', 'mediumseagreen', 'darkorange', 'purple']
    YEARS_COLORS = dict(zip(YEARS, _YEAR_COLOR_PALETTE))

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