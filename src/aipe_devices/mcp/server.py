"""Local stdio MCP server of the AIPE Semiconductor Database (read-only data access).

* Protocol: Model Context Protocol, Python SDK ``mcp>=2`` (``MCPServer``), stdio transport
  only; no network listener, no API keys, no cloud services; the server never writes files.
* Tools return plain JSON. Every value carries its unit, stated operating conditions,
  ``data_class`` (manufacturer_model, manufacturer_datasheet, measured ...), source and
  rights status.
* No loss calculation, interpolation or device selection: those are separate services.
* Unknown or misspelled tool arguments are rejected instead of being dropped silently.

The data are read from a checkout of the repository (``$AIPE_DEVICES_DATA`` or the
``data/`` directory next to an editable install); the wheel bundles no dataset.

Run: ``aipe-devices-mcp`` (or ``python -m aipe_devices.mcp.server``); ``--self-test``
lists the tools.
"""

import argparse
import json
import sys
from typing import Any

from aipe_devices import __version__
from aipe_devices.api import MAX_ROWS, Database, QueryError

SERVER_NAME = "aipe-semiconductor-database"
INSTRUCTIONS = (
    "AIPE Semiconductor Database: power semiconductor device records (domain schema 3.0.0, "
    "SI units; temperatures in K, energies in J). Every value states its unit, the operating "
    "conditions the source stated (a condition that is absent was not stated; do not assume "
    "one), its data_class (manufacturer_model = simulation model table, manufacturer_datasheet "
    "= datasheet transcription, measured = laboratory measurement), its source and its rights "
    "status. Today no record is a measurement and no record has been reviewed by a person. "
    "Contributed data are a class of their own: always report their contribution_status, and "
    "never call data 'reviewed' unless that status says so; attribute CC BY data as stated. "
    "Rights status 'not_established' means the owner has given no licence: use the value for "
    "engineering work and cite the source, do not republish it as data. Report only values "
    "present in tool results; never interpolate, extrapolate or fill a missing value. Give "
    "filter values with units, e.g. '25 degC' or '400 V..800 V'."
)


