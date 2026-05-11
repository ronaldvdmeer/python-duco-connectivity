"""Shared fixtures for python-duco-connectivity tests."""

import pytest


@pytest.fixture
def mock_host() -> str:
    """Return the mock Duco host."""
    return "192.0.2.94"


@pytest.fixture
def api_info_data() -> dict[str, object]:
    """Mock response for GET /api."""
    return {
        "PublicApiVersion": {"Val": "2.5"},
        "ApiInfo": [],
    }


@pytest.fixture
def api_info_full_data() -> dict[str, object]:
    """Mock response for GET /api with endpoint metadata."""
    return {
        "PublicApiVersion": {"Val": "2.6"},
        "ApiVersion": {"Val": "MOCKAPI 2.6.0"},
        "ApiInfo": [
            {
                "Url": "/api",
                "QueryParameters": [],
                "Methods": ["GET"],
                "Modules": [],
            },
            {
                "Url": "/info",
                "QueryParameters": ["module", "submodule", "parameter"],
                "Methods": ["GET"],
                "Modules": ["General", "Diag"],
            },
        ],
    }


@pytest.fixture
def generic_info_all_data() -> dict[str, object]:
    """Mock response for GET /info without query parameters."""
    return {
        "General": {
            "Board": {
                "PublicApiVersion": {"Val": "2.6"},
                "BoxName": {"Val": "SILENT_CONNECT"},
                "BoxSubTypeName": {"Val": "Eu"},
                "SerialBoardBox": {"Val": "RS2420002577"},
                "SerialBoardComm": {"Val": "PS2424005629"},
                "SerialDucoBox": {"Val": "n/a"},
                "SerialDucoComm": {"Val": "P369348-241126-033"},
                "Time": {"Val": 1778454913},
            },
            "Lan": {
                "Mode": {"Val": "WIFI_CLIENT"},
                "Ip": {"Val": "192.168.3.94"},
                "NetMask": {"Val": "255.255.255.0"},
                "DefaultGateway": {"Val": "192.168.3.1"},
                "Dns": {"Val": "192.168.3.1"},
                "Mac": {"Val": "a0:dd:6c:06:12:90"},
                "HostName": {"Val": "duco_061293"},
                "DucoClientIp": {"Val": "0.0.0.0"},
                "WifiApSsid": {"Val": "DUCO"},
                "WifiApKey": {"Val": "12345678"},
                "RssiWifi": {"Val": -47},
                "ScanWifi": [],
            },
            "PublicApi": {"WriteReqCntRemain": {"Val": 198}},
            "Modbus": {"WriteReqCntRemain": {"Val": 200}},
            "Cloud": {"RegistrationMode": {"Val": False}},
        },
        "Diag": {
            "SubSystems": [
                {"Component": "Ventilation", "Status": "Ok"},
                {"Component": "VentCool", "Status": "Ok"},
                {"Component": "SunCtrl", "Status": "Ok"},
            ]
        },
    }


@pytest.fixture
def generic_info_general_data() -> dict[str, object]:
    """Mock response for GET /info with a module query."""
    return {
        "General": {
            "PublicApi": {
                "WriteReqCntRemain": {"Val": 198},
            }
        }
    }


@pytest.fixture
def generic_info_board_data() -> dict[str, object]:
    """Mock response for GET /info with board-level queries."""
    return {
        "General": {
            "Board": {
                "PublicApiVersion": {"Val": "2.6"},
            }
        }
    }


@pytest.fixture
def config_data() -> dict[str, object]:
    """Mock response for GET /config."""
    return {
        "General": {
            "Time": {
                "TimeZone": {"Val": 1, "Min": -12, "Inc": 1, "Max": 12},
                "Dst": {"Val": 1, "Min": 0, "Inc": 1, "Max": 1},
            },
            "Lan": {
                "Mode": {"Val": 1, "Options": [1, 2, 4]},
                "Dhcp": {"Val": 1, "Min": 0, "Inc": 1, "Max": 1},
                "StaticIp": {"Val": "192.0.2.94"},
                "WifiClientSsid": {"Val": "duco-test-net"},
            },
        },
        "HeatRecovery": {
            "Bypass": {
                "TempSupTgtZone1": {"Val": 180, "Min": 120, "Inc": 5, "Max": 220},
            }
        },
    }


