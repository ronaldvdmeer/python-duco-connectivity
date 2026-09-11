# Read endpoint inventory

This document inventories the JSON returned by every read endpoint in the
Duco Public API 2.5 specification and compares that contract with three live
systems running Public API 2.7. It is intended to support client design and
polling optimization decisions.

The observations are a point-in-time compatibility sample, not an exhaustive
firmware guarantee. Response times are single samples on a local network and
must not be treated as benchmarks.

## Methodology

The route baseline is the 16 `GET` route templates in
[`notes/public_api_v2.5.yaml`](../notes/public_api_v2.5.yaml). Every static
route was requested from each system. Every route containing a node, zone, or
group path parameter was requested for every ID discovered through `/nodes`
and `/info/zones`.

The test systems were:

| System | Public API | Nodes | Zones | Groups |
| --- | ---: | ---: | ---: | ---: |
| ENERGY | 2.7 | 2 | 2 | 2 |
| FOCUS | 2.7 | 5 | 4 | 4 |
| SILENT_CONNECT | 2.7 | 2 | 1 | 1 |

Only response metadata, JSON structure, field paths, and non-sensitive
capability values were retained. The inventory does not contain device
addresses, serial numbers, MAC addresses, network addresses, SSIDs, Wi-Fi
keys, host names, or custom node and zone names.

## OpenAPI 2.5 route inventory

All 16 documented routes returned HTTP `200` on all three systems when valid
path IDs were used. Optional branches differ by product and installed node
capabilities.

| GET route | OpenAPI 2.5 response schema | Query selectors | Live response shape |
| --- | --- | --- | --- |
| `/api` | `Api` | None | Object with API version and advertised routes |
| `/info` | `Info` | `module`, `submodule`, `parameter` | Object keyed by available modules |
| `/nodes` | `NodesOverview` | None | Array of node objects |
| `/info/nodes` | `InfoNodesOverview` | `module`, `parameter` | Object containing `Nodes` array |
| `/info/nodes/{node}` | `InfoNode` | `module`, `parameter` | Object for one node |
| `/config` | `Config` | `module`, `submodule`, `parameter` | Object keyed by available modules |
| `/config/nodes` | `ConfigNodeOverview` | `parameter` | Object containing `Nodes` array |
| `/config/nodes/{node}` | `ConfigNode` | `parameter` | Object with node ID and name configuration |
| `/action` | `ActionItemList` | None | Array of system action descriptors |
| `/action/nodes` | `NodeListActionItemList` | None | Object containing `Nodes` array |
| `/action/nodes/{node}` | `NodeActionItemList` | None | Object with node ID and action descriptors |
| `/info/zones` | `InfoZonesOverview` | `zone`, `group`, `module`, `submodule`, `parameter` | Object containing `Zones` array |
| `/config/zones` | `ConfigZonesOverview` | `zone`, `group`, `module`, `submodule`, `parameter` | Object containing `Zones` array |
| `/info/zones/{zone}` | `InfoZone` | `group`, `module`, `submodule`, `parameter` | Object for one zone and its groups |
| `/config/zones/{zone}` | `ConfigZone` | `group`, `module`, `submodule`, `parameter` | Object for one zone |
| `/info/zones/{zone}/groups/{group}` | `InfoGroupStruct` | `module`, `submodule`, `parameter` | Object for one zone/group pair |

Selectors are optional. With no selectors, the API returns all available data
for that resource. Multiple selector values can be comma-separated according
to the specification.

### Static endpoint measurement snapshot

Each cell is `HTTP status / response bytes / elapsed milliseconds`. These are
single sequential requests. The large timing variation, especially on ENERGY,
shows why the values are diagnostic samples rather than performance results.
Payload sizes are still useful for comparing response scope.

| GET route | ENERGY | FOCUS | SILENT_CONNECT |
| --- | ---: | ---: | ---: |
| `/api` | 200 / 2075 / 1796 | 200 / 2033 / 222 | 200 / 2017 / 516 |
| `/info` | 200 / 1206 / 2122 | 200 / 1007 / 277 | 200 / 985 / 220 |
| `/nodes` | 200 / 24 / 2448 | 200 / 56 / 188 | 200 / 25 / 272 |
| `/info/nodes` | 200 / 691 / 4487 | 200 / 1757 / 196 | 200 / 691 / 199 |
| `/config` | 200 / 695 / 194 | 200 / 609 / 107 | 200 / 609 / 405 |
| `/config/nodes` | 200 / 70 / 181 | 200 / 214 / 205 | 200 / 71 / 346 |
| `/action` | 200 / 388 / 527 | 200 / 388 / 79 | 200 / 388 / 130 |
| `/action/nodes` | 200 / 483 / 140 | 200 / 1301 / 107 | 200 / 484 / 100 |
| `/info/zones` | 200 / 303 / 619 | 200 / 590 / 728 | 200 / 159 / 282 |
| `/config/zones` | 200 / 165 / 876 | 200 / 313 / 626 | 200 / 88 / 267 |

