import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="West Ham United - Football Analytics",
    page_icon="⚽",
    layout="wide",
)

DATA_DIR = Path(__file__).parent / "VDS2526 Football"

OUR_TEAM_API_ID = 8654
OUR_TEAM_NAME = "West Ham United"
EPL_LEAGUE_ID = 1729


@st.cache_data
def load_data():
    match = pd.read_csv(DATA_DIR / "Match.csv")
    player = pd.read_csv(DATA_DIR / "Player.csv")
    player_attr = pd.read_csv(DATA_DIR / "Player_Attributes.csv")
    team = pd.read_csv(DATA_DIR / "Team.csv")
    league = pd.read_csv(DATA_DIR / "League.csv")
    pos_ref = pd.read_csv(DATA_DIR / "PositionReference.csv")
    match_goals = pd.read_csv(DATA_DIR / "Match_Goals.csv")
    match_poss = pd.read_csv(DATA_DIR / "Match_Possesion.csv")
    match_cards = pd.read_csv(DATA_DIR / "Match_Cards.csv")
    match_shots_on = pd.read_csv(DATA_DIR / "Match_Shots_On.csv")
    match_shots_off = pd.read_csv(DATA_DIR / "Match_Shots_Off.csv")
    return {
        "match": match,
        "player": player,
        "player_attr": player_attr,
        "team": team,
        "league": league,
        "pos_ref": pos_ref,
        "match_goals": match_goals,
        "match_poss": match_poss,
        "match_cards": match_cards,
        "match_shots_on": match_shots_on,
        "match_shots_off": match_shots_off,
    }


data = load_data()
match = data["match"]
player = data["player"]
player_attr = data["player_attr"]
team = data["team"]
pos_ref = data["pos_ref"]
match_goals = data["match_goals"]
match_poss = data["match_poss"]
match_cards = data["match_cards"]
match_shots_on = data["match_shots_on"]
match_shots_off = data["match_shots_off"]

team_id_to_name = dict(zip(team["team_api_id"], team["team_long_name"]))

epl_matches = match[match["league_id"] == EPL_LEAGUE_ID].copy()

wh_matches = epl_matches[
    (epl_matches["home_team_api_id"] == OUR_TEAM_API_ID)
    | (epl_matches["away_team_api_id"] == OUR_TEAM_API_ID)
].copy()


def get_match_result(row):
    if row["home_team_api_id"] == OUR_TEAM_API_ID:
        our_goals = row["home_team_goal"]
        their_goals = row["away_team_goal"]
    else:
        our_goals = row["away_team_goal"]
        their_goals = row["home_team_goal"]
    if our_goals > their_goals:
        return "Win"
    elif our_goals < their_goals:
        return "Loss"
    return "Draw"


def get_opponent(row):
    if row["home_team_api_id"] == OUR_TEAM_API_ID:
        return team_id_to_name.get(row["away_team_api_id"], "Unknown")
    return team_id_to_name.get(row["home_team_api_id"], "Unknown")


wh_matches["result"] = wh_matches.apply(get_match_result, axis=1)
wh_matches["opponent"] = wh_matches.apply(get_opponent, axis=1)
wh_matches["venue"] = wh_matches.apply(
    lambda r: "Home" if r["home_team_api_id"] == OUR_TEAM_API_ID else "Away", axis=1
)
wh_matches["our_goals"] = wh_matches.apply(
    lambda r: r["home_team_goal"]
    if r["home_team_api_id"] == OUR_TEAM_API_ID
    else r["away_team_goal"],
    axis=1,
)
wh_matches["their_goals"] = wh_matches.apply(
    lambda r: r["away_team_goal"]
    if r["home_team_api_id"] == OUR_TEAM_API_ID
    else r["home_team_goal"],
    axis=1,
)
wh_matches["goal_diff"] = wh_matches["our_goals"] - wh_matches["their_goals"]


def get_latest_rating(player_api_id):
    pa = player_attr[player_attr["player_api_id"] == player_api_id]
    if pa.empty:
        return None, None
    pa = pa.sort_values("date", ascending=False)
    return pa.iloc[0]["overall_rating"], pa.iloc[0]["potential"]


def get_season_rating(player_api_id, season):
    pa = player_attr[player_attr["player_api_id"] == player_api_id].copy()
    if pa.empty:
        return None
    pa["date"] = pd.to_datetime(pa["date"])
    start_year = int(season.split("/")[0])
    season_start = pd.Timestamp(f"{start_year}-07-01")
    season_end = pd.Timestamp(f"{start_year + 1}-06-30")
    season_pa = pa[(pa["date"] >= season_start) & (pa["date"] <= season_end)]
    if season_pa.empty:
        return None
    return season_pa.sort_values("date", ascending=False).iloc[0]["overall_rating"]


def get_wh_players_for_season(season):
    season_matches = wh_matches[wh_matches["season"] == season]
    player_ids = set()
    for _, row in season_matches.iterrows():
        if row["home_team_api_id"] == OUR_TEAM_API_ID:
            prefix = "home_player_"
        else:
            prefix = "away_player_"
        for i in range(1, 12):
            pid = row.get(f"{prefix}{i}")
            if pd.notna(pid):
                player_ids.add(int(pid))
    return player_ids


