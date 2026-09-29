from tribal_assistant.core.game.world import parse_allies, parse_players, parse_villages, parse_xml


def test_parse_map_files() -> None:
    (village,) = parse_villages("1,King+James+002,451,551,7879970,9100,0\n")
    assert (village["name"], village["x"], village["player_id"]) == ("King James 002", 451, 7879970)
    (player,) = parse_players("1508,xnando,0,1,26,54231\n")
    assert player["name"] == "xnando" and player["rank"] == 54231
    (ally,) = parse_allies("3,DEPARTAMENTO,DEA,1,0,77,77,789\n")
    assert ally["tag"] == "DEA" and ally["all_points"] == 77


def test_parse_xml_casts_numbers() -> None:
    data = parse_xml("<config><speed>2</speed><unit_speed>0.5</unit_speed><spear><speed>18</speed></spear></config>")
    assert data == {"speed": 2, "unit_speed": 0.5, "spear": {"speed": 18}}