@pytest.fixture
def node_configs_data() -> dict[str, object]:
    """Mock response for GET /config/nodes."""
    return {
        "Nodes": [
            {
                "Node": 1,
                "Name": {"Val": "DucoBox"},
            },
            {
                "Node": 7,
                "Name": {"Val": "Kitchen valve"},
            },
            {
                "Node": 113,
            },
        ]
    }


@pytest.fixture
def board_info_data() -> dict[str, object]:
    """Mock response for GET /info?module=General&submodule=Board."""
    return {
        "General": {
            "Board": {
                "PublicApiVersion": {"Val": "2.5"},
                "BoxName": {"Val": "SILENT_CONNECT"},
                "BoxSubTypeName": {"Val": "Eu"},
                "SerialBoardBox": {"Val": "RS0000000001"},
                "SerialBoardComm": {"Val": "PS0000000001"},
                "SerialDucoBox": {"Val": "n/a"},
                "SerialDucoComm": {"Val": "P000000-000000-001"},
                "Time": {"Val": 1775082497},
            }
        }
    }


@pytest.fixture
def board_info_with_optional_versions_data() -> dict[str, object]:
    """Mock response for GET /info?module=General&submodule=Board with SwVersion."""
    return {
        "General": {
            "Board": {
                "PublicApiVersion": {"Val": "2.6"},
                "BoxName": {"Val": "SILENT_CONNECT"},
                "BoxSubTypeName": {"Val": "Eu"},
                "SerialBoardBox": {"Val": "RS0000000001"},
                "SerialBoardComm": {"Val": "PS0000000001"},
                "SerialDucoBox": {"Val": "n/a"},
                "SerialDucoComm": {"Val": "P000000-000000-001"},
                "SwVersion": {"Val": "2.0.6.0"},
                "Time": {"Val": 1775082497},
            }
        }
    }


@pytest.fixture
def lan_info_data() -> dict[str, object]:
    """Mock response for GET /info?module=General&submodule=Lan with Wi-Fi."""
    return {
        "General": {
            "Lan": {
                "Mode": {"Val": "WIFI_CLIENT"},
                "Ip": {"Val": "192.0.2.94"},
                "NetMask": {"Val": "255.255.255.0"},
                "DefaultGateway": {"Val": "192.0.2.1"},
                "Dns": {"Val": "192.0.2.1"},
                "Mac": {"Val": "a0:dd:6c:06:12:90"},
                "HostName": {"Val": "duco_test_box"},
                "RssiWifi": {"Val": -44},
            }
        }
    }


@pytest.fixture
def lan_info_ethernet_data() -> dict[str, object]:
    """Mock response for GET /info?module=General&submodule=Lan with ethernet."""
    return {
        "General": {
            "Lan": {
                "Mode": {"Val": "ETHERNET"},
                "Ip": {"Val": "198.51.100.97"},
                "NetMask": {"Val": "255.255.255.0"},
                "DefaultGateway": {"Val": "198.51.100.1"},
                "Dns": {"Val": "198.51.100.1"},
                "Mac": {"Val": "a0:dd:6c:06:12:93"},
                "HostName": {"Val": "duco_test_box"},
            }
        }
    }


@pytest.fixture
def diag_data() -> dict[str, object]:
    """Mock response for GET /info?module=Diag."""
    return {
        "Diag": {
            "SubSystems": [
                {"Component": "Ventilation", "Status": "Ok"},
                {"Component": "VentCool", "Status": "Ok"},
                {"Component": "SunCtrl", "Status": "Ok"},
            ]
        }
    }