## Static response fields

The paths below normalize array indexes to `[]`. A path records presence and
nesting only; it does not imply that every node has that field.

### API discovery

`/api` returned the same structural fields on every system:

```text
PublicApiVersion.Val
ApiInfo.[].Url
ApiInfo.[].Methods.[]
ApiInfo.[].QueryParameters.[]
ApiInfo.[].Modules.[]
```

The advertised surface cannot be used as proof that a capability works. See
[Public API 2.7 deviations](#public-api-27-deviations).

### System information

The broad `/info` response contained these modules:

| Module | ENERGY | FOCUS | SILENT_CONNECT |
| --- | :---: | :---: | :---: |
| `General` | Yes | Yes | Yes |
| `Diag` | Yes | Yes | Yes |
| `HeatRecovery` | Yes | No | No |
| `Ventilation` | Yes | No | No |

Common `/info` paths:

```text
General.Board.BoxName.Val
General.Board.BoxSubTypeName.Val
General.Board.PublicApiVersion.Val
General.Board.SerialBoardBox.Val
General.Board.SerialBoardComm.Val
General.Board.SerialDucoBox.Val
General.Board.SerialDucoComm.Val
General.Board.Time.Val
General.Lan.DefaultGateway.Val
General.Lan.Dns.Val
General.Lan.DucoClientIp.Val
General.Lan.HostName.Val
General.Lan.Ip.Val
General.Lan.Mac.Val
General.Lan.Mode.Val
General.Lan.NetMask.Val
General.Lan.RssiWifi.Val
General.Lan.WifiApKey.Val
General.Lan.WifiApSsid.Val
General.Modbus.WriteReqCntRemain.Val
General.PublicApi.WriteReqCntRemain.Val
Diag.SubSystems.[].Component
Diag.SubSystems.[].Status
```

ENERGY additionally returned:

```text
HeatRecovery.General.TimeFilterRemain.Val
Ventilation.Sensor.TempEha.Val
Ventilation.Sensor.TempEta.Val
Ventilation.Sensor.TempOda.Val
Ventilation.Sensor.TempSup.Val
```

The broad response naturally omitted unsupported modules on FOCUS and
SILENT_CONNECT instead of failing the complete request.

### Nodes

`/nodes` is a top-level array, not an object:

```text
[].Node
```

`/info/nodes` wraps the detailed node objects in `Nodes`. The common paths are:

```text
Nodes.[].Node
Nodes.[].General.Asso.Val
Nodes.[].General.Identify.Val
Nodes.[].General.Name.Val
Nodes.[].General.NetworkType.Val
Nodes.[].General.Parent.Val
Nodes.[].General.SubType.Val
Nodes.[].General.Type.Val
Nodes.[].Ventilation.FlowLvlTgt.Val
Nodes.[].Ventilation.Mode.Val
Nodes.[].Ventilation.State.Val
Nodes.[].Ventilation.TimeStateEnd.Val
Nodes.[].Ventilation.TimeStateRemain.Val
```

Sensor paths varied with installed nodes:

| Sensor path | ENERGY | FOCUS | SILENT_CONNECT |
| --- | :---: | :---: | :---: |
| `Nodes.[].Sensor.Rh.Val` | Yes | Yes | Yes |
| `Nodes.[].Sensor.IaqRh.Val` | Yes | Yes | Yes |
| `Nodes.[].Sensor.Co2.Val` | No | Yes | No |
| `Nodes.[].Sensor.IaqCo2.Val` | No | Yes | No |

`/config/nodes` returned `Nodes.[].Node` and `Nodes.[].Name.Val`.
`/action/nodes` returned `Nodes.[].Node` plus
`Nodes.[].Actions.[].Action`, `ValType`, and optional `Enum.[]`.

The corresponding single-node endpoints returned the same fields without the
`Nodes.[]` prefix. All nine discovered nodes returned HTTP `200` from each of
`/info/nodes/{node}`, `/config/nodes/{node}`, and
`/action/nodes/{node}`.

### System actions

`/action` returned a top-level array with these paths on every system:

```text
[].Action
[].ValType
```

All systems exposed eight system action descriptors. Node ventilation action
enums were also consistent across the three systems:

| System action | Value type |
| --- | --- |
| `SetTime` | `Integer` |
| `SetIdentify` | `Boolean` |
| `SetIdentifyAll` | `Boolean` |
| `ReconnectWifi` | `None` |
| `ScanWifi` | `None` |
| `SetWifiApMode` | `Boolean` |
| `SetCloudRegistrationMode` | `Boolean` |
| `SetCloudAllowRemoteIntervention` | `Boolean` |

The node action `SetVentilationState` used value type `Enum` and exposed:

```text
AUTO, AUT1, AUT2, AUT3, MAN1, MAN2, MAN3, EMPT, CNT1, CNT2, CNT3,
MAN1x2, MAN2x2, MAN3x2, MAN1x3, MAN2x3, MAN3x3
```

Action availability remains node-specific and should be read from the action
response rather than assumed from this sample.

### Zones and groups

`/info/zones` returned:

```text
Zones.[].Zone
Zones.[].DeviceGroupConfig.General.Name.Val
Zones.[].Groups.[].Group
Zones.[].Groups.[].DeviceGroupConfig.General.Nodes.[]
```

`/config/zones` returned:

```text
Zones.[].Zone
Zones.[].DeviceGroupConfig.General.Name.Val
```

The single-zone endpoints returned the same shapes without `Zones.[]`.
`/info/zones/{zone}/groups/{group}` always returned `Zone` and `Group`; the
`DeviceGroupConfig.General.Nodes.[]` branch was present when the firmware
included group membership in that response.

All seven discovered zones and seven groups returned HTTP `200` from every
corresponding route in the 2.5 specification.

### Configuration

The broad `/config` response returned these common branches:

```text
General.AutoRebootComm.Period.{Val,Min,Max,Inc}
General.AutoRebootComm.Time.{Val,Min,Max,Inc}
General.Lan.Dhcp.{Val,Min,Max,Inc}
General.Lan.Mode.{Val,Min,Max,Inc}
General.Lan.StaticDefaultGateway.Val
General.Lan.StaticDns.Val
General.Lan.StaticIp.Val
General.Lan.StaticNetMask.Val
General.Lan.WifiClientKey.Val
General.Lan.WifiClientSsid.Val
General.Modbus.Addr.{Val,Min,Max,Inc}
General.Modbus.Offset.{Val,Min,Max,Inc}
General.Time.Dst.{Val,Min,Max,Inc}
General.Time.TimeZone.{Val,Min,Max,Inc}
```

ENERGY additionally returned
`HeatRecovery.Bypass.TempSupTgtZone1.{Val,Min,Max,Inc}`.

The `/config` payload contains Wi-Fi credentials and network configuration.
It must not be logged, committed as an unredacted fixture, exposed through
diagnostics, or retained as an indiscriminate polling snapshot.

## Public API 2.7 deviations

All three systems advertised `GET /config/zones/{zone}/groups/{group}`, which
is absent from the Public API 2.5 specification. Every request using a valid
zone/group pair returned:

```json
{"Code":3,"Result":"FAILED"}
```

with HTTP `400`. The route is therefore advertised but not usable on the
tested firmware.

All three systems also advertised the `WeatherHandler` module for `/info`, but
`GET /info?module=WeatherHandler` returned the same HTTP `400`, code `3`
response on each system.

These observations show that `/api` is useful for discovery but is not an
authoritative runtime capability check. A client must tolerate advertised
routes and modules that fail when queried.

## Polling implications

The live responses support the following conclusions:

1. Prefer one broad `/info` request over separate system-information requests.
   It succeeded on every tested product and omitted unavailable optional
   modules without failing.
2. Derive optional system capabilities from branches actually present in the
   broad response. Do not schedule direct `HeatRecovery`, `Ventilation`, or
   `WeatherHandler` reads based only on `/api` advertisements.
3. Continue to read node information separately through `/info/nodes`. System
   `/info` does not include node state or node sensor data.
4. Fetch actions, configuration, names, and zone membership only when their
   slower-changing data is needed. They do not belong in the regular dynamic
   state poll.
5. Never use broad `/config` as a retained state cache. Use narrowly selected
   configuration reads and keep credential-bearing branches out of logs and
   diagnostics.
6. Treat endpoint latency and payload size as secondary to request count and
   capability correctness. The measurements are single local-network samples,
   while fewer sequential requests directly reduce timeout exposure.

The resulting minimal dynamic poll is one broad `/info` request plus one
`/info/nodes` request. Further reductions would require either omitting node
state or firmware support for combining system and node information.