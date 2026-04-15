import pandas as pd
"""
This function builds cumulative conversion curves for each monthly cohort of users, capped by how much time has elapsed
since each cohort started.

Input parameters

df — a DataFrame where each row is a user, with columns for cohort_month, converted (0/1), and conv_week (which week 
they converted)
max_weeks — the maximum number of weeks to track conversions out to
end_month — the reference month (e.g. "today"), used to determine how much time has passed for each cohort

For each cohort month it does

- Filters the DataFrame to users who belong to that cohort month
- Skips cohorts with fewer than 5 users (too small to be meaningful)
- Caps the week range — it calculates how many months have passed since the cohort started (months_since), converts 
that to weeks (* 4), and takes the minimum of that and max_weeks. This prevents extrapolating beyond data that could
actually exist yet.
- Builds a cumulative curve — for each week from 0 to the capped max, it calculates what percentage of the cohort had 
converted by that week. This produces a monotonically increasing list of percentages.
- Appends the curve to the results list

Output
A list of lists — one curve per qualifying cohort — where each inner list contains the cumulative conversion rate
(0–100%) at each week index.
"""


def get_cohort_conversion_curves(df: pd.DataFrame, max_weeks: int, end_month: str):
    """
    Build cumulative conversion curves for each monthly cohort of users,
    capped by how much time has elapsed since each cohort started.

    Parameters
    ----------
    df : pd.DataFrame
        A DataFrame where each row is a user, with columns:
        - cohort_month : the month the user belongs to (pd.Period, monthly frequency)
        - converted    : 1 if the user converted, 0 otherwise
        - conv_week    : the week number in which the user converted
    max_weeks : int
        The maximum number of weeks to track conversions out to.
    end_month : str
        The reference month (e.g. "2024-01"), used to determine how much
        time has passed for each cohort and cap the curve accordingly.

    Returns
    -------
    list of list of float
        One curve per qualifying cohort (cohorts with fewer than 5 users are
        skipped). Each inner list contains the cumulative conversion rate
        (0–100%) at each week index, from week 0 up to the capped maximum.
    """
    months = sorted(df['cohort_month'].unique())
    month_curves = []
    for month in months:
        grp = df[df['cohort_month'] == month]
        total = len(grp)
        if total < 5:  # skip tiny monthly cohorts
            continue

        converted = grp[grp['converted'] == 1]
        months_since = (pd.Period(end_month, 'M') - month).n
        capped_weeks = min(max_weeks, months_since * 4)

        curve = []
        for week in range(capped_weeks + 1):
            curve.append((converted['conv_week'] <= week).sum() / total * 100)
        month_curves.append(curve)

    return month_curves


"""

                    month_curves = []

                    for month in year_months:
                        grp = year_df[year_df['cohort_month'] == month]
                        total = len(grp)
                        if total < 5:  # skip tiny monthly cohorts
                            continue
                        converted = grp[grp['converted'] == 1]
                        months_since = (pd.Period(self.end_month, 'M') - month).n
                        max_w = min(self.max_weeks, months_since * 4)
                        curve = []
                        for w in range(max_w + 1):
                            curve.append((converted['conv_week'] <= w).sum() / total * 100)
                        month_curves.append(curve)

                    if not month_curves:
                        continue

"""