@pytest.fixture
def nodes_data() -> dict[str, object]:
    """Mock response for GET /info/nodes."""
    return {
        "Nodes": [
            {
                "Node": 1,
                "General": {
                    "Type": {"Val": "BOX"},
                    "SubType": {"Val": 1},
                    "NetworkType": {"Val": "VIRT"},
                    "Parent": {"Val": 0},
                    "Asso": {"Val": 0},
                    "Name": {"Val": ""},
                    "Identify": {"Val": 0},
                },
                "Ventilation": {
                    "State": {"Val": "CNT1"},
                    "TimeStateRemain": {"Val": 0},
                    "TimeStateEnd": {"Val": 0},
                    "Mode": {"Val": "MANU"},
                    "FlowLvlTgt": {"Val": 15},
                },
                "Sensor": {
                    "Temp": {"Val": 27.9},
                    "Rh": {"Val": 35.5},
                    "IaqRh": {"Val": 83},
                },
            },
            {
                "Node": 2,
                "General": {
                    "Type": {"Val": "UCCO2"},
                    "SubType": {"Val": 0},
                    "NetworkType": {"Val": "RF"},
                    "Parent": {"Val": 1},
                    "Asso": {"Val": 1},
                    "Name": {"Val": ""},
                    "Identify": {"Val": 0},
                },
                "Ventilation": {
                    "State": {"Val": "CNT1"},
                    "TimeStateRemain": {"Val": 0},
                    "TimeStateEnd": {"Val": 0},
                    "Mode": {"Val": "-"},
                },
                "Sensor": {
                    "Temp": {"Val": 19.8},
                    "Co2": {"Val": 536},
                    "IaqCo2": {"Val": 100},
                },
            },
            {
                "Node": 113,
                "General": {
                    "Type": {"Val": "BSRH"},
                    "SubType": {"Val": 0},
                    "NetworkType": {"Val": "VIRT"},
                    "Parent": {"Val": 1},
                    "Asso": {"Val": 1},
                    "Name": {"Val": ""},
                    "Identify": {"Val": 0},
                },
                "Ventilation": {
                    "State": {"Val": "CNT1"},
                    "TimeStateRemain": {"Val": 0},
                    "TimeStateEnd": {"Val": 0},
                    "Mode": {"Val": "-"},
                },
                "Sensor": {
                    "Temp": {"Val": 27.9},
                    "Rh": {"Val": 36.0},
                    "IaqRh": {"Val": 81},
                },
            },
        ]
    }


@pytest.fixture
def nodes_overview_data() -> list[dict[str, int]]:
    """Mock response for GET /nodes."""
    return [
        {"Node": 1},
        {"Node": 2},
        {"Node": 113},
    ]


@pytest.fixture
def node_data() -> dict[str, object]:
    """Mock response for GET /info/nodes/{node}."""
    return {
        "Node": 2,
        "General": {
            "Type": {"Val": "UCCO2"},
            "SubType": {"Val": 0},
            "NetworkType": {"Val": "RF"},
            "Parent": {"Val": 1},
            "Asso": {"Val": 1},
            "Name": {"Val": ""},
            "Identify": {"Val": 0},
        },
        "Ventilation": {
            "State": {"Val": "CNT1"},
            "TimeStateRemain": {"Val": 0},
            "TimeStateEnd": {"Val": 0},
            "Mode": {"Val": "-"},
        },
        "Sensor": {
            "Temp": {"Val": 19.8},
            "Co2": {"Val": 536},
            "IaqCo2": {"Val": 100},
        },
    }


@pytest.fixture
def action_result_success_data() -> dict[str, object]:
    """Mock success response for POST /action/nodes/{node}."""
    return {"Result": "SUCCESS"}


@pytest.fixture
def action_result_failed_data() -> dict[str, object]:
    """Mock failed response for POST /action/nodes/{node}."""
    return {
        "Result": "FAILED",
        "Code": 12,
        "Message": "Action is not performed",
    }