def build_server(database: Database | None = None):
    try:
        from mcp.server.mcpserver import MCPServer
        from mcp.server.mcpserver.exceptions import ToolError
        from mcp.types import ToolAnnotations
    except ImportError as error:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "the MCP server requires the 'mcp' package (pip install -e '.[mcp]')"
        ) from error

    server = MCPServer(
        SERVER_NAME,
        title="AIPE Semiconductor Database",
        instructions=INSTRUCTIONS,
        version=__version__,
    )
    server.middleware.append(_RejectUnknownArguments(server))
    ro = ToolAnnotations(
        title=None,
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
    holder: dict[str, Database] = {} if database is None else {"db": database}

    def run(method: str, *args: Any, **kwargs: Any) -> Any:
        try:
            if "db" not in holder:
                holder["db"] = Database()
            return getattr(holder["db"], method)(*args, **kwargs)
        except QueryError as error:
            raise ToolError(f"{error.code}: {error.message}") from None
        except (TypeError, ValueError) as error:
            raise ToolError(f"invalid_input: {error}") from None

    @server.tool(
        name="database_summary",
        title="Database summary",
        annotations=ro,
        description="Device and record counts per collection and data class, the number of "
        "measured records, and the rights statement that applies to the data.",
    )
    def database_summary() -> dict[str, Any]:
        return run("summary")

    @server.tool(
        name="list_sources",
        title="List sources",
        annotations=ro,
        description="Data owners per collection with their rights status (licence, "
        "redistribution, commercial use) and whether the original files are archived.",
    )
    def list_sources() -> list[dict[str, Any]]:
        return run("list_sources")

    @server.tool(
        name="list_devices",
        title="List devices",
        annotations=ro,
        description="Devices filtered by text, manufacturer, technology (SiC_MOSFET, "
        "Si_MOSFET, IGBT, GaN, diode), integration (discrete | module) or collection "
        "(canonical = manufacturer model records, candidate = unreviewed datasheet "
        "transcriptions).",
    )
    def list_devices(
        query: str | None = None,
        manufacturer: str | None = None,
        technology: str | None = None,
        integration: str | None = None,
        collection: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return run(
            "list_devices",
            query=query,
            manufacturer=manufacturer,
            technology=technology,
            integration=integration,
            collection=collection,
            limit=limit,
        )

    @server.tool(
        name="get_device",
        title="Get device",
        annotations=ro,
        description="One device by device_id or part number: identity, sources with rights, "
        "review status, and every record it holds (single values with unit and conditions; "
        "curves with their axes and ranges). Lists the groups that have no data.",
    )
    def get_device(device: str) -> dict[str, Any]:
        return run("get_device", device)

    @server.tool(
        name="get_values",
        title="Get values",
        annotations=ro,
        description="The stored values of one record (record_id from get_device). For a "
        "curve, 'where' filters grid points by axis, e.g. {\"junction_temperature\": "
        '"25 degC..150 degC", "dc_bus_voltage": "800 V"}; '
        f"at most {MAX_ROWS} rows; grid points only, nothing is interpolated. The result "
        "repeats unit, conditions, data_class, sources and rights.",
    )
    def get_values(
        device: str,
        record_id: str,
        where: dict[str, str] | None = None,
        include_guard_rows: bool = False,
        limit: int = 200,
    ) -> dict[str, Any]:
        return run(
            "get_values",
            device,
            record_id,
            where=where,
            include_guard_rows=include_guard_rows,
            limit=limit,
        )

    @server.tool(
        name="provenance",
        title="Provenance",
        annotations=ro,
        description="Where a device or one of its records comes from: source, original "
        "file and SHA-256, datasheet locator, data_class, lifecycle, review status, quality "
        "flags and rights status. Call it before quoting a value in a report.",
    )
    def provenance(device: str, record_id: str | None = None) -> dict[str, Any]:
        return run("provenance", device, record_id)

    @server.tool(
        name="list_contributions",
        title="List contributed data",
        annotations=ro,
        description="Data contributed by laboratories, manufacturers and individuals under "
        "CC BY 4.0 or CC0, with contribution_status: submitted (not yet passing the "
        "checks), validated (automatic checks pass; no person has confirmed the values) or "
        "reviewed (a named maintainer has looked at it).",
    )
    def list_contributions(
        query: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        return run("list_contributions", query=query, status=status)

    @server.tool(
        name="get_contribution",
        title="Get contributed data",
        annotations=ro,
        description="One contribution: contributor, licence and attribution, device identity "
        "down to lot and sample, test setup, original files with SHA-256, and every value "
        "with unit, conditions, uncertainty, sample and instruments.",
    )
    def get_contribution(contribution_id: str) -> dict[str, Any]:
        return run("get_contribution", contribution_id)

    return server


class _RejectUnknownArguments:
    """Server middleware: a ``tools/call`` naming an undeclared argument is refused.

    The SDK's generated argument model ignores unknown keys, so a misspelled optional
    argument would silently fall back to its default and return a plausible answer.
    """

    def __init__(self, server: Any):
        self._server = server
        self._properties: dict[str, set[str]] | None = None

    async def _declared(self) -> dict[str, set[str]]:
        if self._properties is None:
            tools = await self._server.list_tools()
            self._properties = {
                t.name: set((t.input_schema or {}).get("properties", {})) for t in tools
            }
        return self._properties

    async def __call__(self, ctx: Any, call_next: Any) -> Any:
        if ctx.method == "tools/call" and isinstance(ctx.params, dict):
            name = ctx.params.get("name")
            arguments = ctx.params.get("arguments") or {}
            declared = (await self._declared()).get(name)
            if declared is not None and isinstance(arguments, dict):
                unknown = sorted(set(arguments) - declared)
                if unknown:
                    from mcp.types import CallToolResult, TextContent

                    message = (
                        f"invalid_input: unknown argument(s) for tool {name}: "
                        f"{', '.join(unknown)}; accepted arguments: "
                        f"{', '.join(sorted(declared))}."
                    )
                    return CallToolResult(
                        content=[TextContent(type="text", text=message)], isError=True
                    )
        return await call_next(ctx)


def self_test() -> int:
    """Build the server and list its tools; exit code 0 when tools are registered."""
    import anyio

    server = build_server()

    async def _list() -> list[str]:
        return [t.name for t in await server.list_tools()]

    names = anyio.run(_list)
    report = {"server": SERVER_NAME, "version": __version__, "tools": names, "writes_files": False}
    print(json.dumps(report, indent=2))
    return 0 if names else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aipe-devices-mcp",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--self-test", action="store_true", help="list the tools and exit")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    build_server().run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
