import pytest
from my_types import Game, SeasonPeriod, State


@pytest.mark.parametrize(
    "current_season, game_seasons, state_reset, expected_season, expected_game_seasons",
    [
        # Only preseason games
        (
            SeasonPeriod.PRESEASON,
            [SeasonPeriod.PRESEASON, SeasonPeriod.PRESEASON],
            False,
            SeasonPeriod.PRESEASON,
            [SeasonPeriod.PRESEASON, SeasonPeriod.PRESEASON],
        ),
        # Only regular season games
        (
            SeasonPeriod.REGULAR_SEASON,
            [SeasonPeriod.REGULAR_SEASON, SeasonPeriod.REGULAR_SEASON],
            False,
            SeasonPeriod.REGULAR_SEASON,
            [SeasonPeriod.REGULAR_SEASON, SeasonPeriod.REGULAR_SEASON],
        ),
        # Only playoff games
        (
            SeasonPeriod.PLAYOFFS,
            [SeasonPeriod.PLAYOFFS, SeasonPeriod.PLAYOFFS],
            False,
            SeasonPeriod.PLAYOFFS,
            [SeasonPeriod.PLAYOFFS, SeasonPeriod.PLAYOFFS],
        ),
        # Only playin games
        (
            SeasonPeriod.PLAYIN,
            [SeasonPeriod.PLAYIN, SeasonPeriod.PLAYIN],
            False,
            SeasonPeriod.PLAYIN,
            [SeasonPeriod.PLAYIN, SeasonPeriod.PLAYIN],
        ),
        # Seeing regular season games when it's preseason
        (
            SeasonPeriod.PRESEASON,
            [SeasonPeriod.PRESEASON, SeasonPeriod.REGULAR_SEASON],
            True,
            SeasonPeriod.REGULAR_SEASON,
            [SeasonPeriod.REGULAR_SEASON],
        ),
        # Seeing playoff games when it's the regular season
        (
            SeasonPeriod.REGULAR_SEASON,
            [SeasonPeriod.REGULAR_SEASON, SeasonPeriod.PLAYOFFS],
            True,
            SeasonPeriod.PLAYOFFS,
            [SeasonPeriod.PLAYOFFS],
        ),
        # Seeing playin games when it's the regular season
        (
            SeasonPeriod.REGULAR_SEASON,
            [SeasonPeriod.REGULAR_SEASON, SeasonPeriod.PLAYIN],
            True,
            SeasonPeriod.PLAYIN,
            [SeasonPeriod.PLAYIN],
        ),
        # Seeing playoff games when it's the playin
        (
            SeasonPeriod.PLAYIN,
            [SeasonPeriod.PLAYIN, SeasonPeriod.PLAYOFFS],
            True,
            SeasonPeriod.PLAYOFFS,
            [SeasonPeriod.PLAYOFFS],
        ),
        # Seeing only preseason games when it's the playoffs
        (
            SeasonPeriod.PLAYOFFS,
            [SeasonPeriod.PRESEASON, SeasonPeriod.PRESEASON],
            True,
            SeasonPeriod.PRESEASON,
            [SeasonPeriod.PRESEASON, SeasonPeriod.PRESEASON],
        ),
    ],
)
def test_check_for_season_period_change(
    current_season: SeasonPeriod,
    game_seasons: list[SeasonPeriod],
    state_reset: bool,
    expected_season: SeasonPeriod,
    expected_game_seasons: list[SeasonPeriod],
):
    state = State(
        current_letter="Y",
        times_cycled=2,
        season=current_season.value,
        initial_current_letter="Y",
        initial_times_cycled=2,
        initial_season=current_season.value,
    )
    games: list[Game] = []
    for s in game_seasons:
        games.append(
            Game(
                game_id="1",
                season_period=s,
                is_complete=False,
                home_team_id=1,
                away_team_id=2,
            )
        )

    filtered_games = state.check_for_season_period_change(games)

    assert [g.season_period for g in filtered_games] == expected_game_seasons

    assert state.season == expected_season.value
    if state_reset:
        assert state.current_letter == "A"
        assert state.times_cycled == 0
    else:
        assert state.current_letter == "Y"
        assert state.times_cycled == 2


@pytest.mark.parametrize(
    "current_season, game_seasons",
    [
        # Seeing postseason games when it's the preseason
        (
            SeasonPeriod.PRESEASON,
            [SeasonPeriod.PRESEASON, SeasonPeriod.PLAYOFFS],
        ),
        # Seeing playin games when it's the preseason
        (
            SeasonPeriod.PRESEASON,
            [SeasonPeriod.PRESEASON, SeasonPeriod.PLAYIN],
        ),
        # Seeing regular season games when it's the playoffs
        (
            SeasonPeriod.PLAYOFFS,
            [SeasonPeriod.PLAYOFFS, SeasonPeriod.REGULAR_SEASON],
        ),
        # Seeing playin games when it's the playoffs
        (
            SeasonPeriod.PLAYOFFS,
            [SeasonPeriod.PLAYOFFS, SeasonPeriod.PLAYIN],
        ),
        # Seeing postseason and preseason games together
        (SeasonPeriod.PLAYOFFS, [SeasonPeriod.PLAYOFFS, SeasonPeriod.PRESEASON]),
    ],
)
def test_check_for_season_period_change_error(
    current_season: SeasonPeriod,
    game_seasons: list[SeasonPeriod],
):
    state = State(
        current_letter="Y",
        times_cycled=2,
        season=current_season.value,
        initial_current_letter="Y",
        initial_times_cycled=2,
        initial_season=current_season.value,
    )
    games: list[Game] = []
    for s in game_seasons:
        games.append(
            Game(
                game_id="1",
                season_period=s,
                is_complete=False,
                home_team_id=1,
                away_team_id=2,
            )
        )

    with pytest.raises(ValueError):
        state.check_for_season_period_change(games)