def get_player_position(player_api_id, season):
    season_matches = wh_matches[wh_matches["season"] == season]
    positions = []
    for _, row in season_matches.iterrows():
        if row["home_team_api_id"] == OUR_TEAM_API_ID:
            prefix_p = "home_player_"
            prefix_x = "home_player_X"
            prefix_y = "home_player_Y"
        else:
            prefix_p = "away_player_"
            prefix_x = "away_player_X"
            prefix_y = "away_player_Y"
        for i in range(1, 12):
            if row.get(f"{prefix_p}{i}") == player_api_id:
                px_val = row.get(f"{prefix_x}{i}")
                py_val = row.get(f"{prefix_y}{i}")
                if pd.notna(px_val) and pd.notna(py_val):
                    match_pos = pos_ref[
                        (pos_ref["player_pos_x"] == int(px_val))
                        & (pos_ref["player_pos_y"] == int(py_val))
                    ]
                    if not match_pos.empty:
                        positions.append(match_pos.iloc[0]["role_xy"])
    if not positions:
        return "Unknown"
    from collections import Counter

    return Counter(positions).most_common(1)[0][0]


def classify_position(pos):
    if pos == "GK":
        return "GK"
    if pos in ("LB", "RB", "CB", "LWB", "RWB", "SW"):
        return "DEF"
    if pos in ("LM", "RM", "CM", "DM", "AM"):
        return "MID"
    if pos in ("LW", "RW", "CF", "SS"):
        return "ATK"
    return "Unknown"



st.sidebar.title("West Ham United Analytics")
page = st.sidebar.radio(
    "Navigate",
    [
        "Introduction",
        "Q1: Which Players Help Us Win?",
        "Q2: Possession & Winning",
        "Q3: Threatening Teams",
    ],
)


