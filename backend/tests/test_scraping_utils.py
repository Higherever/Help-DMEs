import pytest
from backend.services.scraping_utils import (
    parse_requirement_text,
    parse_cost_text,
    normalize_category
)

def test_parse_team_rating():
    text = "Min. Team Rating: 85"
    expected = {"requirement_type": "team_rating", "operator": "min", "value": "85", "detail": None}
    assert parse_requirement_text(text) == expected

def test_parse_players_from_league():
    text = "Min. 3 Players from: Premier League"
    expected = {"requirement_type": "players_from", "operator": "min", "value": "3", "detail": "Premier League"}
    assert parse_requirement_text(text) == expected

def test_parse_player_quality():
    text = "Min. 4 Players: Rare"
    expected = {"requirement_type": "player_quality", "operator": "min", "value": "4", "detail": "Rare"}
    assert parse_requirement_text(text) == expected

def test_parse_same_attribute_nation():
    text = "Min. 2 Players same Nation"
    expected = {"requirement_type": "same_attribute", "operator": "min", "value": "2", "detail": "Nation"}
    assert parse_requirement_text(text) == expected

def test_parse_squad_chemistry():
    text = "Minimum Squad Chemistry: 20"
    expected = {"requirement_type": "squad_chemistry", "operator": "min", "value": "20", "detail": None}
    assert parse_requirement_text(text) == expected

def test_parse_players_from_exact():
    text = "Exactly 1 Players from: Brazil"
    expected = {"requirement_type": "players_from", "operator": "exact", "value": "1", "detail": "Brazil"}
    assert parse_requirement_text(text) == expected

def test_parse_same_attribute_club_max():
    text = "Max. 3 Players same Club"
    expected = {"requirement_type": "same_attribute", "operator": "max", "value": "3", "detail": "Club"}
    assert parse_requirement_text(text) == expected

def test_parse_player_type_totw():
    text = "Min. 1 Players: Any TOTW or TOTS"
    expected = {"requirement_type": "player_type", "operator": "min", "value": "1", "detail": "Any TOTW or TOTS"}
    assert parse_requirement_text(text) == expected

def test_parse_cost():
    assert parse_cost_text("10,000") == 10000
    assert parse_cost_text("1.500") == 1500
    assert parse_cost_text("500") == 500
    assert parse_cost_text(None) is None
    assert parse_cost_text("N/A") is None

def test_normalize_category():
    assert normalize_category("Players") == "players"
    assert normalize_category("Upgrades") == "upgrades"
    assert normalize_category("Custom") == "custom"