if page == "Introduction":
    st.title("West Ham United - Football Data Analytics")
    st.markdown(
        """
    As managers of **West Ham United**, we analyse European football data (2008/09 – 2015/16)
    to determine our strategy for the next season. We answer three guiding questions:

    1. **Which players increase our chances of winning matches?**
    2. **How does possession affect winning?**
    3. **Which teams pose a threat and which do we have most/least trouble with?**
    """
    )

    col1, col2 = st.columns(2)

    # League Standings Bar Chart
    with col1:
        st.subheader("League Standings for West Ham United")
        standings_data = []
        for season in sorted(wh_matches["season"].unique()):
            season_epl = epl_matches[epl_matches["season"] == season]
            teams_in_season = set(season_epl["home_team_api_id"].unique()) | set(
                season_epl["away_team_api_id"].unique()
            )
            team_points = {}
            team_gd = {}
            for t in teams_in_season:
                t_matches = season_epl[
                    (season_epl["home_team_api_id"] == t)
                    | (season_epl["away_team_api_id"] == t)
                ]
                points = 0
                gd = 0
                for _, r in t_matches.iterrows():
                    if r["home_team_api_id"] == t:
                        gf, ga = r["home_team_goal"], r["away_team_goal"]
                    else:
                        gf, ga = r["away_team_goal"], r["home_team_goal"]
                    gd += gf - ga
                    if gf > ga:
                        points += 3
                    elif gf == ga:
                        points += 1
                team_points[t] = points
                team_gd[t] = gd
            sorted_teams = sorted(
                teams_in_season, key=lambda t: (team_points[t], team_gd[t]), reverse=True
            )
            if OUR_TEAM_API_ID in sorted_teams:
                standing = sorted_teams.index(OUR_TEAM_API_ID) + 1
                standings_data.append(
                    {"Season": season, "Standing": standing, "21 - Standing": 21 - standing}
                )

        if standings_data:
            df_standings = pd.DataFrame(standings_data)
            fig = px.bar(
                df_standings,
                x="Season",
                y="21 - Standing",
                text="Standing",
                title="League Standings for West Ham United",
                color_discrete_sequence=["#1f77b4"],
            )
            fig.update_traces(texttemplate="%{text}th", textposition="outside")
            fig.update_layout(yaxis_title="21 - Standing (higher is better)", yaxis_range=[0, 20])
            st.plotly_chart(fig, use_container_width=True)

    # Match record summary
    with col2:
        st.subheader("Overall Match Record")
        result_counts = wh_matches["result"].value_counts()
        fig = px.pie(
            values=result_counts.values,
            names=result_counts.index,
            title="West Ham United Match Outcomes (All Seasons)",
            color=result_counts.index,
            color_discrete_map={"Win": "#2ecc71", "Draw": "#f39c12", "Loss": "#e74c3c"},
        )
        st.plotly_chart(fig, use_container_width=True)

    # Player ratings comparison
    st.subheader("Player Ratings: West Ham vs Manchester City (2015/2016)")
    col1, col2 = st.columns(2)

    wh_players_1516 = get_wh_players_for_season("2015/2016")
    mc_id = 8456
    mc_matches_1516 = epl_matches[
        (epl_matches["season"] == "2015/2016")
        & (
            (epl_matches["home_team_api_id"] == mc_id)
            | (epl_matches["away_team_api_id"] == mc_id)
        )
    ]
    mc_players_1516 = set()
    for _, row in mc_matches_1516.iterrows():
        prefix = "home_player_" if row["home_team_api_id"] == mc_id else "away_player_"
        for i in range(1, 12):
            pid = row.get(f"{prefix}{i}")
            if pd.notna(pid):
                mc_players_1516.add(int(pid))

    with col1:
        wh_ratings = []
        for pid in wh_players_1516:
            r = get_season_rating(pid, "2015/2016")
            if r is not None:
                wh_ratings.append(r)
        if wh_ratings:
            mean_r = np.mean(wh_ratings)
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=wh_ratings, nbinsx=20, marker_color="#1f77b4"))
            fig.add_vline(x=mean_r, line_dash="dash", line_color="red", annotation_text=f"Mean = {mean_r:.2f}")
            fig.update_layout(
                title="Player Ratings - West Ham United (2015/16)",
                xaxis_title="FIFA Rating",
                yaxis_title="Frequency",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        mc_ratings = []
        for pid in mc_players_1516:
            r = get_season_rating(pid, "2015/2016")
            if r is not None:
                mc_ratings.append(r)
        if mc_ratings:
            mean_r = np.mean(mc_ratings)
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=mc_ratings, nbinsx=20, marker_color="#ff7f0e"))
            fig.add_vline(x=mean_r, line_dash="dash", line_color="red", annotation_text=f"Mean = {mean_r:.2f}")
            fig.update_layout(
                title="Player Ratings - Manchester City (2015/16)",
                xaxis_title="FIFA Rating",
                yaxis_title="Frequency",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Player roster table
    st.subheader("West Ham United Squad (2015/2016)")
    roster_data = []
    for pid in wh_players_1516:
        p = player[player["player_api_id"] == pid]
        if p.empty:
            continue
        p = p.iloc[0]
        rating, potential = get_latest_rating(pid)
        pos = get_player_position(pid, "2015/2016")
        roster_data.append(
            {
                "Name": p["player_name"],
                "Rating": rating,
                "Potential": potential,
                "Position": pos,
            }
        )
    df_roster = pd.DataFrame(roster_data).dropna(subset=["Rating"])
    df_roster = df_roster.sort_values("Rating", ascending=False).reset_index(drop=True)
    st.dataframe(df_roster, use_container_width=True)



elif page == "Q1: Which Players Help Us Win?":
    st.title("Q1: Which Players Increase Our Chances of Winning?")

    season_filter = st.sidebar.selectbox(
        "Season",
        ["All Seasons"] + sorted(wh_matches["season"].unique()),
        index=0,
    )

    if season_filter == "All Seasons":
        filtered_matches = wh_matches
    else:
        filtered_matches = wh_matches[wh_matches["season"] == season_filter]

    #  Task 1.6: Average Starting XI Rating vs Win Rate
    st.subheader("Average Starting XI Rating vs Win Rate")
    st.caption("Do higher-rated starting lineups correlate with more wins?")

    rating_win_data = []
    for _, row in filtered_matches.iterrows():
        if row["home_team_api_id"] == OUR_TEAM_API_ID:
            prefix = "home_player_"
        else:
            prefix = "away_player_"
        ratings = []
        for i in range(1, 12):
            pid = row.get(f"{prefix}{i}")
            if pd.notna(pid):
                pa = player_attr[player_attr["player_api_id"] == int(pid)]
                if not pa.empty:
                    pa = pa.sort_values("date", ascending=False)
                    r = pa.iloc[0]["overall_rating"]
                    if pd.notna(r):
                        ratings.append(r)
        if len(ratings) >= 8:
            avg_rating = np.mean(ratings)
            win_val = 1 if row["result"] == "Win" else (0.5 if row["result"] == "Draw" else 0)
            rating_win_data.append(
                {
                    "avg_rating": avg_rating,
                    "win_val": win_val,
                    "result": row["result"],
                    "season": row["season"],
                    "opponent": row["opponent"],
                }
            )

    if rating_win_data:
        df_rw = pd.DataFrame(rating_win_data)
        bins = pd.cut(df_rw["avg_rating"], bins=8)
        binned = df_rw.groupby(bins, observed=False)["win_val"].mean().reset_index()
        binned.columns = ["Rating Bin", "Win Rate"]
        binned["Rating Bin"] = binned["Rating Bin"].astype(str)

        fig = px.scatter(
            df_rw,
            x="avg_rating",
            y="win_val",
            color="result",
            color_discrete_map={"Win": "#2ecc71", "Draw": "#f39c12", "Loss": "#e74c3c"},
            title="Average Starting XI Rating vs Match Outcome",
            labels={"avg_rating": "Average FIFA Rating of Starting XI", "win_val": "Win Value (1=Win, 0.5=Draw, 0=Loss)"},
            hover_data=["opponent", "season"],
            trendline="ols",
        )
        st.plotly_chart(fig, use_container_width=True)

    #  Task 1.7: Top Players by Win Contribution
    st.subheader("Top Players by Win Contribution")
    st.caption("Which players appear most often in our winning matches?")

    player_win_data = {}
    player_total_data = {}
    player_position_cache = {}

    for _, row in filtered_matches.iterrows():
        if row["home_team_api_id"] == OUR_TEAM_API_ID:
            prefix_p = "home_player_"
            prefix_x = "home_player_X"
            prefix_y = "home_player_Y"
        else:
            prefix_p = "away_player_"
            prefix_x = "away_player_X"
            prefix_y = "away_player_Y"

        for i in range(1, 12):
            pid = row.get(f"{prefix_p}{i}")
            if pd.notna(pid):
                pid = int(pid)
                player_total_data[pid] = player_total_data.get(pid, 0) + 1
                if row["result"] == "Win":
                    player_win_data[pid] = player_win_data.get(pid, 0) + 1

                if pid not in player_position_cache:
                    px_val = row.get(f"{prefix_x}{i}")
                    py_val = row.get(f"{prefix_y}{i}")
                    if pd.notna(px_val) and pd.notna(py_val):
                        mp = pos_ref[
                            (pos_ref["player_pos_x"] == int(px_val))
                            & (pos_ref["player_pos_y"] == int(py_val))
                        ]
                        if not mp.empty:
                            player_position_cache[pid] = mp.iloc[0]["role_xy"]

    win_contrib = []
    for pid, total in player_total_data.items():
        if total >= 5:
            wins = player_win_data.get(pid, 0)
            p = player[player["player_api_id"] == pid]
            name = p.iloc[0]["player_name"] if not p.empty else f"Player {pid}"
            pos = player_position_cache.get(pid, "Unknown")
            pos_group = classify_position(pos)
            win_contrib.append(
                {
                    "Player": name,
                    "Win %": round(100 * wins / total, 1),
                    "Matches": total,
                    "Wins": wins,
                    "Position": pos,
                    "Position Group": pos_group,
                }
            )

    if win_contrib:
        df_wc = pd.DataFrame(win_contrib).sort_values("Win %", ascending=True).tail(20)
        fig = px.bar(
            df_wc,
            y="Player",
            x="Win %",
            color="Position Group",
            orientation="h",
            title="Top 20 Players by Win % (min 5 appearances)",
            color_discrete_map={"ATK": "#e74c3c", "MID": "#f39c12", "DEF": "#2ecc71", "GK": "#3498db", "Unknown": "#95a5a6"},
            hover_data=["Matches", "Wins", "Position"],
        )
        fig.update_layout(yaxis_title="", height=600)
        st.plotly_chart(fig, use_container_width=True)

    #  Task 1.4: Key Player Absence Effect
    st.subheader("Key Player Absence Effect")
    st.caption("Win rate when a key player is present vs absent in the starting XI")

    key_player_data = []
    for pid, total in player_total_data.items():
        if total >= 10:
            wins_present = player_win_data.get(pid, 0)
            absent_matches = filtered_matches[~filtered_matches["id"].isin(
                filtered_matches.apply(
                    lambda r: r["id"]
                    if pid
                    in [
                        r.get(f"{'home_player_' if r['home_team_api_id'] == OUR_TEAM_API_ID else 'away_player_'}{i}")
                        for i in range(1, 12)
                        if pd.notna(r.get(f"{'home_player_' if r['home_team_api_id'] == OUR_TEAM_API_ID else 'away_player_'}{i}"))
                    ]
                    else None,
                    axis=1,
                ).dropna()
            )]
            absent_total = len(absent_matches)
            absent_wins = len(absent_matches[absent_matches["result"] == "Win"])
            if absent_total >= 3:
                p = player[player["player_api_id"] == pid]
                name = p.iloc[0]["player_name"] if not p.empty else f"Player {pid}"
                key_player_data.append(
                    {
                        "Player": name,
                        "Present Win %": round(100 * wins_present / total, 1),
                        "Absent Win %": round(100 * absent_wins / absent_total, 1) if absent_total > 0 else 0,
                        "Present Matches": total,
                        "Absent Matches": absent_total,
                    }
                )

    if key_player_data:
        df_kp = pd.DataFrame(key_player_data)
        df_kp["Impact"] = df_kp["Present Win %"] - df_kp["Absent Win %"]
        df_kp = df_kp.sort_values("Impact", ascending=False).head(10)
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                name="Present",
                y=df_kp["Player"],
                x=df_kp["Present Win %"],
                orientation="h",
                marker_color="#2ecc71",
                text=df_kp["Present Matches"].apply(lambda x: f"({x} matches)"),
            )
        )
        fig.add_trace(
            go.Bar(
                name="Absent",
                y=df_kp["Player"],
                x=df_kp["Absent Win %"],
                orientation="h",
                marker_color="#e74c3c",
                text=df_kp["Absent Matches"].apply(lambda x: f"({x} matches)"),
            )
        )
        fig.update_layout(
            barmode="group",
            title="Win Rate: Player Present vs Absent (Top 10 Impact)",
            xaxis_title="Win %",
            yaxis_title="",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    #  Task 1.5: Goals & Assists by Top Contributors
    st.subheader("Top Offensive Contributors")
    st.caption("Players with the most goals and assists per season")

    goal_data = {}
    for _, row in filtered_matches.iterrows():
        match_id = row["id"]
        mg = match_goals[match_goals["match_id"] == match_id]
        for _, g in mg.iterrows():
            if g.get("goal") == "y" or (pd.notna(g.get("goal")) and str(g["goal"]).lower() in ("y", "yes", "true", "1")):
                scorer = g.get("player1")
                assister = g.get("player2")
                is_our_team = g.get("team") == OUR_TEAM_API_ID
                if is_our_team and pd.notna(scorer):
                    scorer = int(scorer)
                    if scorer not in goal_data:
                        goal_data[scorer] = {"goals": 0, "assists": 0}
                    goal_data[scorer]["goals"] += 1
                if is_our_team and pd.notna(assister):
                    assister = int(assister)
                    if assister not in goal_data:
                        goal_data[assister] = {"goals": 0, "assists": 0}
                    goal_data[assister]["assists"] += 1

    if not goal_data:
        for _, row in filtered_matches.iterrows():
            if row["our_goals"] > 0:
                match_id = row["id"]
                mg = match_goals[match_goals["match_id"] == match_id]
                our_team_id = OUR_TEAM_API_ID
                our_goals_events = mg[mg["team"] == our_team_id]
                for _, g in our_goals_events.iterrows():
                    scorer = g.get("player1")
                    assister = g.get("player2")
                    if pd.notna(scorer):
                        scorer = int(scorer)
                        if scorer not in goal_data:
                            goal_data[scorer] = {"goals": 0, "assists": 0}
                        goal_data[scorer]["goals"] += 1
                    if pd.notna(assister):
                        assister = int(assister)
                        if assister not in goal_data:
                            goal_data[assister] = {"goals": 0, "assists": 0}
                        goal_data[assister]["assists"] += 1

    contrib_rows = []
    for pid, stats in goal_data.items():
        p = player[player["player_api_id"] == pid]
        name = p.iloc[0]["player_name"] if not p.empty else f"Player {pid}"
        contrib_rows.append(
            {"Player": name, "Goals": stats["goals"], "Assists": stats["assists"]}
        )
    if contrib_rows:
        df_contrib = pd.DataFrame(contrib_rows)
        df_contrib["Total"] = df_contrib["Goals"] + df_contrib["Assists"]
        df_contrib = df_contrib.sort_values("Total", ascending=False).head(15)
        fig = go.Figure()
        fig.add_trace(
            go.Bar(name="Goals", x=df_contrib["Player"], y=df_contrib["Goals"], marker_color="#f1c40f")
        )
        fig.add_trace(
            go.Bar(name="Assists", x=df_contrib["Player"], y=df_contrib["Assists"], marker_color="#2ecc71")
        )
        fig.update_layout(
            barmode="stack",
            title="Top 15 Offensive Contributors (Goals + Assists)",
            xaxis_title="",
            yaxis_title="Count",
            xaxis_tickangle=-45,
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No goal event data available for the selected season filter.")

    #  Task 1.2: Player Performance Radar Chart
    st.subheader("Player Performance Radar Chart")
    st.caption("Compare multiple players across key attributes")

    sel_season = season_filter if season_filter != "All Seasons" else "2015/2016"
    season_players = get_wh_players_for_season(sel_season)
    player_names_map = {}
    for pid in season_players:
        p = player[player["player_api_id"] == pid]
        if not p.empty:
            player_names_map[p.iloc[0]["player_name"]] = pid

    selected_players = st.multiselect(
        "Select players to compare",
        sorted(player_names_map.keys()),
        default=sorted(player_names_map.keys())[:3],
    )

    if selected_players:
        fig = go.Figure()
        categories = ["Overall Rating", "Goals/Match", "Assists/Match", "Shots on Target/Match", "Discipline"]

        for pname in selected_players:
            pid = player_names_map[pname]
            rating = get_season_rating(pid, sel_season) or 0
            total_matches = player_total_data.get(pid, 1)

            p_goals_data = goal_data.get(pid, {"goals": 0, "assists": 0})
            goals_pm = p_goals_data["goals"] / max(total_matches, 1)
            assists_pm = p_goals_data["assists"] / max(total_matches, 1)

            shots = match_shots_on[match_shots_on["player1"] == pid]
            shots_pm = len(shots) / max(total_matches, 1)

            cards = match_cards[match_cards["player1"] == pid]
            discipline = max(0, 10 - len(cards) / max(total_matches, 1) * 10)

            rating_norm = rating / 100 * 10 if rating else 0
            goals_norm = min(goals_pm * 20, 10)
            assists_norm = min(assists_pm * 20, 10)
            shots_norm = min(shots_pm * 5, 10)

            values = [rating_norm, goals_norm, assists_norm, shots_norm, discipline]
            values.append(values[0])
            cats = categories + [categories[0]]

            fig.add_trace(
                go.Scatterpolar(r=values, theta=cats, fill="toself", name=pname)
            )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
            title="Player Performance Comparison",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    #  Task 1.3: Most Improved Young Players
    st.subheader("Most Improved Young Players")
    st.caption("Young (< 25), non-star players (rating < 85) with the biggest rating improvement")

    improved = []
    for pid in get_wh_players_for_season("2015/2016"):
        p = player[player["player_api_id"] == pid]
        if p.empty:
            continue
        birthday = pd.to_datetime(p.iloc[0]["birthday"])
        age = 2016 - birthday.year
        if age >= 25:
            continue
        r_new = get_season_rating(pid, "2015/2016")
        r_old = get_season_rating(pid, "2014/2015")
        if r_new is None or r_old is None or r_new >= 85:
            continue
        improved.append(
            {
                "Player": p.iloc[0]["player_name"],
                "Age": age,
                "2014/15 Rating": r_old,
                "2015/16 Rating": r_new,
                "Improvement": r_new - r_old,
            }
        )

    if improved:
        df_imp = pd.DataFrame(improved).sort_values("Improvement", ascending=False).head(10)
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                name="2014/15",
                x=df_imp["Player"],
                y=df_imp["2014/15 Rating"],
                marker_color="#95a5a6",
            )
        )
        fig.add_trace(
            go.Bar(
                name="2015/16",
                x=df_imp["Player"],
                y=df_imp["2015/16 Rating"],
                marker_color="#3498db",
                text=df_imp["Improvement"].apply(lambda x: f"+{x}" if x > 0 else str(x)),
                textposition="outside",
            )
        )
        fig.update_layout(
            barmode="group",
            title="Rating Improvement: Young Players (< 25, Rating < 85)",
            yaxis_title="FIFA Overall Rating",
            height=450,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for young player improvement.")



elif page == "Q2: Possession & Winning":
    st.title("Q2: How Does Possession Affect Winning?")

    league_filter = st.sidebar.selectbox(
        "League Scope",
        ["Premier League Only", "All Leagues"],
        index=0,
    )
    venue_filter = st.sidebar.selectbox(
        "Venue",
        ["All", "Home", "Away"],
        index=0,
    )

    if league_filter == "Premier League Only":
        base_matches = epl_matches
    else:
        base_matches = match

    poss_data = []
    for _, row in base_matches.iterrows():
        mp = match_poss[match_poss["match_id"] == row["id"]]
        if mp.empty:
            continue
        last_poss = mp.sort_values("elapsed", ascending=False).iloc[0]
        home_poss = last_poss["homepos"]
        away_poss = last_poss["awaypos"]
        if pd.isna(home_poss) or pd.isna(away_poss):
            continue

        home_goals = row["home_team_goal"]
        away_goals = row["away_team_goal"]

        if home_goals > away_goals:
            home_result, away_result = "Win", "Loss"
        elif home_goals < away_goals:
            home_result, away_result = "Loss", "Win"
        else:
            home_result = away_result = "Draw"

        poss_data.append(
            {
                "possession": home_poss,
                "result": home_result,
                "goals_scored": home_goals,
                "goals_conceded": away_goals,
                "venue": "Home",
                "team_api_id": row["home_team_api_id"],
            }
        )
        poss_data.append(
            {
                "possession": away_poss,
                "result": away_result,
                "goals_scored": away_goals,
                "goals_conceded": home_goals,
                "venue": "Away",
                "team_api_id": row["away_team_api_id"],
            }
        )

    df_poss = pd.DataFrame(poss_data)
    if venue_filter != "All":
        df_poss = df_poss[df_poss["venue"] == venue_filter]

    #  Task 3.1: Win Rate by Possession Bins
    st.subheader("Win Rate by Possession Percentage")
    if not df_poss.empty:
        df_poss["poss_bin"] = pd.cut(
            df_poss["possession"],
            bins=[20, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80],
            labels=["20-30", "30-35", "35-40", "40-45", "45-50", "50-55", "55-60", "60-65", "65-70", "70-80"],
        )
        df_poss["win_val"] = df_poss["result"].map({"Win": 1, "Draw": 0.5, "Loss": 0})
        binned = df_poss.groupby("poss_bin", observed=False).agg(
            win_rate=("win_val", "mean"),
            count=("win_val", "count"),
        ).reset_index()
        binned = binned[binned["count"] > 0]

        fig = px.bar(
            binned,
            x="poss_bin",
            y="win_rate",
            text="count",
            title="Win Rate by Possession Percentage Range",
            labels={"poss_bin": "Possession %", "win_rate": "Win Rate"},
            color="win_rate",
            color_continuous_scale="RdYlGn",
        )
        fig.update_traces(texttemplate="%{text} matches", textposition="outside")
        fig.update_layout(yaxis_range=[0, 1], height=450)
        st.plotly_chart(fig, use_container_width=True)

    #  Possession vs Goals
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Possession vs Goals Scored")
        if not df_poss.empty:
            fig = px.scatter(
                df_poss,
                x="possession",
                y="goals_scored",
                color="result",
                color_discrete_map={"Win": "#2ecc71", "Draw": "#f39c12", "Loss": "#e74c3c"},
                title="Possession vs Goals Scored",
                labels={"possession": "Possession %", "goals_scored": "Goals Scored"},
                trendline="ols",
                opacity=0.5,
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Possession vs Goals Conceded")
        if not df_poss.empty:
            fig = px.scatter(
                df_poss,
                x="possession",
                y="goals_conceded",
                color="result",
                color_discrete_map={"Win": "#2ecc71", "Draw": "#f39c12", "Loss": "#e74c3c"},
                title="Possession vs Goals Conceded",
                labels={"possession": "Possession %", "goals_conceded": "Goals Conceded"},
                trendline="ols",
                opacity=0.5,
            )
            st.plotly_chart(fig, use_container_width=True)

    #  Outcome distribution by possession bin
    st.subheader("Match Outcome Distribution by Possession")
    if not df_poss.empty:
        outcome_by_poss = df_poss.groupby(["poss_bin", "result"], observed=False).size().reset_index(name="count")
        fig = px.bar(
            outcome_by_poss,
            x="poss_bin",
            y="count",
            color="result",
            title="Match Outcomes by Possession Range",
            labels={"poss_bin": "Possession %", "count": "Number of Matches"},
            color_discrete_map={"Win": "#2ecc71", "Draw": "#f39c12", "Loss": "#e74c3c"},
            barmode="stack",
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    #  West Ham specific possession analysis
    st.subheader("West Ham: Possession Impact")
    wh_poss = df_poss[df_poss["team_api_id"] == OUR_TEAM_API_ID]
    if not wh_poss.empty:
        wh_binned = wh_poss.groupby("poss_bin", observed=False).agg(
            win_rate=("win_val", "mean"),
            count=("win_val", "count"),
        ).reset_index()
        wh_binned = wh_binned[wh_binned["count"] > 0]
        fig = px.bar(
            wh_binned,
            x="poss_bin",
            y="win_rate",
            text="count",
            title="West Ham Win Rate by Possession Range",
            labels={"poss_bin": "Possession %", "win_rate": "Win Rate"},
            color="win_rate",
            color_continuous_scale="RdYlGn",
        )
        fig.update_traces(texttemplate="%{text} matches", textposition="outside")
        fig.update_layout(yaxis_range=[0, 1.1], height=450)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No possession data found for West Ham.")



elif page == "Q3: Threatening Teams":
    st.title("Q3: Which Teams Pose a Threat?")

    season_q3 = st.sidebar.selectbox(
        "Season",
        ["All Seasons"] + sorted(wh_matches["season"].unique()),
        index=0,
        key="q3_season",
    )
    venue_q3 = st.sidebar.selectbox(
        "Venue",
        ["All", "Home", "Away"],
        index=0,
        key="q3_venue",
    )

    filt = wh_matches.copy()
    if season_q3 != "All Seasons":
        filt = filt[filt["season"] == season_q3]
    if venue_q3 != "All":
        filt = filt[filt["venue"] == venue_q3]

    #  Task 2.1: Win Rate vs Each Opponent
    st.subheader("Win Rate vs Each Opponent")
    opponent_stats = []
    for opp, grp in filt.groupby("opponent"):
        total = len(grp)
        wins = len(grp[grp["result"] == "Win"])
        draws = len(grp[grp["result"] == "Draw"])
        losses = len(grp[grp["result"] == "Loss"])
        win_rate = (wins + 0.5 * draws) / total
        opponent_stats.append(
            {
                "Opponent": opp,
                "Win Rate": round(win_rate, 3),
                "Wins": wins,
                "Draws": draws,
                "Losses": losses,
                "Matches": total,
            }
        )
    df_opp = pd.DataFrame(opponent_stats).sort_values("Win Rate", ascending=True)

    fig = px.bar(
        df_opp,
        y="Opponent",
        x="Win Rate",
        orientation="h",
        title="Win Rate Against Each Opponent",
        color="Win Rate",
        color_continuous_scale="RdYlGn",
        hover_data=["Wins", "Draws", "Losses", "Matches"],
    )
    fig.update_layout(height=max(400, len(df_opp) * 25), yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    #  Task 2.3: Match Outcomes per Opponent (Stacked Bars)
    st.subheader("Performance Balance per Opponent")
    df_opp_sorted = df_opp.sort_values("Matches", ascending=True)
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Wins",
            y=df_opp_sorted["Opponent"],
            x=df_opp_sorted["Wins"],
            orientation="h",
            marker_color="#2ecc71",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Draws",
            y=df_opp_sorted["Opponent"],
            x=df_opp_sorted["Draws"],
            orientation="h",
            marker_color="#f39c12",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Losses",
            y=df_opp_sorted["Opponent"],
            x=df_opp_sorted["Losses"],
            orientation="h",
            marker_color="#e74c3c",
        )
    )
    fig.update_layout(
        barmode="stack",
        title="Wins / Draws / Losses per Opponent",
        xaxis_title="Number of Matches",
        yaxis_title="",
        height=max(400, len(df_opp_sorted) * 25),
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    #  Task 2.2: Match Outcomes per Season
    with col1:
        st.subheader("Match Outcomes per Season")
        season_outcomes = (
            wh_matches.groupby(["season", "result"]).size().reset_index(name="count")
        )
        fig = px.bar(
            season_outcomes,
            x="season",
            y="count",
            color="result",
            title="Wins / Draws / Losses per Season",
            color_discrete_map={"Win": "#2ecc71", "Draw": "#f39c12", "Loss": "#e74c3c"},
            barmode="group",
        )
        fig.update_layout(xaxis_title="Season", yaxis_title="Number of Matches")
        st.plotly_chart(fig, use_container_width=True)

    #  Task 2.4: Goal Difference Distribution
    with col2:
        st.subheader("Goal Difference Distribution")
        fig = go.Figure()
        fig.add_trace(
            go.Histogram(
                x=filt["goal_diff"],
                nbinsx=15,
                marker_color="#3498db",
            )
        )
        fig.add_vline(x=0, line_dash="dash", line_color="red")
        mean_gd = filt["goal_diff"].mean()
        fig.add_vline(
            x=mean_gd,
            line_dash="dot",
            line_color="green",
            annotation_text=f"Mean = {mean_gd:.2f}",
        )
        fig.update_layout(
            title="Goal Difference Distribution",
            xaxis_title="Goal Difference",
            yaxis_title="Frequency",
        )
        st.plotly_chart(fig, use_container_width=True)

    #  Task 2.5: Match Statistics Comparison
    st.subheader("Team Comparison: Average Stats")
    compare_team = st.selectbox(
        "Compare West Ham against:",
        sorted(df_opp["Opponent"].unique()),
        index=0,
    )

    if compare_team:
        compare_id = None
        for tid, tname in team_id_to_name.items():
            if tname == compare_team:
                compare_id = tid
                break

        if compare_id:
            comp_season = season_q3 if season_q3 != "All Seasons" else None
            wh_s = wh_matches if comp_season is None else wh_matches[wh_matches["season"] == comp_season]
            comp_matches = epl_matches[
                (epl_matches["home_team_api_id"] == compare_id)
                | (epl_matches["away_team_api_id"] == compare_id)
            ]
            if comp_season:
                comp_matches = comp_matches[comp_matches["season"] == comp_season]

            def team_avg_stats(matches_df, team_id):
                gf, ga = [], []
                for _, r in matches_df.iterrows():
                    if r["home_team_api_id"] == team_id:
                        gf.append(r["home_team_goal"])
                        ga.append(r["away_team_goal"])
                    else:
                        gf.append(r["away_team_goal"])
                        ga.append(r["home_team_goal"])
                return {
                    "Avg Goals Scored": np.mean(gf) if gf else 0,
                    "Avg Goals Conceded": np.mean(ga) if ga else 0,
                    "Avg Goal Diff": np.mean([g - c for g, c in zip(gf, ga)]) if gf else 0,
                    "Matches": len(gf),
                }

            wh_stats = team_avg_stats(wh_s, OUR_TEAM_API_ID)
            comp_stats = team_avg_stats(comp_matches, compare_id)

            metrics = ["Avg Goals Scored", "Avg Goals Conceded", "Avg Goal Diff"]
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    name=OUR_TEAM_NAME,
                    x=metrics,
                    y=[wh_stats[m] for m in metrics],
                    marker_color="#7b2d8e",
                )
            )
            fig.add_trace(
                go.Bar(
                    name=compare_team,
                    x=metrics,
                    y=[comp_stats[m] for m in metrics],
                    marker_color="#3498db",
                )
            )
            fig.update_layout(
                barmode="group",
                title=f"West Ham vs {compare_team} - Average Match Statistics",
                yaxis_title="Value",
            )
            st.plotly_chart(fig, use_container_width=True)

    #  Task 2.7: League Standings
    st.subheader("League Standings")
    standings_season = st.selectbox(
        "Season for standings",
        sorted(epl_matches["season"].unique()),
        index=len(epl_matches["season"].unique()) - 1,
        key="standings_season",
    )
    season_epl = epl_matches[epl_matches["season"] == standings_season]
    teams_in_season = set(season_epl["home_team_api_id"].unique()) | set(
        season_epl["away_team_api_id"].unique()
    )
    table_rows = []
    for t in teams_in_season:
        t_matches = season_epl[
            (season_epl["home_team_api_id"] == t) | (season_epl["away_team_api_id"] == t)
        ]
        pts, gf_total, ga_total, w, d, lo = 0, 0, 0, 0, 0, 0
        for _, r in t_matches.iterrows():
            if r["home_team_api_id"] == t:
                gf, ga = r["home_team_goal"], r["away_team_goal"]
            else:
                gf, ga = r["away_team_goal"], r["home_team_goal"]
            gf_total += gf
            ga_total += ga
            if gf > ga:
                pts += 3
                w += 1
            elif gf == ga:
                pts += 1
                d += 1
            else:
                lo += 1
        table_rows.append(
            {
                "Team": team_id_to_name.get(t, f"Team {t}"),
                "Played": len(t_matches),
                "W": w,
                "D": d,
                "L": lo,
                "GF": gf_total,
                "GA": ga_total,
                "GD": gf_total - ga_total,
                "Points": pts,
                "is_whu": t == OUR_TEAM_API_ID,
            }
        )
    df_table = pd.DataFrame(table_rows).sort_values(
        ["Points", "GD", "GF"], ascending=[False, False, False]
    )
    df_table.insert(0, "Pos", range(1, len(df_table) + 1))

    colors = ["#7b2d8e" if r else "#3498db" for r in df_table["is_whu"]]
    fig = px.bar(
        df_table,
        x="Team",
        y="Points",
        title=f"League Standings {standings_season}",
        color="is_whu",
        color_discrete_map={True: "#7b2d8e", False: "#3498db"},
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False,
        height=500,
        xaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)

    display_table = df_table.drop(columns=["is_whu"]).reset_index(drop=True)
    st.dataframe(display_table, use_container_width=True)
